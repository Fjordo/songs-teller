"""
Flask route handlers for Song Teller API.
"""

import json
import logging
import os
import shutil
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request

from songs_teller.config import config
from songs_teller.llm import force_unload_model, process_with_llm
from songs_teller.tts import play_and_delete, play_audio
from songs_teller.utils import get_project_root

logger = logging.getLogger(__name__)

MAX_FIELD_LENGTH = 200  # max characters for artist / title fields

# In-memory storage for current song session
current_session: Dict[str, Any] = {
    "songs": [],
    "started_at": None,
    "last_updated": None,
}

# Protects all reads and writes to current_session across threads
_session_lock = threading.Lock()

# Reference to the most recent LLM thread — used by tests to join before asserting
_last_llm_thread: Optional[threading.Thread] = None


def register_routes(app: Flask) -> None:
    """
    Register all API routes on the Flask app.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def _check_api_key():
        """Reject requests that don't carry a valid X-Api-Key header.

        Authentication is only enforced when the API_KEY environment variable
        is set. When it is absent the server operates in open/dev mode.
        """
        expected = os.environ.get("API_KEY")
        if not expected:
            return  # dev mode — no auth required
        provided = request.headers.get("X-Api-Key")
        if not provided or provided != expected:
            return jsonify({"error": "Unauthorized"}), 401

    @app.route("/api/song", methods=["POST"])
    def add_song():
        """
        Add a song to the current session.

        Expected JSON body:
        {
            "artist": "Artist Name",
            "title": "Song Title"
        }
        """
        try:
            data = request.get_json(force=True, silent=True)

            if data is None:
                return jsonify({"error": "Invalid or missing JSON data provided"}), 400

            artist = data.get("artist")
            title = data.get("title")

            if not artist or not title:
                return jsonify({"error": "Both artist and title are required"}), 400

            if len(artist) > MAX_FIELD_LENGTH or len(title) > MAX_FIELD_LENGTH:
                return jsonify(
                    {"error": f"artist and title must not exceed {MAX_FIELD_LENGTH} characters"}
                ), 400

            song = {
                "artist": artist,
                "title": title,
                "timestamp": datetime.now().isoformat(),
            }

            with _session_lock:
                is_duplicate = any(
                    s["artist"] == artist and s["title"] == title
                    for s in current_session["songs"]
                )
                if not is_duplicate:
                    current_session["songs"].append(song)
                    current_session["last_updated"] = datetime.now().isoformat()
                    if current_session["started_at"] is None:
                        current_session["started_at"] = datetime.now().isoformat()
                total = len(current_session["songs"])

            if not is_duplicate:
                logger.info("Added: %s - %s (Total: %d)", artist, title, total)
                return jsonify(
                    {
                        "status": "success",
                        "message": "Song added",
                        "total_songs": total,
                    }
                ), 200
            else:
                logger.info("Skipped duplicate: %s - %s", artist, title)
                return jsonify(
                    {
                        "status": "skipped",
                        "message": "Song already in session",
                        "total_songs": total,
                    }
                ), 200

        except Exception as e:
            logger.error("Error in add_song: %s", e)
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/session/reset", methods=["POST"])
    def reset_session():
        """
        Reset the current session and optionally process the songs.

        Optional JSON body:
        {
            "process": true,
            "play_opening_audio": false
        }
        """
        global _last_llm_thread
        try:
            data = request.get_json() or {}
            should_process = data.get("process", True)
            play_opening_audio = data.get("play_opening_audio", False)

            with _session_lock:
                songs_snapshot = current_session["songs"].copy()

            song_count = len(songs_snapshot)

            if should_process and song_count > 0:
                logger.info("Closing session with %d songs", song_count)

                if config.get("save_session", False):
                    _save_session_to_file(songs_snapshot)

                _handle_buffered_audio()

                if play_opening_audio:
                    threading.Thread(target=_play_opening_audio, daemon=True).start()

                _last_llm_thread = threading.Thread(
                    target=process_with_llm, args=(songs_snapshot,), daemon=True
                )
                _last_llm_thread.start()

            with _session_lock:
                current_session["songs"] = []
                current_session["started_at"] = None
                current_session["last_updated"] = None

            logger.info("Session reset (processed %d songs)", song_count)

            return jsonify(
                {
                    "status": "success",
                    "message": "Session reset",
                    "songs_processed": song_count,
                }
            ), 200

        except Exception as e:
            logger.error("Error in reset_session: %s", e)
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/session/status", methods=["GET"])
    def get_status():
        """Get current session status."""
        with _session_lock:
            snapshot = {
                "song_count": len(current_session["songs"]),
                "started_at": current_session["started_at"],
                "last_updated": current_session["last_updated"],
                "songs": current_session["songs"].copy(),
            }
        return jsonify(snapshot), 200

    @app.route("/api/llm/context/reset", methods=["POST"])
    def reset_llm_context():
        """Forces Ollama to unload the model, clearing context."""
        try:
            local_config = config.get("local", {})
            base_url = local_config.get("llm_api_url", "http://localhost:11434")
            model = local_config.get("llm_model", "llama3.1")

            if force_unload_model(base_url, model):
                logger.info("LLM context reset successful.")
                return jsonify({"status": "success", "message": "LLM context reset"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to reset context"}), 500

        except Exception as e:
            logger.error("Error resetting LLM context: %s", e)
            return jsonify({"status": "error", "message": "Internal server error"}), 500


def _handle_buffered_audio() -> None:
    """Play the previously buffered commentary audio if one exists."""
    if not config.get("buffer_audio", False) or not config.get("play_audio", False):
        return

    mode_config = config.get(config.get("mode", "google"), {})
    tts_opts = mode_config.get("tts_options", {})
    ext = tts_opts.get("response_format", "wav")

    base_path = get_project_root()
    buffer_file = base_path / f"buffered_commentary.{ext}"

    if not buffer_file.exists():
        logger.info("No buffered audio found. Nothing to play yet.")
        return

    playing_file = base_path / f"playing_commentary.{ext}"
    if playing_file.exists():
        try:
            playing_file.unlink()
        except Exception as e:
            logger.warning("Could not remove existing playing file: %s", e)

    shutil.move(str(buffer_file), str(playing_file))
    logger.info("Starting async playback of: %s", playing_file)
    threading.Thread(target=play_and_delete, args=(str(playing_file),), daemon=True).start()


def _save_session_to_file(songs: List[Dict]) -> None:
    """Save songs to a JSON file with timestamp."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = get_project_root() / f"song_session_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)

        logger.info("Session saved to: %s", filename)
    except Exception as e:
        logger.warning("Error saving session to file: %s", e)


def _play_opening_audio() -> None:
    """Play the opening audio file. Path is resolved relative to the project root."""
    try:
        if not config.get("play_audio", False):
            return

        opening_audio_path = config.get("opening_audio_path")
        if not opening_audio_path:
            logger.info("No opening_audio_path configured. Skipping opening audio.")
            return

        audio_file = (get_project_root() / opening_audio_path).resolve()

        if not audio_file.exists():
            logger.warning("Opening audio file not found: %s", audio_file)
            return

        logger.info("Playing opening audio from: %s", audio_file)
        play_audio(str(audio_file))

    except Exception as e:
        logger.warning("Error playing opening audio: %s", e)
