#!/usr/bin/env python3
"""
Entry point script for Songs Teller API server.
"""

import sys
import os

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from songs_teller.api import create_app
from songs_teller.config import config

if __name__ == "__main__":
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
        print(f"  LLM:   Ollama ({mode_config.get('llm_model', 'gemma-3-27b-it')}) @ {mode_config.get('llm_api_url', 'http://localhost:11434')}")
        print(f"  TTS:   Chatterbox @ {mode_config.get('tts_api_url', 'N/A')}")
    print(f"  Audio: {'ON' if config.get('play_audio') else 'OFF'} | Buffer: {'ON' if config.get('buffer_audio') else 'OFF'}")
    print(f"\nEndpoints:")
    print("  POST /api/song            - Add a song to current session")
    print("  POST /api/session/reset   - Reset session (process songs)")
    print("  GET  /api/session/status  - Get current session status")
    print("  POST /api/llm/context/reset - Unload Ollama model (local mode)")
    print(f"\nServer starting on http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
