"""
Configuration loader for Song Teller.
"""

import json
from typing import Any, Dict

from dotenv import load_dotenv

from songs_teller.utils import get_config_path

# Shared config dict — populated by load_config(), imported by other modules.
config: Dict[str, Any] = {}


def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json and .env into the shared dict.
    
    Returns:
        The loaded configuration dictionary
    """
    load_dotenv()
    try:
        config_path = get_config_path("config.json")
        
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
    except Exception as e:
        print(f"⚠️  Error loading config: {e}")
    return config
