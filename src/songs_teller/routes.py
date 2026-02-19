"""
Flask route handlers for Song Teller API.
"""

import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, request

from songs_teller.config import config
from songs_teller.llm import force_unload_model, process_with_llm
from songs_teller.tts import play_and_delete, play_audio
from songs_teller.utils import get_project_root

# In-memory storage for current song session
current_session: Dict[str, any] = {
    "songs": [],
    "started_at": None,
    "last_updated": None,
}


def register_routes(app: Flask) -> None:
    """
    Register all API routes on the Flask app.

    Args:
        app: Flask application instance
    """

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
            # Try to parse JSON, return 400 if parsing fails
            data = request.get_json(force=True, silent=True)

            if data is None:
                return jsonify({"error": "Invalid or missing JSON data provided"}), 400

            artist = data.get("artist")
            title = data.get("title")

            if not artist or not title:
                return jsonify({"error": "Both artist and title are required"}), 400

            song = {
                "artist": artist,
                "title": title,
                "timestamp": datetime.now().isoformat(),
            }

            # Check for duplicates
            is_duplicate = any(
                s["artist"] == artist and s["title"] == title
                for s in current_session["songs"]
            )

            if not is_duplicate:
                current_session["songs"].append(song)
                current_session["last_updated"] = datetime.now().isoformat()

                if current_session["started_at"] is None:
                    current_session["started_at"] = datetime.now().isoformat()

                print(
                    f"✅ Added: {artist} - {title} (Total: {len(current_session['songs'])})"
                )

                return jsonify(
                    {
                        "status": "success",
                        "message": "Song added",
                        "total_songs": len(current_session["songs"]),
                    }
                ), 200
            else:
                print(f"⏭️  Skipped duplicate: {artist} - {title}")
                return jsonify(
                    {
                        "status": "skipped",
                        "message": "Song already in session",
                        "total_songs": len(current_session["songs"]),
                    }
                ), 200

        except Exception as e:
            print(f"❌ Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/session/reset", methods=["POST"])
    def reset_session():
        """
        Reset the current session and optionally process the songs.

        Optional JSON body:
        {
            "process": true,  // If true, process songs before resetting
            "play_opening_audio": false  // If true, play opening audio after LLM invocation
        }
        """
        try:
            data = request.get_json() or {}
            should_process = data.get("process", True)
            play_opening_audio = data.get("play_opening_audio", False)

            if should_process and len(current_session["songs"]) > 0:
                print(f"\n{'=' * 60}")
                print(f"🔄 Closing Session with {len(current_session['songs'])} songs")
                print(f"{'=' * 60}\n")

                # Save to file
                if config.get("save_session", False):
                    _save_session_to_file(current_session["songs"])

                # AUDIO BUFFERING: Asynchronous Playback
                if config.get("buffer_audio", False) and config.get(
                    "play_audio", False
                ):
                    mode_config = config.get(config.get("mode", "google"), {})
                    tts_opts = mode_config.get("tts_options", {})
                    ext = tts_opts.get("response_format", "wav")

                    # Get project root for buffer file location
                    base_path = get_project_root()
                    buffer_file = base_path / f"buffered_commentary.{ext}"
                    if buffer_file.exists():
                        playing_file = base_path / f"playing_commentary.{ext}"

                        if playing_file.exists():
                            try:
                                playing_file.unlink()
                            except Exception as e:
                                print(
                                    f"⚠️ Warning: Could not remove existing playing file: {e}"
                                )

                        shutil.move(str(buffer_file), str(playing_file))
                        print(f"🔊 Starting async playback of: {playing_file}")

                        playback_thread = threading.Thread(
                            target=play_and_delete, args=(str(playing_file),)
                        )
                        playback_thread.start()
                    else:
                        print("ℹ️  No buffered audio found. Nothing to play yet.")

                # Play opening audio asynchronously before/during LLM invocation
                if play_opening_audio:
                    audio_thread = threading.Thread(target=_play_opening_audio)
                    audio_thread.start()

                # Query LLM about the songs/artists (Generates new buffer)
                process_with_llm(current_session["songs"])

            song_count = len(current_session["songs"])

            # Reset session
            current_session["songs"] = []
            current_session["started_at"] = None
            current_session["last_updated"] = None

            print(f"🔄 Session reset (processed {song_count} songs)\n")

            return jsonify(
                {
                    "status": "success",
                    "message": "Session reset",
                    "songs_processed": song_count,
                }
            ), 200

        except Exception as e:
            print(f"❌ Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/session/status", methods=["GET"])
    def get_status():
        """Get current session status."""
        return jsonify(
            {
                "song_count": len(current_session["songs"]),
                "started_at": current_session["started_at"],
                "last_updated": current_session["last_updated"],
                "songs": current_session["songs"],
            }
        ), 200

    @app.route("/api/llm/context/reset", methods=["POST"])
    def reset_llm_context():
        """
        Forces Ollama to unload the model, clearing context.
        """
        try:
            local_config = config.get("local", {})
            base_url = local_config.get("llm_api_url", "http://localhost:11434")
            model = local_config.get("llm_model", "llama3.1")

            if force_unload_model(base_url, model):
                print("✅ LLM Context reset successful.")
                return jsonify(
                    {"status": "success", "message": "LLM context reset"}
                ), 200
            else:
                return jsonify(
                    {"status": "error", "message": "Failed to reset context"}
                ), 500

        except Exception as e:
            print(f"❌ Error resetting LLM context: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500


def _save_session_to_file(songs: List[Dict]) -> None:
    """
    Save songs to a JSON file with timestamp.

    Args:
        songs: List of song dictionaries to save
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = get_project_root() / f"song_session_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)

        print(f"💾 Session saved to: {filename}")
    except Exception as e:
        print(f"⚠️  Error saving to file: {e}")


def _play_opening_audio() -> None:
    """
    Play the opening audio file immediately after LLM invocation completes.
    Path is resolved relative to the api.py module directory.
    """
    try:
        if not config.get("play_audio", False):
            return

        opening_audio_path = config.get("opening_audio_path")
        if not opening_audio_path:
            print("ℹ️  No opening_audio_path configured. Skipping opening audio.")
            return

        # Resolve path relative to api.py directory
        from songs_teller import api as api_module

        api_dir = Path(api_module.__file__).parent
        audio_file = (api_dir / opening_audio_path).resolve()

        if not audio_file.exists():
            print(f"⚠️  Opening audio file not found: {audio_file}")
            return

        print(f"🎵 Playing opening audio from: {audio_file}")
        play_audio(str(audio_file))

    except Exception as e:
        print(f"⚠️  Error playing opening audio: {e}")
