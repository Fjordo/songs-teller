"""
Utility functions for Songs Teller.
"""

import os
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path object pointing to the project root
    """
    # Get the directory containing this file (src/songs_teller/)
    current_file = Path(__file__).resolve()
    # Go up: src/songs_teller -> src -> project root
    return current_file.parent.parent.parent


def get_config_path(filename: str) -> Path:
    """
    Get the path to a file in the config directory.
    
    Args:
        filename: Name of the config file
        
    Returns:
        Path object pointing to the config file
    """
    return get_project_root() / "config" / filename


def normalize_ollama_url(url: str) -> str:
    """
    Normalize Ollama API URL by removing /api/ suffix if present.
    
    Args:
        url: The URL to normalize
        
    Returns:
        Normalized URL without /api/ suffix
    """
    if "/api/" in url:
        return url.split("/api/")[0]
    return url
