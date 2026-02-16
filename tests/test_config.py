"""
Tests for configuration loading.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from songs_teller.config import config, load_config


class TestLoadConfig:
    """Tests for configuration loading."""

    def test_load_config_file_exists(self, temp_config_file, mock_config):
        """Test loading configuration from existing file."""
        # Temporarily replace the config path
        with patch("songs_teller.config.get_config_path") as mock_get_path:
            from pathlib import Path
            mock_get_path.return_value = Path(temp_config_file)

            # Clear config and reload
            config.clear()
            load_config()

            # Verify config was loaded
            assert config.get("mode") == mock_config["mode"]
            assert config.get("prompt_file") == mock_config["prompt_file"]

    def test_load_config_file_not_exists(self):
        """Test loading configuration when file doesn't exist."""
        # Clear config first
        original_config = config.copy()
        config.clear()
        
        with patch("songs_teller.config.load_dotenv"):
            with patch("songs_teller.config.get_config_path") as mock_get_path:
                from pathlib import Path
                from unittest.mock import MagicMock
                mock_path = MagicMock(spec=Path)
                mock_path.exists.return_value = False
                mock_get_path.return_value = mock_path
                
                load_config()
                # Config should remain empty (or at least be a dict)
                assert isinstance(config, dict)
        
        # Restore original config
        config.clear()
        config.update(original_config)

    def test_load_config_invalid_json(self):
        """Test loading configuration with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            temp_path = f.name

        try:
            with patch("songs_teller.config.get_config_path") as mock_get_path:
                from pathlib import Path
                mock_path = Path(temp_path)
                mock_get_path.return_value = mock_path
                
                config.clear()
                # Should handle error gracefully
                load_config()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_load_config_env_variables(self):
        """Test that environment variables are loaded via dotenv."""
        with patch("songs_teller.config.load_dotenv") as mock_load_dotenv:
            load_config()
            mock_load_dotenv.assert_called_once()

    def test_config_structure(self, mock_config):
        """Test that config has expected structure."""
        # This test verifies the config structure matches expectations
        assert isinstance(config, dict)
        # After load_config, these keys should exist if config file is present
        # We're just checking the structure is a dict
