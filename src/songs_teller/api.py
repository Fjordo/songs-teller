#!/usr/bin/env python3
"""
Song Teller API Server — Main Flask application.
"""

import logging

from flask import Flask

from songs_teller.config import config, load_config
from songs_teller.routes import register_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    load_config()
    register_routes(app)
    return app


def main() -> None:
    """Start the Songs Teller API server (console script entry point)."""
    app = create_app()

    mode = config.get("mode", "google")
    mode_config = config.get(mode, {})

    print("=" * 60)
    print("🎵 Song Teller API Server")
    print("=" * 60)
    print(f"\n  Mode:  {mode.upper()}")
    if mode == "google":
        print(f"  LLM:   Google Gemini ({mode_config.get('llm_model', 'gemini-2.0-flash')})")
        print(f"  TTS:   Google Cloud TTS ({mode_config.get('tts_voice', 'en-US-Neural2-D')})")
    else:
        print(f"  LLM:   Ollama ({mode_config.get('llm_model', 'llama3.1')}) @ {mode_config.get('llm_api_url', 'http://localhost:11434')}")
        print(f"  TTS:   Chatterbox @ {mode_config.get('tts_api_url', 'N/A')}")
    print(f"  Audio: {'ON' if config.get('play_audio') else 'OFF'} | Buffer: {'ON' if config.get('buffer_audio') else 'OFF'}")
    print(f"\nEndpoints:")
    print("  POST /api/song              - Add a song to current session")
    print("  POST /api/session/reset     - Reset session (process songs)")
    print("  GET  /api/session/status    - Get current session status")
    print("  POST /api/llm/context/reset - Unload Ollama model (local mode)")
    print(f"\nServer starting on http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
