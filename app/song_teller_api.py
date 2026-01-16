#!/usr/bin/env python3
"""
Song Teller API Server
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import requests
import tempfile
import pygame
import shutil
import threading
import time
import re

app = Flask(__name__)

# In-memory storage for current song session
current_session = {
    'songs': [],
    'started_at': None,
    'last_updated': None
}


@app.route('/api/song', methods=['POST'])
def add_song():
    """
    Add a song to the current session.
    
    Expected JSON body:
    {
        "artist": "Artist Name",
        "title": "Song Title"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        artist = data.get('artist')
        title = data.get('title')
        
        if not artist or not title:
            return jsonify({'error': 'Both artist and title are required'}), 400
        
        song = {
            'artist': artist,
            'title': title,
            'timestamp': datetime.now().isoformat()
        }
        
        # Check for duplicates
        is_duplicate = any(
            s['artist'] == artist and s['title'] == title 
            for s in current_session['songs']
        )
        
        if not is_duplicate:
            current_session['songs'].append(song)
            current_session['last_updated'] = datetime.now().isoformat()
            
            if current_session['started_at'] is None:
                current_session['started_at'] = datetime.now().isoformat()
            
            print(f"✅ Added: {artist} - {title} (Total: {len(current_session['songs'])})")
            
            return jsonify({
                'status': 'success',
                'message': 'Song added',
                'total_songs': len(current_session['songs'])
            }), 200
        else:
            print(f"⏭️  Skipped duplicate: {artist} - {title}")
            return jsonify({
                'status': 'skipped',
                'message': 'Song already in session',
                'total_songs': len(current_session['songs'])
            }), 200
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/reset', methods=['POST'])
def reset_session():
    """
    Reset the current session and optionally process the songs.
    
    Optional JSON body:
    {
        "process": true  // If true, process songs before resetting
    }
    """
    try:
        data = request.get_json() or {}
        should_process = data.get('process', True)
        
        if should_process and len(current_session['songs']) > 0:
            print(f"\n{'='*60}")
            print(f"🔄 Closing Session with {len(current_session['songs'])} songs")
            print(f"{'='*60}\n")
            
            # Save to file
            if (config.get('save_session', False)):
                save_session_to_file(current_session['songs'])

            # AUDIO BUFFERING: Asynchronous Playback
            if config.get('buffer_audio', False) and config.get('play_audio', False):
                 # Determine extension
                 tts_opts = config.get('tts_options', {})
                 ext = tts_opts.get('response_format', 'mp3')
                 
                 buffer_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'buffered_commentary.{ext}')
                 if os.path.exists(buffer_file):
                     # Move to a temp playing file to free up the buffer path for the new generation
                     playing_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'playing_commentary.{ext}')
                     
                     # Ensure we overwrite if exists (though play_and_delete should clean it)
                     if os.path.exists(playing_file):
                         try: os.remove(playing_file)
                         except: pass
                         
                     shutil.move(buffer_file, playing_file)
                     print(f"🔊 Starting async playback of: {playing_file}")
                     
                     # Play in a separate thread so we don't block
                     playback_thread = threading.Thread(target=play_and_delete, args=(playing_file,))
                     playback_thread.start()
                 else:
                     print("ℹ️  No buffered audio found. Nothing to play yet.")

            # Query LLM about the songs/artists (Generates new buffer)
            process_with_llm(current_session['songs'])
        
        song_count = len(current_session['songs'])
        
        # Reset session
        current_session['songs'] = []
        current_session['started_at'] = None
        current_session['last_updated'] = None
        
        print(f"🔄 Session reset (processed {song_count} songs)\n")
        
        return jsonify({
            'status': 'success',
            'message': 'Session reset',
            'songs_processed': song_count
        }), 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/status', methods=['GET'])
def get_status():
    """Get current session status."""
    return jsonify({
        'song_count': len(current_session['songs']),
        'started_at': current_session['started_at'],
        'last_updated': current_session['last_updated'],
        'songs': current_session['songs']
    }), 200


def save_session_to_file(songs):
    """Save songs to a JSON file with timestamp."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"song_session_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Session saved to: {filename}")
    except Exception as e:
        print(f"⚠️  Error saving to file: {e}")



def load_config():
    """Load configuration from JSON file."""
    try:
        # Config is in the *same* directory as this script (app/config.json)
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_path, 'config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"⚠️  Error loading config: {e}")
        return {}


def process_with_llm(songs):
    """
    Send the list of songs to the configured LLM for processing using LangChain.
    """
    try:
        from langchain_ollama import OllamaLLM
        
        if not songs:
            return
        
        # Default settings
        api_url = config.get('llm_api_url', 'http://localhost:11434') # Base URL for LangChain/Ollama
        model = config.get('llm_model', 'llama3.1')
        prompt_file = config.get('prompt_file', 'prompt.txt')
        
        # Resolve prompt file path
        base_path = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(base_path, prompt_file)
        
        prompt_template = ""
        try:
           if os.path.exists(prompt_path):
               with open(prompt_path, 'r', encoding='utf-8') as f:
                   prompt_template = f.read()
           else:
               print(f"⚠️  Prompt file not found at: {prompt_path}")
               prompt_template = "Analyze these songs:\n{songs_list}"
        except Exception as e:
             print(f"⚠️  Could not read prompt file: {e}")
             prompt_template = "Analyze these songs:\n{songs_list}"

        # Format song list
        songs_list_str = "\n".join([f"- {s['artist']} - {s['title']}" for s in songs])
        final_prompt = prompt_template.replace('{songs_list}', songs_list_str)
        
        print(f"🤖 Sending request to LLM ({model}) via LangChain (OllamaLLM)...")
        
        # Initialize LangChain Ollama wrapper
        # Note: base_url should be the host, e.g. http://localhost:11434
        # If the user put '/api/generate' in config, we might need to strip it, 
        # but LangChain usually expects the base URL.
        # Let's clean it just in case.
        base_url = api_url.replace("/api/generate", "")
        
        llm = OllamaLLM(model=model, base_url=base_url)
        
        # Invoke the model
        response = llm.invoke(final_prompt)
        
        print(f"\n{'='*20} LLM Analysis {'='*20}\n")
        print(response)
        print(f"\n{'='*54}\n")

        # Speak the response if enabled
        speak_text(response)
        
        # Unload model to clear context
        force_unload_model(base_url, model)

    except ImportError:
         print(f"❌ Error: langchain-ollama is not installed. Please run: pip install -r requirements.txt")
    except Exception as e:
         print(f"❌ Error in process_with_llm: {e}")


def speak_text(text):
    """
    Wrapper to handle synthesis and playback based on configuration.
    """
    config = load_config()
    should_play = config.get('play_audio', False)
    should_buffer = config.get('buffer_audio', False)
    
    if not should_play:
        return

    tts_opts = config.get('tts_options', {})
    ext = tts_opts.get('response_format', 'mp3')

    # Determine output path
    if should_buffer:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'buffered_commentary.{ext}')
        print("INFO: Buffering enabled. Generating audio for NEXT session...")
    else:
        # Temp file for immediate playback
        fd, output_path = tempfile.mkstemp(suffix=f'.{ext}')
        os.close(fd)

    # Synthesize
    success = synthesize_audio(text, output_path)
    
    if success:
        if should_buffer:
            print(f"✅ Audio buffered to {output_path}.")
        else:
            # Play immediately (synchronous for non-buffered mode)
            play_and_delete(output_path)


def synthesize_audio(text, output_path):
    """
    Sends text to TTS API and saves to output_path.
    Returns True if success.
    """
    try:
        config = load_config()
        tts_url = config.get('tts_api_url')
        tts_voice = config.get('tts_voice')
        
        if not tts_url:
            print("⚠️  TTS URL not configured.")
            return False

        # Sanitize text
        # 1. Remove text between '=' chars (e.g. === Headers ===)
        text = re.sub(r'=+.*?=+', ' ', text, flags=re.DOTALL)
        # 2. Remove newlines and replace double quotes
        text = text.replace('\n', ' ').replace('"', "'").strip()
        # 3. Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Check for long text
        if len(text) >= 3000:
            print(f"INFO: Text length {len(text)} > 3000. Using /long endpoint.")
            if not tts_url.endswith('/long'):
                 if tts_url.endswith('/'):
                     tts_url = f"{tts_url}long"
                 else:
                     tts_url = f"{tts_url}/long"

        print(f"🗣️  Synthesizing audio via {tts_url}...")
        
        # Default extended params
        tts_options = config.get('tts_options', {})
        
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
            "streaming_quality": tts_options.get("streaming_quality", "balanced")
        }
        
        response = requests.post(tts_url, json=payload, stream=True)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"💾 Audio saved to {output_path}")
            return True
        else:
            print(f"❌ TTS Request failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
         print(f"❌ Error in synthesize_audio: {e}")
         return False

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
            # time.sleep is better for threading than pygame.time.Clock when not in a main loop
            time.sleep(0.1)
            
        pygame.mixer.quit()
        
        # Clean up
        try:
            os.remove(file_path)
            print(f"🗑️  Deleted played file: {file_path}")
        except Exception as e:
            print(f"⚠️ Warning: Could not delete {file_path}: {e}")
            
    except ImportError:
         print(f"❌ Error: pygame is not installed.")
    except Exception as e:
         print(f"❌ Error playing audio: {e}")



def force_unload_model(base_url, model):
    """
    Helper function to force unload Ollama model.
    """
    try:
        # Handle cases where user might have put full endpoint in config
        if '/api/generate' in base_url:
            base_url = base_url.split('/api/generate')[0]
            
        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "keep_alive": 0
        }
        
        print(f"🧠 Unloading model {model}...")
        requests.post(url, json=payload)
        return True
    except Exception as e:
        print(f"⚠️ Error unloading model: {e}")
        return False

@app.route('/api/llm/context/reset', methods=['POST'])
def reset_llm_context():
    """
    Forces Ollama to unload the model, clearing context.
    """
    try:
        config = load_config()
        base_url = config.get('llm_api_url', 'http://localhost:11434')
        model = config.get('llm_model', 'llama3.1')
        
        if force_unload_model(base_url, model):
            print("✅ LLM Context reset successful.")
            return jsonify({'status': 'success', 'message': 'LLM context reset'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to reset context'}), 500
            
    except Exception as e:
        print(f"❌ Error resetting LLM context: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print("="*60)
    print("🎵 Song Teller API Server")
    print("="*60)
    print("\nEndpoints:")
    print("  POST /api/song          - Add a song to current session")
    print("  POST /api/session/reset - Reset session (process songs)")
    print("  GET  /api/session/status - Get current session status")
    print("\nServer starting on http://localhost:5000")
    print("="*60 + "\n")
    
    config = load_config()
    app.run(host='0.0.0.0', port=5000, debug=False)
