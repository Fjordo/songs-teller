# Song Teller API — Quick Start

## Installation

```bash
pip install -e ".[dev]"
```

## Running the API Server

```bash
python scripts/run.py
```

The server starts on `http://localhost:5000` (all interfaces — restrict with
`host="127.0.0.1"` in `api.py` if only local access is needed).

## Authentication

Authentication is **optional**. Set the `API_KEY` environment variable to enable it:

```env
API_KEY=your-secret-key
```

When set, every request must include the header:

```http
X-Api-Key: your-secret-key
```

Requests missing or carrying an incorrect key receive **401 Unauthorized**.
When `API_KEY` is not set the server operates in open/dev mode with no auth.

## API Endpoints

### POST /api/song

Add a song to the current session.

**Request headers (when `API_KEY` is set):**

```http
X-Api-Key: your-secret-key
```

**Request body:**

```json
{
  "artist": "Iron Maiden",
  "title": "The Prisoner"
}
```

Both fields are required and must not exceed **200 characters**.

**Response — success:**

```json
{
  "status": "success",
  "message": "Song added",
  "total_songs": 1
}
```

**Response — duplicate:**

```json
{
  "status": "skipped",
  "message": "Song already in session",
  "total_songs": 1
}
```

---

### POST /api/session/reset

Reset the current session. When `process` is `true` (the default) the server
snapshots the song list, resets the session immediately (returning **200**),
then processes the songs via LLM and TTS **asynchronously** in the background.

**Request body (all fields optional):**

```json
{
  "process": true,
  "play_opening_audio": false
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

---

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

---

### POST /api/llm/context/reset

Force-unload the local Ollama model to free VRAM and clear its context.
Only relevant when `mode` is `"local"` in `config.json`.

**Response:**

```json
{
  "status": "success",
  "message": "LLM context reset"
}
```

---

## Configuration

Edit `config/config.json` to switch between Google (cloud) and local modes:

```json
{
  "mode": "google",
  "save_session": false,
  "play_audio": true,
  "buffer_audio": false
}
```

See `config/.env.example` for all environment variables.
