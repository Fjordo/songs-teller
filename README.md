# Songs Teller

**Songs Teller** is an intelligent audio session tracker and analyzer. It receives real-time song information, tracks sessions, and uses a local Large Language Model (LLM) to generate engaging narratives, summaries, or DJ-style commentary about the played music.

## Features

- **Real-time Song Tracking**: Add songs to a session via a simple REST API.
- **Session Management**: Track session start time, duration, and song history.
- **AI Integration**: Automatically analyzes the session using a local LLM (Ollama) when the session is reset.
- **Text-to-Speech**: Generates audio using a Chatterbox-compatible TTS service.
- **Customizable Prompts**: Define the persona and output style via an external text file.

## Architecture

- **Backend**: Python (Flask)
- **AI Engine**: LangChain + Ollama (Local Llama 3.1) or Google Gemini
- **TTS Engine**: Google Cloud TTS or Chatterbox-compatible Service
- **Data format**: JSON

## Project Structure

```properties
songs-teller/
├── src/
│   └── songs_teller/          # Main package
│       ├── __init__.py
│       ├── api.py            # Flask application entry point
│       ├── routes.py         # API route handlers
│       ├── config.py         # Configuration loader
│       ├── llm.py            # LLM integration (Google/Ollama)
│       └── tts.py            # Text-to-Speech integration
├── config/                   # Configuration files
│   ├── config.json           # Main configuration
│   ├── prompt.txt            # LLM prompt template
│   ├── .env.example          # Environment variables template
│   └── google_cloud_tts_key.json  # Google Cloud credentials (not in git)
├── tests/                    # Test files
│   ├── __init__.py
│   ├── test_with_cloud_console.py
│   └── test_with_google_ai_studio.py
├── scripts/                   # Utility scripts
│   └── run.py                # Entry point script
├── docs/                      # Documentation
│   ├── API_USAGE.md
│   ├── RUNNING_OLLAMA_LOCALLY.md
│   └── RUNNING_CHATTERBOX_LOCALLY.md
├── api/                       # API definitions
│   └── songs-teller.postman_collection.json
├── pyproject.toml            # Python package configuration
├── requirements.txt          # Python dependencies
└── README.md
```

## Getting Started

### Prerequisites

1. **Python 3.8+**
2. **Ollama**: For running the local LLM.
    - See [Running Ollama Locally](docs/RUNNING_OLLAMA_LOCALLY.md).
3. **Chatterbox TTS**:
    - You must configure a Chatterbox service.
    - See [Running Chatterbox Locally](docs/RUNNING_CHATTERBOX_LOCALLY.md).

### Installation

1. Clone the repository and navigate to the folder.
2. Create a virtual environment (recommended):

    ```bash
    python -m venv .venv
    .venv\Scripts\activate  # On Windows
    # or
    source .venv/bin/activate  # On Linux/Mac
    ```

3. Install Python dependencies:

    ```bash
    pip install -e .
    ```

    Or install dependencies directly:

    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1. Copy the example environment file:

    ```bash
    copy config\.env.example config\.env  # On Windows
    # or
    cp config/.env.example config/.env  # On Linux/Mac
    ```

2. Edit `config/.env` and add your API keys:

    ```properties
    GOOGLE_AI_STUDIO_API_KEY=your_api_key_here
    ```

3. Edit `config/config.json` to configure LLM and TTS:

    ```json
    {
        "mode": "google",
        "google": {
            "llm_model": "gemini-2.0-flash",
            "tts_key_path": "google_cloud_tts_key.json",
            "tts_voice": "en-US-Neural2-D"
        },
        "local": {
            "llm_api_url": "http://localhost:11434",
            "llm_model": "llama3.1",
            "tts_api_url": "http://localhost:5500/v1/audio/speech"
        },
        "prompt_file": "prompt.txt",
        "play_audio": true
    }
    ```

4. Place your Google Cloud service account JSON key file in `config/google_cloud_tts_key.json` (if using Google TTS).

5. Edit `config/prompt.txt` to change the instruction given to the AI.

## Usage

### 1. Start the Server

**Option 1: Using the entry point script (recommended)**

```bash
python scripts/run.py
```

**Option 2: Using Python module**

```bash
python -m songs_teller.api
```

**Option 3: Using Flask directly**

```bash
export FLASK_APP=src/songs_teller/api.py  # Linux/Mac
set FLASK_APP=src\songs_teller\api.py     # Windows
flask run
```

*Server runs on <http://localhost:5000>*

### 2. Using the API

See [docs/API_USAGE.md](docs/API_USAGE.md) for detailed API definitions.

**Brief Example (PowerShell):**

```powershell
# Add a song
Invoke-RestMethod -Method Post -Uri "http://localhost:5000/api/song" -Body (@{artist="Pink Floyd"; title="Time"} | ConvertTo-Json) -ContentType "application/json"

# Reset session and trigger AI analysis
Invoke-RestMethod -Method Post -Uri "http://localhost:5000/api/session/reset" -Body (@{process=$true; play_opening_audio=$true} | ConvertTo-Json) -ContentType "application/json"
```

## Testing

The project includes comprehensive tests. To run them:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=songs_teller --cov-report=html

# Run specific test file
pytest tests/test_api_routes.py
```

See [tests/README.md](tests/README.md) for more details.

## Documentation

- [API Usage Guide](docs/API_USAGE.md)
- [Running Ollama Locally](docs/RUNNING_OLLAMA_LOCALLY.md)
- [Test Documentation](tests/README.md)
