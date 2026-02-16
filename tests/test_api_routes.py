"""
Tests for Flask API routes.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

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
        # Add songs
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

        # Verify session was reset
        assert len(current_session["songs"]) == 0

        # LLM should be called with the songs
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
        # Add songs
        for song in sample_songs:
            client.post(
                "/api/song",
                data=json.dumps(song),
                content_type="application/json",
            )

        # Don't specify process parameter (should default to True)
        response = client.post(
            "/api/session/reset",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 200
        # LLM should be called
        mock_llm.assert_called_once()


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
        mock_unload.side_effect = Exception("Connection error")

        response = client.post("/api/llm/context/reset")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
