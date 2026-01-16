# Running Ollama Locally for Songs Teller

This project uses [Ollama](https://ollama.com/) to run Large Language Models (LLMs) locally for analyzing song sessions.

## 1. Install Ollama

Download and install Ollama from the official website:

- **Windows**: [Download Ollama for Windows](https://ollama.com/download/windows)
- **Mac/Linux**: Follow instructions on [ollama.com](https://ollama.com)

## 2. Pull the Model

Once installed, open a terminal (PowerShell or Command Prompt) and run the following command to download the Llama 3.1 model (default for this project):

```powershell
ollama pull llama3.1
```

*Note: You can use other models like `llama3`, `mistral`, etc., but make sure to update `app/config.json` if you do.*

## 3. Run the Ollama Server

Ollama usually runs in the background after installation. You can verify it's running by visiting:
[http://localhost:11434](http://localhost:11434)

If it's not running, start it from your Start Menu or terminal:

```powershell
ollama serve
```

## 4. Configuration

The `songs-teller` API connects to Ollama using the settings in `app/config.json`.

Default configuration:

```json
{
    "llm_api_url": "http://localhost:11434/api/generate",
    "llm_model": "llama3.1",
    "prompt_file": "prompt.txt"
}
```

- **llm_api_url**: The URL where Ollama is running.
- **llm_model**: The name of the model you pulled (e.g., `llama3.1`).
- **prompt_file**: The text file containing the prompt template.

## 5. Troubleshooting

- **Connection Error**: Ensure Ollama is running (`ollama serve`).
- **Model Not Found**: Run `ollama list` to see installed models and `ollama pull <model_name>` to install missing ones.
- **Slow Performance**: Local LLMs depend on your hardware (GPU/RAM). Llama 3.1 8B is reasonably fast on most modern machines.
