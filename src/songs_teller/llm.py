"""
LLM integration — Google Gemini and local Ollama.
"""

import os

import requests
from langchain_google_genai import ChatGoogleGenerativeAI

from songs_teller.config import config
from songs_teller.tts import speak_text


def process_with_llm(songs):
    """
    Send the list of songs to the configured LLM for processing.
    Dispatches to Google Gemini or local Ollama based on config mode.
    """
    try:
        if not songs:
            return

        mode = config.get("mode", "google")
        mode_config = config.get(mode, {})
        model = mode_config.get("llm_model", "gemini-2.0-flash")
        prompt_file = config.get("prompt_file", "prompt.txt")

        # Resolve prompt file path relative to config directory
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        prompt_path = os.path.join(base_path, "config", prompt_file)

        prompt_template = ""
        try:
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_template = f.read()
            else:
                print(f"⚠️  Prompt file not found at: {prompt_path}")
                prompt_template = "Analyze these songs:\n{songs_list}"
        except Exception as e:
            print(f"⚠️  Could not read prompt file: {e}")
            prompt_template = "Analyze these songs:\n{songs_list}"

        # Format song list
        songs_list_str = "\n".join([f"- {s['artist']} - {s['title']}" for s in songs])
        final_prompt = prompt_template.replace("{songs_list}", songs_list_str)

        # Dispatch to the right LLM backend
        if mode == "google":
            content = _llm_google(model, final_prompt)
        else:
            content = _llm_local(model, mode_config, final_prompt)

        if content is None:
            return

        print(f"\n{'=' * 20} LLM Analysis {'=' * 20}\n")
        print(content)
        print(f"\n{'=' * 54}\n")

        # Speak the response if enabled
        speak_text(content)

    except Exception as e:
        print(f"❌ Error in process_with_llm: {e}")


def _llm_google(model, prompt):
    """Call Google Gemini via LangChain."""
    api_key = os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
    if not api_key:
        print(
            "❌ Error: GOOGLE_AI_STUDIO_API_KEY not found in .env. Please set it to use Google LLM."
        )
        return None

    print(f"🤖 Sending request to Google Gemini ({model})...")
    llm = ChatGoogleGenerativeAI(
        model=model, google_api_key=api_key, temperature=0.7
    )
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _llm_local(model, mode_config, prompt):
    """Call local Ollama LLM via REST API."""
    base_url = mode_config.get("llm_api_url", "http://localhost:11434")
    # Ensure we have the base URL without path suffixes
    if "/api/" in base_url:
        base_url = base_url.split("/api/")[0]

    url = f"{base_url}/api/generate"
    print(f"🤖 Sending request to Ollama ({model}) at {base_url}...")

    response = requests.post(
        url,
        json={"model": model, "prompt": prompt, "stream": False},
    )
    response.raise_for_status()
    return response.json().get("response", "")


def force_unload_model(base_url, model):
    """
    Helper function to force unload Ollama model.
    """
    try:
        if "/api/generate" in base_url:
            base_url = base_url.split("/api/generate")[0]

        url = f"{base_url}/api/generate"
        payload = {"model": model, "keep_alive": 0}

        print(f"🧠 Unloading model {model}...")
        requests.post(url, json=payload)
        return True
    except Exception as e:
        print(f"⚠️ Error unloading model: {e}")
        return False
