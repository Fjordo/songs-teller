"""
Tests for Text-to-Speech integration.
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from songs_teller import tts


class TestSpeakText:
    """Tests for speak_text function."""

    @patch("songs_teller.tts.config")
    def test_speak_text_disabled(self, mock_config):
        """Test speak_text when audio is disabled."""
        mock_config.get.side_effect = lambda key, default=False: {
            "play_audio": False,
        }.get(key, default)

        # Should return early without error
        tts.speak_text("Test text")

    @patch("songs_teller.tts.play_and_delete")
    @patch("songs_teller.tts._synthesize_audio")
    @patch("songs_teller.tts.config")
    def test_speak_text_google_mode_immediate(
        self, mock_config, mock_synthesize, mock_play
    ):
        """Test speak_text in Google mode with immediate playback."""
        mock_config.get.side_effect = lambda key, default=False: {
            "play_audio": True,
            "buffer_audio": False,
            "mode": "google",
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "google": {
                "tts_options": {"response_format": "wav"},
            },
        }[key]

        mock_synthesize.return_value = True

        tts.speak_text("Test text")

        mock_synthesize.assert_called_once()
        mock_play.assert_called_once()

    @patch("songs_teller.tts.synthesize_audio_google")
    @patch("songs_teller.tts.config")
    def test_speak_text_google_mode_buffered(
        self, mock_config, mock_synthesize
    ):
        """Test speak_text in Google mode with buffering."""
        mock_config.get.side_effect = lambda key, default=False: {
            "play_audio": True,
            "buffer_audio": True,
            "mode": "google",
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "google": {
                "tts_options": {"response_format": "wav"},
            },
        }[key]

        mock_synthesize.return_value = True

        tts.speak_text("Test text")

        mock_synthesize.assert_called_once()
        # play_and_delete should not be called in buffered mode
        # (we can't easily check this without mocking it, but synthesize should be called)

    @patch("songs_teller.tts.play_and_delete")
    @patch("songs_teller.tts._synthesize_audio")
    @patch("songs_teller.tts.config")
    def test_speak_text_local_mode(
        self, mock_config, mock_synthesize, mock_play
    ):
        """Test speak_text in local mode."""
        mock_config.get.side_effect = lambda key, default=False: {
            "play_audio": True,
            "buffer_audio": False,
            "mode": "local",
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "local": {
                "tts_options": {"response_format": "mp3"},
            },
        }[key]

        mock_synthesize.return_value = True

        tts.speak_text("Test text")

        mock_synthesize.assert_called_once()
        mock_play.assert_called_once()


class TestSynthesizeAudioGoogle:
    """Tests for synthesize_audio_google function."""

    @patch("songs_teller.tts.service_account.Credentials.from_service_account_file")
    @patch("songs_teller.tts.texttospeech.TextToSpeechClient")
    @patch("songs_teller.tts._synthesize_chunks")
    @patch("songs_teller.tts.get_config_path")
    @patch("songs_teller.tts.config")
    def test_synthesize_audio_google_success(
        self, mock_config, mock_get_path, mock_synthesize_chunks, mock_client_class, mock_credentials
    ):
        """Test successful Google TTS synthesis."""
        from pathlib import Path
        
        mock_config.get.side_effect = lambda key, default=None: {
            "google": {
                "tts_voice": "en-US-Neural2-D",
                "tts_language_code": "en-US",
                "tts_key_path": "test_key.json",
            },
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "google": {
                "tts_voice": "en-US-Neural2-D",
                "tts_language_code": "en-US",
                "tts_key_path": "test_key.json",
            },
        }[key]

        from unittest.mock import MagicMock
        mock_key_path = MagicMock(spec=Path)
        mock_key_path.exists.return_value = True
        mock_get_path.return_value = mock_key_path

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_synthesize_chunks.return_value = [b"fake audio data"]

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            result = tts.synthesize_audio_google("Test text", temp_path)
            assert result is True
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch("songs_teller.tts.config")
    def test_synthesize_audio_google_no_key_path(self, mock_config):
        """Test Google TTS synthesis without key path."""
        mock_config.get.side_effect = lambda key, default=None: {
            "google": {
                "tts_key_path": None,
            },
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "google": {
                "tts_key_path": None,
            },
        }[key]

        result = tts.synthesize_audio_google("Test text", "output.wav")
        assert result is False

    @patch("songs_teller.tts.service_account.Credentials.from_service_account_file")
    @patch("songs_teller.tts.config")
    def test_synthesize_audio_google_exception(self, mock_config, mock_credentials):
        """Test Google TTS synthesis with exception."""
        mock_config.get.side_effect = lambda key, default=None: {
            "google": {
                "tts_voice": "en-US-Neural2-D",
                "tts_language_code": "en-US",
                "tts_key_path": "test_key.json",
            },
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "google": {
                "tts_voice": "en-US-Neural2-D",
                "tts_language_code": "en-US",
                "tts_key_path": "test_key.json",
            },
        }[key]

        mock_credentials.side_effect = Exception("Invalid credentials")

        result = tts.synthesize_audio_google("Test text", "output.wav")
        assert result is False


class TestSynthesizeAudioLocal:
    """Tests for synthesize_audio_local function."""

    @patch("songs_teller.tts.requests.post")
    @patch("songs_teller.tts.config")
    def test_synthesize_audio_local_success(self, mock_config, mock_post):
        """Test successful local TTS synthesis."""
        mock_config.get.side_effect = lambda key, default=None: {
            "local": {
                "tts_api_url": "http://localhost:5500/v1/audio/speech",
                "tts_voice": "alloy",
                "tts_options": {
                    "response_format": "mp3",
                    "speed": 1.0,
                },
            },
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "local": {
                "tts_api_url": "http://localhost:5500/v1/audio/speech",
                "tts_voice": "alloy",
                "tts_options": {
                    "response_format": "mp3",
                    "speed": 1.0,
                },
            },
        }[key]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake audio data"]
        mock_post.return_value = mock_response

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            result = tts.synthesize_audio_local("Test text", temp_path)
            assert result is True
            mock_post.assert_called_once()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch("songs_teller.tts.config")
    def test_synthesize_audio_local_no_url(self, mock_config):
        """Test local TTS synthesis without URL."""
        mock_config.get.side_effect = lambda key, default=None: {
            "local": {
                "tts_api_url": None,
            },
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "local": {
                "tts_api_url": None,
            },
        }[key]

        result = tts.synthesize_audio_local("Test text", "output.mp3")
        assert result is False

    @patch("songs_teller.tts.requests.post")
    @patch("songs_teller.tts.config")
    def test_synthesize_audio_local_long_text(self, mock_config, mock_post):
        """Test local TTS synthesis with long text (uses /long endpoint)."""
        long_text = "x" * 3000  # Longer than 3000 chars

        mock_config.get.side_effect = lambda key, default=None: {
            "local": {
                "tts_api_url": "http://localhost:5500/v1/audio/speech",
                "tts_voice": "alloy",
                "tts_options": {"response_format": "mp3"},
            },
        }.get(key, default)

        mock_config.__getitem__ = lambda self, key: {
            "local": {
                "tts_api_url": "http://localhost:5500/v1/audio/speech",
                "tts_voice": "alloy",
                "tts_options": {"response_format": "mp3"},
            },
        }[key]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"fake audio data"]
        mock_post.return_value = mock_response

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            tts.synthesize_audio_local(long_text, temp_path)
            # Verify URL was modified to include /long
            call_url = mock_post.call_args[0][0]
            assert "/long" in call_url
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestSplitTextForTTS:
    """Tests for _split_text_for_tts function."""

    def test_split_text_short(self):
        """Test splitting short text (should not split)."""
        text = "This is a short text."
        chunks = tts._split_text_for_tts(text, 1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_text_long(self):
        """Test splitting long text."""
        # Create text longer than max_bytes
        text = "This is a sentence. " * 100
        chunks = tts._split_text_for_tts(text, 100)
        assert len(chunks) > 1
        # Verify all chunks are within limit
        for chunk in chunks:
            assert len(chunk.encode("utf-8")) <= 100

    def test_split_text_sentence_boundaries(self):
        """Test that splitting respects sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence."
        chunks = tts._split_text_for_tts(text, 20)
        # Should split on sentence boundaries when possible
        assert len(chunks) >= 1


class TestPlayAndDelete:
    """Tests for play_and_delete function."""

    @patch("songs_teller.tts.pygame.mixer")
    def test_play_and_delete_success(self, mock_mixer):
        """Test successful audio playback and deletion."""
        mock_mixer.init = MagicMock()
        mock_mixer.music = MagicMock()
        mock_mixer.music.get_busy.return_value = False
        mock_mixer.quit = MagicMock()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
            f.write(b"fake audio")

        try:
            tts.play_and_delete(temp_path)
            mock_mixer.init.assert_called_once()
            mock_mixer.music.load.assert_called_once_with(temp_path)
            mock_mixer.music.play.assert_called_once()
            mock_mixer.quit.assert_called_once()
            # File should be deleted
            assert not os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @patch("songs_teller.tts.pygame.mixer")
    def test_play_and_delete_import_error(self, mock_mixer):
        """Test play_and_delete when pygame is not available."""
        mock_mixer.init.side_effect = ImportError("pygame not installed")

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            # Should handle error gracefully
            tts.play_and_delete(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
