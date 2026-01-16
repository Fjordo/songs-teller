# Running Chatterbox TTS Locally

This project supports **Chatterbox TTS**, which offers high-quality neural text-to-speech with an OpenAI-compatible API.

## 1. Setup

We recommend using Docker Compose to run Chatterbox.

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/travisvn/chatterbox-tts-api
    cd chatterbox-tts-api
    ```

2. **Prepare Environment**:

    ```bash
    # Copy the docker-specific env file
    cp .env.example.docker .env
    ```

3. **Start the Container**:
    Run one of the following commands depending on your hardware:

    ```bash
    # Standard (CPU/Auto-detect)
    docker compose -f docker/docker-compose.yml up -d

    # NVIDIA GPU (Faster)
    docker compose -f docker/docker-compose.gpu.yml up -d
    ```

    *Note: Run these commands from the root of the `chatterbox-tts-api` directory.*

## 2. Configuration

Chatterbox runs on port **4123** by default.

To configure `songs-teller` to use it, update your `app/config.json`:

```json
{
    "tts_api_url": "http://localhost:4123/v1/audio/speech",
    "tts_voice": "default",
    "play_audio": true,
    "tts_options": {
        "response_format": "mp3",
        "speed": 1,
        "temperature": 0.1,
        "exaggeration": 0.25,
        "streaming_limit": 3000
    }
}
```

## 3. Managing Voices

Chatterbox allows you to use custom voices by uploading a reference audio file.

1. **Upload a Voice**:

    ```bash
    curl -X POST http://localhost:4123/v1/voices \
      -F "voice_file=@path/to/my-voice.mp3" \
      -F "name=my-custom-voice"
    ```

2. **Use it**:
    Update `tts_voice` in `app/config.json` to `"my-custom-voice"`.

## 4. Verification

Test if the server is running:

```bash
curl http://localhost:4123/health
```

Access the API documentation at [http://localhost:4123/docs](http://localhost:4123/docs).
