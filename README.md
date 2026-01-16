# Songs Teller

**Songs Teller** is an intelligent audio session tracker and analyzer. It receives real-time song information, tracks sessions, and uses a local Large Language Model (LLM) to generate engaging narratives, summaries, or DJ-style commentary about the played music.

## Features

- **Real-time Song Tracking**: Add songs to a session via a simple REST API.
- **Session Management**: Track session start time, duration, and song history.
- **AI Integration**: Automatically analyzes the session using a local LLM (Ollama) when the session is reset.
- **Customizable Prompts**: Define the persona and output style via an external text file.

## Architecture

- **Backend**: Python (Flask)
- **AI Engine**: LangChain + Ollama (Local Llama 3.1)
- **Data format**: JSON

## Getting Started

### Prerequisites

1. **Python 3.8+**
2. **Ollama**: For running the local LLM.
    - See [Running Ollama Locally](docs/RUNNING_OLLAMA_LOCALLY.md) for installation and setup instructions.

### Installation

1. Clone the repository and navigate to the folder.
2. Install Python dependencies:

    ```bash
    pip install -r app/requirements.txt
    ```

### Configuration

Edit `app/config.json` to configure the LLM connection:

```json
{
    "llm_api_url": "http://localhost:11434",
    "llm_model": "llama3.1",
    "prompt_file": "prompt.txt"
}
```

Edit `app/prompt.txt` to change the instruction given to the AI (e.g., "Act as a music critic", "Act as a radio DJ").

## Usage

### 1. Start the Server

```bash
python app/song_teller_api.py
```

*Server runs on <http://localhost:5000>*

### 2. Using the API

See [docs/API_USAGE.md](docs/API_USAGE.md) for detailed API definitions.

**Brief Example (PowerShell):**

```powershell
# Add a song
Invoke-RestMethod -Method Post -Uri "http://localhost:5000/api/song" -Body (@{artist="Pink Floyd"; title="Time"} | ConvertTo-Json) -ContentType "application/json"

# Reset session and trigger AI analysis
Invoke-RestMethod -Method Post -Uri "http://localhost:5000/api/session/reset" -Body (@{process=$true} | ConvertTo-Json) -ContentType "application/json"
```

## Documentation

- [API Usage Guide](docs/API_USAGE.md)
- [Running Ollama Locally](docs/RUNNING_OLLAMA_LOCALLY.md)
