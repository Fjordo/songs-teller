"""
Pytest configuration and fixtures for Songs Teller tests.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from songs_teller.api import create_app
from songs_teller.config import config


@pytest.fixture
def app():
    """Create a Flask application instance for testing."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def sample_song():
    """Return a sample song dictionary."""
    return {"artist": "Pink Floyd", "title": "Time"}


@pytest.fixture
def sample_song_data():
    """Return sample song data as JSON string."""
    return '{"artist": "Pink Floyd", "title": "Time"}'


@pytest.fixture
def sample_songs():
    """Return a list of sample songs."""
    return [
        {"artist": "Pink Floyd", "title": "Time"},
        {"artist": "The Beatles", "title": "Hey Jude"},
        {"artist": "Led Zeppelin", "title": "Stairway to Heaven"},
    ]


@pytest.fixture
def mock_config():
    """Mock configuration dictionary."""
    return {
        "mode": "google",
        "google": {
            "llm_model": "gemini-2.0-flash",
            "tts_key_path": "test_key.json",
            "tts_voice": "en-US-Neural2-D",
            "tts_language_code": "en-US",
        },
        "local": {
            "llm_api_url": "http://localhost:11434",
            "llm_model": "llama3.1",
            "tts_api_url": "http://localhost:5500/v1/audio/speech",
        },
        "prompt_file": "prompt.txt",
        "save_session": False,
        "play_audio": False,  # Disable audio in tests
        "buffer_audio": False,
    }


@pytest.fixture
def temp_config_file(mock_config):
    """Create a temporary config.json file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(mock_config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def reset_session():
    """Reset the session state before each test."""
    from songs_teller.routes import current_session

    # Save original state
    original_songs = current_session["songs"].copy()
    original_started_at = current_session["started_at"]
    original_last_updated = current_session["last_updated"]

    yield

    # Restore original state
    current_session["songs"] = original_songs
    current_session["started_at"] = original_started_at
    current_session["last_updated"] = original_last_updated


@pytest.fixture(autouse=True)
def reset_session_auto(reset_session):
    """Automatically reset session before each test."""
    from songs_teller.routes import current_session

    current_session["songs"] = []
    current_session["started_at"] = None
    current_session["last_updated"] = None


@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    mock_response = MagicMock()
    mock_response.content = "This is a test commentary about the songs played."
    return mock_response


@pytest.fixture
def mock_requests_post():
    """Mock requests.post for external API calls."""
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test LLM response"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        yield mock_post
