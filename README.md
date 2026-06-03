# Songs Teller

**Songs Teller** is an intelligent audio session tracker for DJs. It receives real-time song information via REST API, accumulates a session, and when the session is reset it uses an LLM (Google Gemini or local Ollama) to generate DJ-style commentary about the played music, then synthesises it to audio via Google Cloud TTS or a local Chatterbox-compatible service.

## Features

- **Real-time song tracking** — add songs to a session via a simple REST API
- **Session management** — tracks start time, duration, and song history; detects duplicates
- **AI commentary** — generates radio DJ-style narration using Google Gemini or local Ollama
- **Text-to-Speech** — synthesises audio via Google Cloud TTS or a Chatterbox-compatible service
- **Async processing** — session resets return immediately; LLM + TTS run in the background
- **Audio buffering** — pre-generates commentary for the next session while the current one is playing
- **Optional authentication** — protect the API with a static key via `API_KEY` env variable
- **Customisable prompt** — edit `config/prompt.txt` to change the AI persona and style

## Architecture

| Layer | Technology |
| ----- | ---------- |
| Backend | Python 3.8+, Flask |
| LLM (cloud) | Google Gemini via LangChain |
| LLM (local) | Ollama (Llama 3, Gemma, …) |
| TTS (cloud) | Google Cloud Text-to-Speech |
| TTS (local) | Chatterbox-compatible service |
| Audio playback | pygame |

## Repository Structure

```text
songs-teller/
├── assets/
│   └── audio/
│       └── opening.mp3          # optional intro audio clip
├── config/
│   ├── config.json              # main configuration (mode, models, voices…)
│   ├── prompt.txt               # LLM instruction template
│   └── .env.example             # environment variables template
├── data/
│   └── sessions/                # saved session JSON files (gitignored)
├── docs/
│   ├── API_USAGE.md
│   ├── RUNNING_OLLAMA_LOCALLY.md
│   ├── RUNNING_CHATTERBOX_LOCALLY.md
│   ├── examples/
│   │   └── sample_songs_list.json
│   └── postman/
│       └── songs-teller.postman_collection.json
├── src/
│   └── songs_teller/            # installable Python package
│       ├── api.py               # Flask app factory + main() entry point
│       ├── routes.py            # API route handlers
│       ├── config.py            # configuration loader
│       ├── llm.py               # LLM integration (Google / Ollama)
│       ├── tts.py               # TTS integration (Google / Chatterbox)
│       └── utils.py             # shared helpers
├── tests/
│   ├── conftest.py
│   └── test_*.py
├── .github/
│   ├── dependabot.yml
│   └── workflows/automatic-tests.yml
└── pyproject.toml
```

## Getting Started

### Prerequisites

- **Python 3.8+**
- For local mode: a running [Ollama](docs/RUNNING_OLLAMA_LOCALLY.md) instance and a [Chatterbox](docs/RUNNING_CHATTERBOX_LOCALLY.md) TTS service
- For Google mode: a Google AI Studio API key and a Google Cloud service account JSON with TTS permissions

### Installation

```bash
git clone <repo-url>
cd songs-teller

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e .
```

For development (includes pytest, black, flake8, mypy):

```bash
pip install -e ".[dev]"
```

### Configuration

#### 1. Environment variables

```bash
# Windows
copy config\.env.example config\.env
# Linux / macOS
cp config/.env.example config/.env
```

Edit `config/.env`:

```env
# Required for Google mode
GOOGLE_AI_STUDIO_API_KEY=your_api_key_here

# Optional: enable API key authentication
API_KEY=
```

#### 2. `config/config.json`

Choose `"mode": "google"` or `"mode": "local"` and fill in the relevant section:

```json
{
    "mode": "google",
    "google": {
        "llm_model": "gemma-4-31b-it",
        "tts_key_path": "your-service-account.json",
        "tts_voice": "en-US-Neural2-D",
        "tts_language_code": "en-US"
    },
    "local": {
        "llm_api_url": "http://localhost:11434",
        "llm_model": "llama3.1",
        "tts_api_url": "http://localhost:4123/v1/audio/speech"
    },
    "prompt_file": "prompt.txt",
    "play_audio": true,
    "save_session": false,
    "buffer_audio": false,
    "opening_audio_path": "assets/audio/opening.mp3"
}
```

#### 3. Google Cloud credentials (Google mode only)

Place the service account JSON file in `config/` and set its name in `config.json` under `google.tts_key_path`.

## Usage

### Start the server

```bash
# Recommended — uses the installed console script
songs-teller

# Alternative — run as a Python module
python -m songs_teller.api
```

The server starts on `http://localhost:5000`.

### API quick reference

See [docs/API_USAGE.md](docs/API_USAGE.md) for the full reference including authentication headers.

```powershell
# Add a song
Invoke-RestMethod -Method Post -Uri "http://localhost:5000/api/song" `
  -Body (@{artist="Pink Floyd"; title="Time"} | ConvertTo-Json) `
  -ContentType "application/json"

# Reset session and trigger AI commentary (returns immediately)
Invoke-RestMethod -Method Post -Uri "http://localhost:5000/api/session/reset" `
  -Body (@{process=$true; play_opening_audio=$true} | ConvertTo-Json) `
  -ContentType "application/json"

# Check session state
Invoke-RestMethod -Uri "http://localhost:5000/api/session/status"
```

### Authentication

When `API_KEY` is set in `.env`, add the header to every request:

```powershell
-Headers @{"X-Api-Key" = "your-secret-key"}
```

## Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=songs_teller --cov-report=html
```

## Documentation

| Document | Description |
| -------- | ----------- |
| [docs/API_USAGE.md](docs/API_USAGE.md) | Full API reference with request/response examples |
| [docs/RUNNING_OLLAMA_LOCALLY.md](docs/RUNNING_OLLAMA_LOCALLY.md) | Set up a local Ollama LLM |
| [docs/RUNNING_CHATTERBOX_LOCALLY.md](docs/RUNNING_CHATTERBOX_LOCALLY.md) | Set up a local Chatterbox TTS |
