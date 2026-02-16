"""
Tests for Flask application creation and configuration.
"""

import pytest

from songs_teller.api import create_app


class TestCreateApp:
    """Tests for create_app function."""

    def test_create_app(self):
        """Test that create_app returns a Flask application."""
        app = create_app()
        assert app is not None
        assert app.config["TESTING"] == False  # Default config

    def test_create_app_routes_registered(self):
        """Test that routes are registered in the app."""
        app = create_app()
        # Check that routes are registered
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert "/api/song" in rules
        assert "/api/session/reset" in rules
        assert "/api/session/status" in rules
        assert "/api/llm/context/reset" in rules

    def test_create_app_config_loaded(self):
        """Test that configuration is loaded when app is created."""
        app = create_app()
        # App should be created without errors even if config file doesn't exist
        assert app is not None
