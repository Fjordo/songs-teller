"""
Configuration loader for Song Teller.
"""

import json
import os

from dotenv import load_dotenv

# Shared config dict — populated by load_config(), imported by other modules.
config = {}


def load_config():
    """Load configuration from config.json and .env into the shared dict."""
    load_dotenv()
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_path, "config.json")

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
    except Exception as e:
        print(f"⚠️  Error loading config: {e}")
    return config
