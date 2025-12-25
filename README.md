# TMA EngineOS KOE Librosa API

A comprehensive Python backend API for TMA EngineOS KOE Engine, providing advanced audio analysis capabilities for music artists. This API combines Librosa's powerful audio analysis with Spotify's Basic Pitch for music theory insights.

## Features

### Core Audio Analysis
- **Tempo and Beat Detection**: Accurate BPM detection and beat timing analysis
- **Key Estimation**: Major/minor key detection with confidence scoring
- **Harmonic Analysis**: Separation of harmonic vs percussive content
- **Spectral Analysis**: Brightness and frequency content analysis
- **Dominant Notes**: Identification of the most prominent notes in the audio

### Music Theory Analysis (NEW)
- **Note Transcription**: Automatic conversion of audio to musical notes
- **Pitch Range Analysis**: Detection of lowest/highest notes and vocal/instrumental range
- **Melody Line Extraction**: Identification of the main melodic content
- **Note Duration Statistics**: Analysis of rhythm patterns and note timing
- **Chord Progression Insights**: Understanding of harmonic content over time

## API Endpoints

### Health Check
```
GET /
```
Returns API status and version information.

### Comprehensive Audio Analysis
```
POST /analyze
```
Performs complete audio analysis including both traditional Librosa features and music theory analysis.

**Headers:**
- `X-API-Key`: Required API key for authentication

**Request Body:**
```json
{
  "audio_url": "https://example.com/audio.wav"
}
```

**Response Example:**
```json
{
  "duration": 120.5,
  "tempo": 128.0,
  "estimated_key": "C major",
  "dominant_notes": ["C", "E", "G"],
  "energy_balance": {
    "harmonic": 0.65,
    "percussive": 0.35,
    "ratio": 0.65,
    "dominant": "harmonic"
  },
  "brightness": {
    "average": 2150.3
  },
  "beat_count": 256,
  "beat_times": [0.47, 0.94, 1.41, 1.88],
  "music_theory": {
    "method": "basic_pitch",
    "total_notes": 342,
    "pitch_range": {
      "lowest": 60,
      "highest": 84,
      "lowest_note": "C4",
      "highest_note": "C6",
      "range_semitones": 24
    },
    "most_common_notes": [
      ["C", 45],
      ["E", 38],
      ["G", 35]
    ],
    "note_durations": {
      "average": 0.5,
      "shortest": 0.1,
      "longest": 2.3,
      "std_dev": 0.4
    },
    "melody_line": [
      {"time": 0.0, "pitch": 72, "note_name": "C5"},
      {"time": 0.5, "pitch": 76, "note_name": "E5"}
    ]
  }
}
```

### Dedicated Music Theory Analysis
```
POST /music-theory
```
Performs only music theory analysis using Basic Pitch (with Librosa fallback).

**Headers:**
- `X-API-Key`: Required API key for authentication

**Request Body:**
```json
{
  "audio_url": "https://example.com/audio.wav"
}
```

## Analysis Methods

### Basic Pitch Integration
The API attempts to use Spotify's Basic Pitch for precise note transcription:
- **Advantages**: Highly accurate note detection, precise timing, MIDI-quality output
- **Use Cases**: Detailed music theory analysis, transcription, educational tools

### Librosa Fallback
When Basic Pitch is unavailable, the API uses enhanced Librosa analysis:
- **Advantages**: Reliable, fast, works in all environments
- **Features**: Chroma analysis, onset detection, pitch tracking
- **Use Cases**: General music analysis, key detection, rhythm analysis

## Environment Setup

### Dependencies
```bash
pip install -r requirements.txt
```

### Environment Variables
- `LIBROSA_API_KEY`: Required API key for authentication
- `PORT`: Server port (default: 5000)

### Railway Deployment
The API is configured for Railway deployment with:
- `Procfile`: Specifies the web process
- Automatic dependency installation
- Environment variable configuration

## Development

### Local Testing
```bash
# Set API key
export LIBROSA_API_KEY=your_test_key

# Run the server
python app.py

# Test the API
curl -X GET http://localhost:5000/
```

### Testing Music Theory Analysis
```bash
# Run the test script
python test_basic_pitch.py
```

## Integration with TMA EngineOS

### Frontend Integration
- Base44 frontend calls this API via serverless functions
- Audio files are hosted externally (e.g., Tonn.roexaudio.com)
- JSON-based communication for easy integration

### Authentication
- API key-based security via `X-API-Key` header
- Environment variable configuration for secure key storage

### Error Handling
- Comprehensive error responses with appropriate HTTP status codes
- Graceful fallback from Basic Pitch to Librosa when needed
- Detailed error messages for debugging

## Performance Considerations

### Audio Processing
- Optimized sample rates for balance between quality and speed
- Temporary file management with automatic cleanup
- Timeout handling for large audio files

### Railway Limitations
- Web request timeout limits
- CPU-intensive analysis considerations
- Memory usage optimization for large files

## Future Enhancements

### Basic Pitch Optimization
- TensorFlow version compatibility improvements
- CoreML support for faster inference
- ONNX runtime integration for cross-platform deployment

### Additional Features
- Chord progression analysis
- Scale detection and mode analysis
- Advanced rhythm pattern recognition
- Multi-instrument separation and analysis

## API Response Formats

### Success Response
```json
{
  "duration": 120.5,
  "tempo": 128.0,
  // ... analysis results
}
```

### Error Response
```json
{
  "error": "Description of the error"
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad request (missing audio_url, download failed)
- `401`: Unauthorized (invalid/missing API key)
- `500`: Server error (configuration issues, analysis failures)

## Contributing

When extending the API:
1. Maintain consistent JSON response formats
2. Include comprehensive error handling
3. Follow existing authentication patterns
4. Test with various audio formats and durations
5. Update documentation for new features

## License

This project is part of the TMA EngineOS ecosystem for AI-powered music analysis.# Deploy trigger Thu 25 Dec 2025 12:48:18 AWST
