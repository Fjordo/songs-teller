"""
Flask route handlers for Song Teller API.
"""

import json
import os
import shutil
import threading
from datetime import datetime

from flask import jsonify, request

from songs_teller.config import config
from songs_teller.llm import force_unload_model, process_with_llm
from songs_teller.tts import play_and_delete

# In-memory storage for current song session
current_session = {"songs": [], "started_at": None, "last_updated": None}


def register_routes(app):
    """Register all API routes on the Flask app."""

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
            "process": true  // If true, process songs before resetting
        }
        """
        try:
            data = request.get_json() or {}
            should_process = data.get("process", True)

            if should_process and len(current_session["songs"]) > 0:
                print(f"\n{'=' * 60}")
                print(f"🔄 Closing Session with {len(current_session['songs'])} songs")
                print(f"{'=' * 60}\n")

                # Save to file
                if config.get("save_session", False):
                    _save_session_to_file(current_session["songs"])

                # AUDIO BUFFERING: Asynchronous Playback
                if config.get("buffer_audio", False) and config.get("play_audio", False):
                    mode_config = config.get(config.get("mode", "google"), {})
                    tts_opts = mode_config.get("tts_options", {})
                    ext = tts_opts.get("response_format", "wav")

                    # Get project root for buffer file location
                    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    buffer_file = os.path.join(
                        base_path,
                        f"buffered_commentary.{ext}",
                    )
                    if os.path.exists(buffer_file):
                        playing_file = os.path.join(
                            base_path,
                            f"playing_commentary.{ext}",
                        )

                        if os.path.exists(playing_file):
                            try:
                                os.remove(playing_file)
                            except Exception as e:
                                print(
                                    f"⚠️ Warning: Could not remove existing playing file: {e}"
                                )

                        shutil.move(buffer_file, playing_file)
                        print(f"🔊 Starting async playback of: {playing_file}")

                        playback_thread = threading.Thread(
                            target=play_and_delete, args=(playing_file,)
                        )
                        playback_thread.start()
                    else:
                        print("ℹ️  No buffered audio found. Nothing to play yet.")

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
                return jsonify({"status": "success", "message": "LLM context reset"}), 200
            else:
                return jsonify(
                    {"status": "error", "message": "Failed to reset context"}
                ), 500

        except Exception as e:
            print(f"❌ Error resetting LLM context: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500


def _save_session_to_file(songs):
    """Save songs to a JSON file with timestamp."""
    try:
        # Save to project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(base_path, f"song_session_{timestamp}.json")

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)

        print(f"💾 Session saved to: {filename}")
    except Exception as e:
        print(f"⚠️  Error saving to file: {e}")
