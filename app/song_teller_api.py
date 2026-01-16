#!/usr/bin/env python3
"""
Song Teller API Server
Receives song information via HTTP API and tracks them in real-time.
Can be extended to query an LLM for information about the songs/artists.
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import requests

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
            print(f"🎵 Processing {len(current_session['songs'])} songs from session")
            print(f"{'='*60}\n")
            
            for i, song in enumerate(current_session['songs'], 1):
                print(f"{i}. {song['artist']} - {song['title']}")
            
            print(f"\n{'='*60}\n")
            
            # Save to file
            if (config.get('save_session', False)):
                save_session_to_file(current_session['songs'])
            
            # Query LLM about the songs/artists
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

    except ImportError:
         print(f"❌ Error: langchain-ollama is not installed. Please run: pip install -r requirements.txt")
    except Exception as e:
         print(f"❌ Error in process_with_llm: {e}")



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
