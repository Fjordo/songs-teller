"""
Text-to-Speech synthesis and audio playback.
"""

import os
import re
import tempfile
import time

import pygame
import requests
from google.cloud import texttospeech
from google.oauth2 import service_account

from songs_teller.config import config


def speak_text(text):
    """
    Wrapper to handle synthesis and playback based on configuration.
    """
    should_play = config.get("play_audio", False)
    should_buffer = config.get("buffer_audio", False)

    if not should_play:
        return

    mode = config.get("mode", "google")
    mode_config = config.get(mode, {})
    tts_opts = mode_config.get("tts_options", {})
    ext = tts_opts.get("response_format", "wav")

    # Determine output path
    if should_buffer:
        # Get project root for buffer file location
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        output_path = os.path.join(
            base_path, f"buffered_commentary.{ext}"
        )
        print("INFO: Buffering enabled. Generating audio for NEXT session...")
    else:
        # Temp file for immediate playback
        fd, output_path = tempfile.mkstemp(suffix=f".{ext}")
        os.close(fd)

    # Synthesize with the right backend
    if mode == "google":
        success = synthesize_audio_google(text, output_path)
    else:
        success = synthesize_audio_local(text, output_path)

    if success:
        if should_buffer:
            print(f"✅ Audio buffered to {output_path}.")
        else:
            # Play immediately (synchronous for non-buffered mode)
            play_and_delete(output_path)


# ---------------------------------------------------------------------------
# Google Cloud TTS
# ---------------------------------------------------------------------------

def synthesize_audio_google(text, output_path):
    """
    Synthesize speech using Google Cloud Text-to-Speech API.
    Handles texts longer than 5000 bytes by chunking.
    """
    try:
        google_config = config.get("google", {})
        voice_name = google_config.get("tts_voice", "en-US-Neural2-D")
        language_code = google_config.get("tts_language_code", "en-US")
        tts_key_path = google_config.get("tts_key_path")

        print(f"🎙️ Synthesizing with Google Cloud TTS (Voice: {voice_name})...")

        if not tts_key_path:
            print("❌ Error: google.tts_key_path not set in config.json.")
            return False

        # Resolve key path relative to config directory
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        key_path = os.path.join(base_path, "config", tts_key_path)

        credentials = service_account.Credentials.from_service_account_file(key_path)
        client = texttospeech.TextToSpeechClient(credentials=credentials)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        )

        # Google Cloud TTS has a 5000 bytes per request limit.
        # Split text into chunks if needed.
        max_bytes = 4500  # leave some margin
        chunks = _split_text_for_tts(text, max_bytes)

        audio_parts = []
        for i, chunk in enumerate(chunks):
            if len(chunks) > 1:
                print(f"  📝 Processing chunk {i + 1}/{len(chunks)} ({len(chunk.encode('utf-8'))} bytes)...")

            synthesis_input = texttospeech.SynthesisInput(text=chunk)
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            audio_parts.append(response.audio_content)

        # Concatenate all audio parts
        with open(output_path, "wb") as f:
            for part in audio_parts:
                f.write(part)

        print(f"💾 Audio saved to {output_path}")
        return True

    except Exception as e:
        print(f"❌ Error in Google Cloud TTS: {e}")
        return False


def _split_text_for_tts(text, max_bytes):
    """
    Split text into chunks that fit within max_bytes (UTF-8).
    Splits on sentence boundaries when possible.
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return [text]

    chunks = []
    # Split by sentences (period, exclamation, question mark followed by space)
    sentences = re.split(r'(?<=[.!?])\s+', text)

    current_chunk = ""
    for sentence in sentences:
        test_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence
        if len(test_chunk.encode("utf-8")) <= max_bytes:
            current_chunk = test_chunk
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If a single sentence exceeds max_bytes, split it by words
            if len(sentence.encode("utf-8")) > max_bytes:
                words = sentence.split()
                current_chunk = ""
                for word in words:
                    test_word = (current_chunk + " " + word).strip() if current_chunk else word
                    if len(test_word.encode("utf-8")) <= max_bytes:
                        current_chunk = test_word
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# ---------------------------------------------------------------------------
# Local Chatterbox TTS
# ---------------------------------------------------------------------------

def synthesize_audio_local(text, output_path):
    """
    Send text to local Chatterbox TTS API and save to output_path.
    """
    try:
        local_config = config.get("local", {})
        tts_url = local_config.get("tts_api_url")
        tts_voice = local_config.get("tts_voice", "default")
        tts_options = local_config.get("tts_options", {})

        if not tts_url:
            print("⚠️  Local TTS URL not configured in config.local.tts_api_url")
            return False

        # Sanitize text
        # 1. Remove text between '=' chars (e.g. === Headers ===)
        text = re.sub(r"=+.*?=+", " ", text, flags=re.DOTALL)
        # 2. Remove newlines and replace double quotes
        text = text.replace("\n", " ").replace('"', "'").strip()
        # 3. Clean up extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        # Check for long text
        if len(text) >= 3000:
            print(f"INFO: Text length {len(text)} > 3000. Using /long endpoint.")
            if not tts_url.endswith("/long"):
                if tts_url.endswith("/"):
                    tts_url = f"{tts_url}long"
                else:
                    tts_url = f"{tts_url}/long"

        print(f"🗣️  Synthesizing audio via {tts_url}...")

        payload = {
            "model": "tts-1",
            "input": text,
            "voice": tts_voice,
            "response_format": tts_options.get("response_format", "mp3"),
            "speed": tts_options.get("speed", 1),
            "stream_format": tts_options.get("stream_format", "audio"),
            "exaggeration": tts_options.get("exaggeration", 0.25),
            "cfg_weight": tts_options.get("cfg_weight", 1),
            "temperature": tts_options.get("temperature", 0.05),
            "streaming_chunk_size": tts_options.get("streaming_chunk_size", 50),
            "streaming_strategy": tts_options.get("streaming_strategy", "paragraph"),
            "streaming_buffer_size": tts_options.get("streaming_buffer_size", 1),
            "streaming_quality": tts_options.get("streaming_quality", "balanced"),
        }

        response = requests.post(tts_url, json=payload, stream=True)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"💾 Audio saved to {output_path}")
            return True
        else:
            print(f"❌ TTS Request failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error in local TTS: {e}")
        return False


# ---------------------------------------------------------------------------
# Audio Playback
# ---------------------------------------------------------------------------

def play_and_delete(file_path):
    """
    Plays the audio file using pygame and deletes it afterwards.
    Designed to run in a thread.
    """
    try:
        print(f"🔊 Playing audio: {file_path}")
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        pygame.mixer.quit()

        # Clean up
        try:
            os.remove(file_path)
            print(f"🗑️  Deleted played file: {file_path}")
        except Exception as e:
            print(f"⚠️ Warning: Could not delete {file_path}: {e}")

    except ImportError:
        print("❌ Error: pygame is not installed.")
    except Exception as e:
        print(f"❌ Error playing audio: {e}")
