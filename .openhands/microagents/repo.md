---
name: TMA EngineOS KOE Librosa API Repository
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - koe-librosa-api
  - TMA EngineOS
  - KOE Engine
  - librosa api
  - music analysis api
  - audio analysis backend
---

# TMA EngineOS KOE Librosa API Repository

## Repository Purpose

This repository serves as the **Python backend API for TMA EngineOS KOE Engine**, providing comprehensive audio analysis capabilities for music artists. The API is specifically designed to:

- Process audio files through advanced music theory analysis using Librosa
- Provide tempo, key, harmonic, and spectral analysis for uploaded audio
- Serve as the backend data source for the Base44 frontend application
- Enable AI-powered music analysis within the TMA EngineOS ecosystem
- Support serverless function integration for scalable audio processing

## Current Architecture

**Technology Stack:**
- **Framework**: Flask (Python web framework)
- **Audio Processing**: Librosa library for music and audio analysis
- **Deployment**: Railway platform with Gunicorn WSGI server
- **Authentication**: API key-based security via `X-API-Key` header
- **File Handling**: Temporary file processing with automatic cleanup

**Core Dependencies:**
- `librosa>=0.10.0` - Primary audio analysis library
- `flask>=2.0.0` - Web framework
- `numpy`, `scipy`, `numba` - Scientific computing
- `soundfile`, `audioread` - Audio file I/O
- `requests` - HTTP client for audio file downloads
- `gunicorn` - Production WSGI server

## Repository Structure

```
koe-librosa-api/
├── app.py              # Main Flask application with analysis endpoints
├── requirements.txt    # Python dependencies
├── Procfile           # Railway deployment configuration
└── .git/              # Git version control
```

**Key Files:**
- `app.py` (133 lines) - Complete Flask application with comprehensive audio analysis
- `requirements.txt` - Pinned dependencies for stable deployment
- `Procfile` - Railway deployment entry point (`web: python app.py`)

## Existing API Endpoints

### Health Check Endpoint
- **Route**: `GET /`
- **Purpose**: Service health verification
- **Response**: `{"status": "KOE Librosa API is running!", "version": "1.0"}`

### Audio Analysis Endpoint
- **Route**: `POST /analyze`
- **Authentication**: Required via `X-API-Key` header
- **Input**: JSON payload with `audio_url` field
- **Process**: Downloads audio → Temporary file → Librosa analysis → Cleanup
- **Output**: Comprehensive musical analysis including:
  - Duration and tempo detection
  - Key estimation (major/minor with confidence)
  - Dominant note identification (top 3 notes)
  - Harmonic vs percussive energy balance
  - Spectral brightness analysis
  - Beat detection and timing (first 10 beats)

## Integration Patterns

**Frontend Integration:**
- Base44 frontend calls this API via serverless functions
- Audio files hosted on external services (e.g., Tonn.roexaudio.com)
- API accepts audio URLs rather than direct file uploads
- JSON-based request/response format for easy integration

**Authentication Flow:**
- API key stored in Railway environment variable `LIBROSA_API_KEY`
- Frontend must include `X-API-Key` header in all requests
- 401 responses for invalid/missing keys, 500 for server configuration issues

**Error Handling:**
- Comprehensive try-catch with detailed error messages
- HTTP status codes: 200 (success), 400 (bad request), 401 (unauthorized), 500 (server error)
- Automatic cleanup of temporary files even on errors

## Deployment Information

**Railway Configuration:**
- **Platform**: Railway.app cloud deployment
- **Entry Point**: `Procfile` specifies `web: python app.py`
- **Port**: Dynamic port from `PORT` environment variable (default: 5000)
- **Host**: `0.0.0.0` for Railway compatibility
- **Environment Variables**:
  - `LIBROSA_API_KEY` - Required for API authentication
  - `PORT` - Automatically set by Railway

**Deployment Process:**
1. Railway automatically detects Python project
2. Installs dependencies from `requirements.txt`
3. Runs `python app.py` as specified in Procfile
4. Exposes service on Railway-provided domain

## Development Guidelines

**Code Patterns:**
- Single-file Flask application for simplicity
- Comprehensive error handling with try-catch blocks
- Temporary file management with automatic cleanup
- Modular analysis functions for maintainability

**Adding New Analysis Features:**
1. Create new analysis function following `analyze_audio_comprehensive()` pattern
2. Add function call to main analysis pipeline
3. Include results in JSON response structure
4. Ensure proper error handling and resource cleanup

**API Extension Best Practices:**
- Maintain consistent JSON response format
- Use appropriate HTTP status codes
- Include detailed error messages for debugging
- Follow existing authentication patterns
- Test with actual audio files from Tonn.roexaudio.com

**Testing Considerations:**
- Test with various audio formats and durations
- Verify API key authentication works correctly
- Ensure temporary file cleanup prevents disk space issues
- Test integration with Base44 frontend serverless functions

**Performance Notes:**
- Librosa analysis can be CPU-intensive for long audio files
- Consider timeout handling for very large files
- Railway has execution time limits for web requests
- Optimize sample rates and analysis parameters for speed vs accuracy