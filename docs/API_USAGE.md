# Song Teller API - Quick Start

## Installation

```bash
pip install -r requirements.txt
```

## Running the API Server

```bash
python song_teller_api.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### POST /api/song

Add a song to the current session.

**Request:**

```json
{
  "artist": "Iron Maiden",
  "title": "The Prisoner"
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Song added",
  "total_songs": 1
}
```

### POST /api/session/reset

Reset the current session and process songs.

**Request:**

```json
{
  "process": true
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Session reset",
  "songs_processed": 3
}
```

### GET /api/session/status

Get current session status.

**Response:**

```json
{
  "song_count": 2,
  "started_at": "2026-01-14T20:30:00",
  "last_updated": "2026-01-14T20:31:00",
  "songs": [
    {
      "artist": "Iron Maiden",
      "title": "The Prisoner",
      "timestamp": "2026-01-14T20:30:00"
    }
  ]
}
```

## How It Works

1. **Start API Server**: Run `song_teller_api.py` - it listens for song data
2. **LLM Integration**: Extend `song_teller_api.py` to query an LLM about the songs

## Extending with LLM

In `song_teller_api.py`, find the `reset_session()` function and add your LLM integration:

```python
# TODO: Add LLM processing here
# Example:
for song in current_session['songs']:
    prompt = f"Tell me about {song['artist']} - {song['title']}"
    response = your_llm.query(prompt)
    print(response)
```
