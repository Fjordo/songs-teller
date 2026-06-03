"""
Tests for Flask API routes.
"""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from songs_teller import routes
from songs_teller.routes import current_session


class TestAddSong:
    """Tests for POST /api/song endpoint."""

    def test_add_song_success(self, client, sample_song):
        """Test successfully adding a song to the session."""
        response = client.post(
            "/api/song",
            data=json.dumps(sample_song),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["message"] == "Song added"
        assert data["total_songs"] == 1

        # Verify song was added to session
        assert len(current_session["songs"]) == 1
        assert current_session["songs"][0]["artist"] == sample_song["artist"]
        assert current_session["songs"][0]["title"] == sample_song["title"]
        assert "timestamp" in current_session["songs"][0]
        assert current_session["started_at"] is not None

    def test_add_song_missing_artist(self, client):
        """Test adding a song without artist field."""
        response = client.post(
            "/api/song",
            data=json.dumps({"title": "Time"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "artist" in data["error"].lower() or "required" in data["error"].lower()

    def test_add_song_missing_title(self, client):
        """Test adding a song without title field."""
        response = client.post(
            "/api/song",
            data=json.dumps({"artist": "Pink Floyd"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "title" in data["error"].lower() or "required" in data["error"].lower()

    def test_add_song_no_json(self, client):
        """Test adding a song without JSON data."""
        response = client.post("/api/song", data="not json")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_add_song_duplicate(self, client, sample_song):
        """Test adding a duplicate song."""
        # Add song first time
        response1 = client.post(
            "/api/song",
            data=json.dumps(sample_song),
            content_type="application/json",
        )
        assert response1.status_code == 200

        # Try to add same song again
        response2 = client.post(
            "/api/song",
            data=json.dumps(sample_song),
            content_type="application/json",
        )

        assert response2.status_code == 200
        data = json.loads(response2.data)
        assert data["status"] == "skipped"
        assert data["message"] == "Song already in session"
        assert data["total_songs"] == 1  # Still only one song

    def test_add_song_artist_too_long(self, client):
        """Test that artist exceeding MAX_FIELD_LENGTH is rejected."""
        response = client.post(
            "/api/song",
            data=json.dumps({"artist": "A" * 201, "title": "Valid"}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "200" in data["error"]

    def test_add_song_title_too_long(self, client):
        """Test that title exceeding MAX_FIELD_LENGTH is rejected."""
        response = client.post(
            "/api/song",
            data=json.dumps({"artist": "Valid", "title": "T" * 201}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_add_song_at_max_length_accepted(self, client):
        """Exactly MAX_FIELD_LENGTH characters should be accepted."""
        response = client.post(
            "/api/song",
            data=json.dumps({"artist": "A" * 200, "title": "T" * 200}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_add_multiple_songs(self, client, sample_songs):
        """Test adding multiple different songs."""
        for song in sample_songs:
            response = client.post(
                "/api/song",
                data=json.dumps(song),
                content_type="application/json",
            )
            assert response.status_code == 200

        assert len(current_session["songs"]) == len(sample_songs)


class TestSessionStatus:
    """Tests for GET /api/session/status endpoint."""

    def test_get_status_empty_session(self, client):
        """Test getting status of empty session."""
        response = client.get("/api/session/status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["song_count"] == 0
        assert data["started_at"] is None
        assert data["last_updated"] is None
        assert data["songs"] == []

    def test_get_status_with_songs(self, client, sample_songs):
        """Test getting status of session with songs."""
        # Add some songs
        for song in sample_songs:
            client.post(
                "/api/song",
                data=json.dumps(song),
                content_type="application/json",
            )

        response = client.get("/api/session/status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["song_count"] == len(sample_songs)
        assert data["started_at"] is not None
        assert data["last_updated"] is not None
        assert len(data["songs"]) == len(sample_songs)


class TestResetSession:
    """Tests for POST /api/session/reset endpoint."""

    @patch("songs_teller.routes.process_with_llm")
    def test_reset_session_with_songs_no_process(self, mock_llm, client, sample_songs):
        """Test resetting session with songs but without processing."""
        # Add songs
        for song in sample_songs:
            client.post(
                "/api/song",
                data=json.dumps(song),
                content_type="application/json",
            )

        response = client.post(
            "/api/session/reset",
            data=json.dumps({"process": False}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["songs_processed"] == len(sample_songs)

        # Verify session was reset
        assert len(current_session["songs"]) == 0
        assert current_session["started_at"] is None
        assert current_session["last_updated"] is None

        # LLM should not be called
        mock_llm.assert_not_called()

    @patch("songs_teller.routes.process_with_llm")
    def test_reset_session_with_songs_and_process(self, mock_llm, client, sample_songs):
        """Test resetting session with songs and processing."""
        for song in sample_songs:
            client.post(
                "/api/song",
                data=json.dumps(song),
                content_type="application/json",
            )

        response = client.post(
            "/api/session/reset",
            data=json.dumps({"process": True}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["songs_processed"] == len(sample_songs)

        # Session is reset before the LLM thread completes
        assert len(current_session["songs"]) == 0

        # Wait for the background LLM thread then verify it was called correctly
        if routes._last_llm_thread:
            routes._last_llm_thread.join(timeout=5.0)
        mock_llm.assert_called_once()
        call_args = mock_llm.call_args[0][0]
        assert len(call_args) == len(sample_songs)

    @patch("songs_teller.routes.process_with_llm")
    def test_reset_session_empty(self, mock_llm, client):
        """Test resetting an empty session."""
        response = client.post(
            "/api/session/reset",
            data=json.dumps({"process": True}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["songs_processed"] == 0

        # LLM should not be called for empty session
        mock_llm.assert_not_called()

    @patch("songs_teller.routes.process_with_llm")
    def test_reset_session_default_process(self, mock_llm, client, sample_songs):
        """Test resetting session with default process=True."""
        for song in sample_songs:
            client.post(
                "/api/song",
                data=json.dumps(song),
                content_type="application/json",
            )

        response = client.post(
            "/api/session/reset",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 200
        if routes._last_llm_thread:
            routes._last_llm_thread.join(timeout=5.0)
        mock_llm.assert_called_once()


class TestAuthentication:
    """Tests for optional API key authentication."""

    @patch.dict(os.environ, {"API_KEY": "test-secret-key"})
    def test_missing_key_returns_401(self, client):
        """Requests without X-Api-Key header are rejected when API_KEY is set."""
        response = client.get("/api/session/status")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error"] == "Unauthorized"

    @patch.dict(os.environ, {"API_KEY": "test-secret-key"})
    def test_valid_key_passes(self, client):
        """Requests with the correct X-Api-Key header are accepted."""
        response = client.get(
            "/api/session/status",
            headers={"X-Api-Key": "test-secret-key"},
        )
        assert response.status_code == 200

    @patch.dict(os.environ, {"API_KEY": "test-secret-key"})
    def test_wrong_key_returns_401(self, client):
        """Requests with an incorrect key are rejected."""
        response = client.get(
            "/api/session/status",
            headers={"X-Api-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_no_auth_without_env_var(self, client):
        """When API_KEY is not set the server accepts requests without a key."""
        env = {k: v for k, v in os.environ.items() if k != "API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            response = client.get("/api/session/status")
        assert response.status_code == 200


class TestResetLLMContext:
    """Tests for POST /api/llm/context/reset endpoint."""

    @patch("songs_teller.routes.force_unload_model")
    def test_reset_llm_context_success(self, mock_unload, client):
        """Test successfully resetting LLM context."""
        mock_unload.return_value = True

        response = client.post("/api/llm/context/reset")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["message"] == "LLM context reset"
        mock_unload.assert_called_once()

    @patch("songs_teller.routes.force_unload_model")
    def test_reset_llm_context_failure(self, mock_unload, client):
        """Test resetting LLM context when it fails."""
        mock_unload.return_value = False

        response = client.post("/api/llm/context/reset")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "fail" in data["message"].lower()

    @patch("songs_teller.routes.force_unload_model")
    def test_reset_llm_context_exception(self, mock_unload, client):
        """Test resetting LLM context when an exception occurs."""
        mock_unload.side_effect = Exception("Connection error db://secret@host/db")

        response = client.post("/api/llm/context/reset")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
        # Internal details must not leak into the response
        assert "secret" not in data["message"]
        assert data["message"] == "Internal server error"
