"""
Text-to-Speech synthesis and audio playback.
"""

import re
import tempfile
import time
from typing import List, Optional

import pygame
import requests
from google.cloud import texttospeech
from google.oauth2 import service_account

from songs_teller.config import config
from songs_teller.utils import get_config_path, get_project_root

# Constants
DEFAULT_MODE = "google"
GOOGLE_TTS_MAX_BYTES = 4500  # Leave margin below 5000 byte limit
LOCAL_TTS_LONG_TEXT_THRESHOLD = 3000
AUDIO_POLL_INTERVAL = 0.1  # seconds


def speak_text(text: str) -> None:
    """
    Wrapper to handle synthesis and playback based on configuration.
    
    Args:
        text: Text to synthesize and speak
    """
    if not config.get("play_audio", False):
        return

    mode = config.get("mode", DEFAULT_MODE)
    mode_config = config.get(mode, {})
    tts_opts = mode_config.get("tts_options", {})
    ext = tts_opts.get("response_format", "wav")
    should_buffer = config.get("buffer_audio", False)

    output_path = _get_output_path(ext, should_buffer)
    
    success = _synthesize_audio(text, output_path, mode)
    
    if success:
        if should_buffer:
            print(f"✅ Audio buffered to {output_path}.")
        else:
            play_and_delete(str(output_path))


def _get_output_path(ext: str, should_buffer: bool) -> str:
    """Get output path for audio file."""
    if should_buffer:
        output_path = get_project_root() / f"buffered_commentary.{ext}"
        print("INFO: Buffering enabled. Generating audio for NEXT session...")
        return str(output_path)
    else:
        fd, output_path = tempfile.mkstemp(suffix=f".{ext}")
        import os
        os.close(fd)  # Close file descriptor
        return output_path


def _synthesize_audio(text: str, output_path: str, mode: str) -> bool:
    """Synthesize audio using the appropriate backend."""
    if mode == "google":
        return synthesize_audio_google(text, output_path)
    return synthesize_audio_local(text, output_path)


# ---------------------------------------------------------------------------
# Google Cloud TTS
# ---------------------------------------------------------------------------

def synthesize_audio_google(text: str, output_path: str) -> bool:
    """
    Synthesize speech using Google Cloud Text-to-Speech API.
    Handles texts longer than 5000 bytes by chunking.
    
    Args:
        text: Text to synthesize
        output_path: Path to save the audio file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        google_config = config.get("google", {})
        voice_name = google_config.get("tts_voice", "en-US-Neural2-D")
        language_code = google_config.get("tts_language_code", "en-US")
        tts_key_path = google_config.get("tts_key_path")

        if not tts_key_path:
            print("❌ Error: google.tts_key_path not set in config.json.")
            return False

        key_path = get_config_path(tts_key_path)
        if not key_path.exists():
            print(f"❌ Error: Key file not found at {key_path}")
            return False

        print(f"🎙️ Synthesizing with Google Cloud TTS (Voice: {voice_name})...")

        credentials = service_account.Credentials.from_service_account_file(str(key_path))
        client = texttospeech.TextToSpeechClient(credentials=credentials)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        )

        chunks = _split_text_for_tts(text, GOOGLE_TTS_MAX_BYTES)
        audio_parts = _synthesize_chunks(client, chunks, voice, audio_config)

        # Concatenate all audio parts
        with open(output_path, "wb") as f:
            for part in audio_parts:
                f.write(part)

        print(f"💾 Audio saved to {output_path}")
        return True

    except Exception as e:
        print(f"❌ Error in Google Cloud TTS: {e}")
        return False


def _synthesize_chunks(client, chunks: List[str], voice, audio_config) -> List[bytes]:
    """Synthesize multiple text chunks and return audio parts."""
    audio_parts = []
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            chunk_size = len(chunk.encode("utf-8"))
            print(f"  📝 Processing chunk {i + 1}/{len(chunks)} ({chunk_size} bytes)...")

        synthesis_input = texttospeech.SynthesisInput(text=chunk)
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        audio_parts.append(response.audio_content)
    return audio_parts


def _split_text_for_tts(text: str, max_bytes: int) -> List[str]:
    """
    Split text into chunks that fit within max_bytes (UTF-8).
    Splits on sentence boundaries when possible.
    
    Args:
        text: Text to split
        max_bytes: Maximum bytes per chunk
        
    Returns:
        List of text chunks
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return [text]

    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current_chunk = ""

    for sentence in sentences:
        test_chunk = (f"{current_chunk} {sentence}").strip() if current_chunk else sentence
        
        if len(test_chunk.encode("utf-8")) <= max_bytes:
            current_chunk = test_chunk
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = _split_long_sentence(sentence, max_bytes, chunks)

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_long_sentence(sentence: str, max_bytes: int, chunks: List[str]) -> str:
    """Split a sentence that exceeds max_bytes by words."""
    if len(sentence.encode("utf-8")) <= max_bytes:
        return sentence

    words = sentence.split()
    current_chunk = ""
    
    for word in words:
        test_word = f"{current_chunk} {word}".strip() if current_chunk else word
        if len(test_word.encode("utf-8")) <= max_bytes:
            current_chunk = test_word
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = word
    
    return current_chunk


# ---------------------------------------------------------------------------
# Local Chatterbox TTS
# ---------------------------------------------------------------------------

def synthesize_audio_local(text: str, output_path: str) -> bool:
    """
    Send text to local Chatterbox TTS API and save to output_path.
    
    Args:
        text: Text to synthesize
        output_path: Path to save the audio file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        local_config = config.get("local", {})
        tts_url = local_config.get("tts_api_url")
        tts_voice = local_config.get("tts_voice", "default")
        tts_options = local_config.get("tts_options", {})

        if not tts_url:
            print("⚠️  Local TTS URL not configured in config.local.tts_api_url")
            return False

        text = _sanitize_text(text)
        tts_url = _adjust_url_for_long_text(tts_url, len(text))

        print(f"🗣️  Synthesizing audio via {tts_url}...")

        payload = _build_tts_payload(text, tts_voice, tts_options)
        response = requests.post(tts_url, json=payload, stream=True)

        if response.status_code == 200:
            _save_audio_stream(response, output_path)
            print(f"💾 Audio saved to {output_path}")
            return True
        else:
            print(f"❌ TTS Request failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error in local TTS: {e}")
        return False


def _sanitize_text(text: str) -> str:
    """Sanitize text for TTS by removing formatting and cleaning up."""
    # Remove text between '=' chars (e.g. === Headers ===)
    text = re.sub(r"=+.*?=+", " ", text, flags=re.DOTALL)
    # Remove newlines and replace double quotes
    text = text.replace("\n", " ").replace('"', "'").strip()
    # Clean up extra spaces
    return re.sub(r"\s+", " ", text).strip()


def _adjust_url_for_long_text(url: str, text_length: int) -> str:
    """Adjust URL to use /long endpoint for long texts."""
    if text_length >= LOCAL_TTS_LONG_TEXT_THRESHOLD and not url.endswith("/long"):
        print(f"INFO: Text length {text_length} >= {LOCAL_TTS_LONG_TEXT_THRESHOLD}. Using /long endpoint.")
        return f"{url.rstrip('/')}/long"
    return url


def _build_tts_payload(text: str, voice: str, options: dict) -> dict:
    """Build payload for TTS API request."""
    return {
        "model": "tts-1",
        "input": text,
        "voice": voice,
        "response_format": options.get("response_format", "mp3"),
        "speed": options.get("speed", 1),
        "stream_format": options.get("stream_format", "audio"),
        "exaggeration": options.get("exaggeration", 0.25),
        "cfg_weight": options.get("cfg_weight", 1),
        "temperature": options.get("temperature", 0.05),
        "streaming_chunk_size": options.get("streaming_chunk_size", 50),
        "streaming_strategy": options.get("streaming_strategy", "paragraph"),
        "streaming_buffer_size": options.get("streaming_buffer_size", 1),
        "streaming_quality": options.get("streaming_quality", "balanced"),
    }


def _save_audio_stream(response, output_path: str) -> None:
    """Save streaming audio response to file."""
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)


# ---------------------------------------------------------------------------
# Audio Playback
# ---------------------------------------------------------------------------

def play_and_delete(file_path: str) -> None:
    """
    Plays the audio file using pygame and deletes it afterwards.
    Designed to run in a thread.
    
    Args:
        file_path: Path to the audio file to play
    """
    try:
        print(f"🔊 Playing audio: {file_path}")
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(AUDIO_POLL_INTERVAL)

        pygame.mixer.quit()
        _delete_file(file_path)

    except ImportError:
        print("❌ Error: pygame is not installed.")
    except Exception as e:
        print(f"❌ Error playing audio: {e}")


def _delete_file(file_path: str) -> None:
    """Delete a file, handling errors gracefully."""
    try:
        import os
        os.remove(file_path)
        print(f"🗑️  Deleted played file: {file_path}")
    except Exception as e:
        print(f"⚠️ Warning: Could not delete {file_path}: {e}")
