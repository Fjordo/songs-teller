# Tests for Songs Teller

This directory contains comprehensive tests for the Songs Teller application.

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_api_routes.py` - Tests for Flask API endpoints
- `test_config.py` - Tests for configuration loading
- `test_llm.py` - Tests for LLM integration (Google/Ollama)
- `test_tts.py` - Tests for Text-to-Speech integration
- `test_app.py` - Tests for Flask application creation

## Running Tests

### Install test dependencies

```bash
pip install -e ".[dev]"
```

Or install pytest directly:

```bash
pip install pytest pytest-cov
```

### Run all tests

```bash
pytest
```

### Run tests with coverage

```bash
pytest --cov=songs_teller --cov-report=html
```

### Run specific test file

```bash
pytest tests/test_api_routes.py
```

### Run specific test

```bash
pytest tests/test_api_routes.py::TestAddSong::test_add_song_success
```

### Run tests with verbose output

```bash
pytest -v
```

## Test Coverage

The tests cover:

- ✅ API route handlers (add song, reset session, get status, reset LLM context)
- ✅ Configuration loading
- ✅ LLM integration (Google Gemini and local Ollama)
- ✅ Text-to-Speech integration (Google Cloud TTS and local Chatterbox)
- ✅ Session management
- ✅ Error handling
- ✅ Edge cases (empty sessions, duplicates, missing data)

## Mocking

Tests use mocking to avoid:
- External API calls (Google Cloud, Ollama, Chatterbox)
- File system operations
- Audio playback
- Network requests

This ensures tests run quickly and don't require external services.
