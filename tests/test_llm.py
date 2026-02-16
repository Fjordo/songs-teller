"""
Tests for LLM integration.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from songs_teller import llm


class TestProcessWithLLM:
    """Tests for process_with_llm function."""

    def test_process_with_llm_empty_songs(self):
        """Test processing with empty song list."""
        # Should return early without error
        llm.process_with_llm([])

    @patch("songs_teller.llm.speak_text")
    @patch("songs_teller.llm._llm_google")
    @patch("songs_teller.llm.config")
    @patch("songs_teller.llm.os.path.exists")
    @patch("builtins.open", create=True)
    def test_process_with_llm_google_mode(
        self, mock_open, mock_exists, mock_config_module, mock_llm_google, mock_speak, sample_songs
    ):
        """Test processing songs with Google mode."""
        # Mock config as a dictionary
        config_dict = {
            "mode": "google",
            "prompt_file": "prompt.txt",
            "google": {"llm_model": "gemini-2.0-flash"},
        }
        
        # Replace the config module's dict
        mock_config_module.clear()
        mock_config_module.update(config_dict)
        mock_config_module.get = lambda key, default=None: config_dict.get(key, default)
        mock_config_module.__getitem__ = lambda key: config_dict[key]
        
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "Analyze these songs:\n{songs_list}"
        mock_open.return_value.__enter__.return_value = mock_file

        mock_llm_google.return_value = "Test commentary"

        llm.process_with_llm(sample_songs)

        mock_llm_google.assert_called_once()
        mock_speak.assert_called_once_with("Test commentary")

    @patch("songs_teller.llm.speak_text")
    @patch("songs_teller.llm._llm_local")
    @patch("songs_teller.llm.config")
    @patch("songs_teller.llm.os.path.exists")
    @patch("builtins.open", create=True)
    def test_process_with_llm_local_mode(
        self, mock_open, mock_exists, mock_config_module, mock_llm_local, mock_speak, sample_songs
    ):
        """Test processing songs with local mode."""
        config_dict = {
            "mode": "local",
            "prompt_file": "prompt.txt",
            "local": {"llm_model": "llama3.1"},
        }
        
        mock_config_module.clear()
        mock_config_module.update(config_dict)
        mock_config_module.get = lambda key, default=None: config_dict.get(key, default)
        mock_config_module.__getitem__ = lambda key: config_dict[key]
        
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "Analyze these songs:\n{songs_list}"
        mock_open.return_value.__enter__.return_value = mock_file

        mock_llm_local.return_value = "Test commentary"

        llm.process_with_llm(sample_songs)

        mock_llm_local.assert_called_once()
        mock_speak.assert_called_once_with("Test commentary")

    @patch("songs_teller.llm.speak_text")
    @patch("songs_teller.llm._llm_google")
    @patch("songs_teller.llm.config")
    def test_process_with_llm_no_content(self, mock_config_module, mock_llm_google, mock_speak, sample_songs):
        """Test processing when LLM returns None."""
        config_dict = {
            "mode": "google",
            "prompt_file": "prompt.txt",
            "google": {"llm_model": "gemini-2.0-flash"},
        }
        
        mock_config_module.clear()
        mock_config_module.update(config_dict)
        mock_config_module.get = lambda key, default=None: config_dict.get(key, default)
        
        mock_llm_google.return_value = None

        llm.process_with_llm(sample_songs)

        # speak_text should not be called if content is None
        mock_speak.assert_not_called()


class TestLLMGoogle:
    """Tests for _llm_google function."""

    @patch("songs_teller.llm.os.environ.get")
    @patch("songs_teller.llm.ChatGoogleGenerativeAI")
    def test_llm_google_success(self, mock_chat_class, mock_env_get):
        """Test successful Google LLM call."""
        mock_env_get.return_value = "test_api_key"
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Test response"
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm_instance

        result = llm._llm_google("gemini-2.0-flash", "Test prompt")

        assert result == "Test response"
        mock_chat_class.assert_called_once()
        mock_llm_instance.invoke.assert_called_once_with("Test prompt")

    @patch("songs_teller.llm.os.environ.get")
    def test_llm_google_no_api_key(self, mock_env_get):
        """Test Google LLM call without API key."""
        mock_env_get.return_value = None

        result = llm._llm_google("gemini-2.0-flash", "Test prompt")

        assert result is None


class TestLLMLocal:
    """Tests for _llm_local function."""

    @patch("songs_teller.llm.requests.post")
    def test_llm_local_success(self, mock_post, mock_config):
        """Test successful local LLM call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Test response"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        mode_config = {"llm_api_url": "http://localhost:11434", "llm_model": "llama3.1"}

        result = llm._llm_local("llama3.1", mode_config, "Test prompt")

        assert result == "Test response"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["model"] == "llama3.1"
        assert call_args[1]["json"]["prompt"] == "Test prompt"

    @patch("songs_teller.llm.requests.post")
    def test_llm_local_url_with_api_path(self, mock_post):
        """Test local LLM call with URL containing /api/ path."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Test response"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        mode_config = {"llm_api_url": "http://localhost:11434/api/generate", "llm_model": "llama3.1"}

        result = llm._llm_local("llama3.1", mode_config, "Test prompt")

        assert result == "Test response"
        # Verify URL was cleaned
        call_url = mock_post.call_args[0][0]
        assert "/api/generate" in call_url
        assert not call_url.startswith("http://localhost:11434/api/api")

    @patch("songs_teller.llm.requests.post")
    def test_llm_local_request_error(self, mock_post):
        """Test local LLM call with request error."""
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        mode_config = {"llm_api_url": "http://localhost:11434", "llm_model": "llama3.1"}

        with pytest.raises(requests.exceptions.RequestException):
            llm._llm_local("llama3.1", mode_config, "Test prompt")


class TestForceUnloadModel:
    """Tests for force_unload_model function."""

    @patch("songs_teller.llm.requests.post")
    def test_force_unload_model_success(self, mock_post):
        """Test successfully unloading model."""
        mock_post.return_value = MagicMock()

        result = llm.force_unload_model("http://localhost:11434", "llama3.1")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert call_args[1]["json"]["keep_alive"] == 0

    @patch("songs_teller.llm.requests.post")
    def test_force_unload_model_url_cleanup(self, mock_post):
        """Test URL cleanup in force_unload_model."""
        mock_post.return_value = MagicMock()

        llm.force_unload_model("http://localhost:11434/api/generate", "llama3.1")

        # Verify URL was cleaned
        call_url = mock_post.call_args[0][0]
        assert call_url == "http://localhost:11434/api/generate"

    @patch("songs_teller.llm.requests.post")
    def test_force_unload_model_error(self, mock_post):
        """Test unloading model with error."""
        mock_post.side_effect = Exception("Connection error")

        result = llm.force_unload_model("http://localhost:11434", "llama3.1")

        assert result is False
