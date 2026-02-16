"""
LLM integration — Google Gemini and local Ollama.
"""

import os
from typing import Dict, List, Optional

import requests
from langchain_google_genai import ChatGoogleGenerativeAI

from songs_teller.config import config
from songs_teller.tts import speak_text
from songs_teller.utils import get_config_path, normalize_ollama_url

# Constants
DEFAULT_MODE = "google"
DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"
DEFAULT_LOCAL_MODEL = "llama3.1"
DEFAULT_PROMPT_FILE = "prompt.txt"
DEFAULT_PROMPT_TEMPLATE = "Analyze these songs:\n{songs_list}"


def process_with_llm(songs: List[Dict[str, str]]) -> None:
    """
    Send the list of songs to the configured LLM for processing.
    Dispatches to Google Gemini or local Ollama based on config mode.
    
    Args:
        songs: List of song dictionaries with 'artist' and 'title' keys
    """
    if not songs:
        return

    try:
        mode = config.get("mode", DEFAULT_MODE)
        mode_config = config.get(mode, {})
        model = mode_config.get("llm_model", DEFAULT_GOOGLE_MODEL if mode == "google" else DEFAULT_LOCAL_MODEL)
        prompt_file = config.get("prompt_file", DEFAULT_PROMPT_FILE)

        prompt_template = _load_prompt_template(prompt_file)
        songs_list_str = _format_song_list(songs)
        final_prompt = prompt_template.replace("{songs_list}", songs_list_str)

        content = _call_llm(mode, model, mode_config, final_prompt)
        
        if content:
            _display_and_speak(content)
    except Exception as e:
        print(f"❌ Error in process_with_llm: {e}")


def _load_prompt_template(prompt_file: str) -> str:
    """Load prompt template from file or return default."""
    try:
        prompt_path = get_config_path(prompt_file)
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        print(f"⚠️  Prompt file not found at: {prompt_path}")
    except Exception as e:
        print(f"⚠️  Could not read prompt file: {e}")
    return DEFAULT_PROMPT_TEMPLATE


def _format_song_list(songs: List[Dict[str, str]]) -> str:
    """Format list of songs into a string."""
    return "\n".join([f"- {song['artist']} - {song['title']}" for song in songs])


def _call_llm(mode: str, model: str, mode_config: Dict, prompt: str) -> Optional[str]:
    """Call the appropriate LLM backend based on mode."""
    if mode == "google":
        return _llm_google(model, prompt)
    return _llm_local(model, mode_config, prompt)


def _display_and_speak(content: str) -> None:
    """Display LLM content and speak it if enabled."""
    print(f"\n{'=' * 20} LLM Analysis {'=' * 20}\n")
    print(content)
    print(f"\n{'=' * 54}\n")
    speak_text(content)


def _llm_google(model: str, prompt: str) -> Optional[str]:
    """
    Call Google Gemini via LangChain.
    
    Args:
        model: Model name to use
        prompt: The prompt to send
        
    Returns:
        LLM response content or None if error
    """
    api_key = os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_AI_STUDIO_API_KEY not found in .env. Please set it to use Google LLM.")
        return None

    print(f"🤖 Sending request to Google Gemini ({model})...")
    llm_client = ChatGoogleGenerativeAI(
        model=model, google_api_key=api_key, temperature=0.7
    )
    response = llm_client.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _llm_local(model: str, mode_config: Dict, prompt: str) -> Optional[str]:
    """
    Call local Ollama LLM via REST API.
    
    Args:
        model: Model name to use
        mode_config: Configuration dictionary for local mode
        prompt: The prompt to send
        
    Returns:
        LLM response content or None if error
    """
    base_url = mode_config.get("llm_api_url", "http://localhost:11434")
    base_url = normalize_ollama_url(base_url)
    
    url = f"{base_url}/api/generate"
    print(f"🤖 Sending request to Ollama ({model}) at {base_url}...")

    try:
        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.RequestException as e:
        print(f"❌ Error calling Ollama: {e}")
        return None


def force_unload_model(base_url: str, model: str) -> bool:
    """
    Force unload Ollama model to clear context.
    
    Args:
        base_url: Base URL of Ollama API
        model: Model name to unload
        
    Returns:
        True if successful, False otherwise
    """
    try:
        base_url = normalize_ollama_url(base_url)
        url = f"{base_url}/api/generate"
        payload = {"model": model, "keep_alive": 0}

        print(f"🧠 Unloading model {model}...")
        requests.post(url, json=payload)
        return True
    except Exception as e:
        print(f"⚠️ Error unloading model: {e}")
        return False
