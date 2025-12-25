# KOE Audio Analysis API

A comprehensive audio analysis API for music producers, providing professional mix/master evaluation with AI-powered genre-specific feedback.

## Features

### Streaming Platform Support
Analyze tracks directly from popular platforms:
- SoundCloud
- YouTube
- Bandcamp
- Audiomack
- TikTok
- Instagram
- Twitter/X

### Professional Mix Analysis (via Tonn/RoEx)
- **Loudness Metering**: Integrated LUFS, loudness range, true peak
- **Stereo Analysis**: Width, mono compatibility, phase issues
- **Dynamic Range**: Compression evaluation
- **Technical Quality**: Sample rate, bit depth, clipping detection

### Genre-Specific Production Targets
Optimized mixing/mastering specs for 13 genres:

| Genre | Target LUFS | Clipping Tolerance | Stereo Width |
|-------|-------------|-------------------|--------------|
| Drum & Bass | -8 to -7 | Low | 70-100% |
| Dubstep | -6 to -4 | High | 70-100% |
| Trap | -10 to -8 | High | 40-80% |
| Techno | -8 to -6 | Moderate | 60-100% |
| Baile Funk | -10 to -8 | Extreme | 50-80% |
| UK Garage | -9 to -6 | Moderate | 50-85% |
| Bass House | -10 to -8 | High | 60-100% |
| Trance | -10 to -8 | Low | 80-100% |
| Afrobeats | -10 to -8 | Moderate | 50-85% |
| Hip-Hop | -12 to -9 | Moderate | 40-70% |
| Pop | -10 to -8 | None | 50-80% |
| R&B | -12 to -9 | None | 40-70% |

### AI-Powered Feedback (Claude)
Personalized production advice based on your genre:
- Overall mix rating
- Loudness evaluation against genre standards
- Stereo field recommendations
- Dynamics assessment
- Actionable production tips

### Music Theory Analysis (Basic Pitch)
- Note transcription
- Pitch range detection
- Melody line extraction
- Chord progression insights

## API Endpoints

### Health Check
```
GET /
```
Returns API status and supported platforms.

### Full Analysis (Recommended)
```
POST /analyze-full
```
Complete analysis with streaming platform support, Tonn mix analysis, and AI feedback.

**Headers:**
```
X-API-Key: your_api_key
Content-Type: application/json
```

**Request:**
```json
{
  "audio_url": "https://soundcloud.com/artist/track",
  "genre": "drum-and-bass",
  "is_master": true
}
```

**Response:**
```json
{
  "source": {
    "url": "https://soundcloud.com/artist/track",
    "platform": "SoundCloud",
    "genre": "drum-and-bass",
    "is_master": true
  },
  "librosa": {
    "tempo": 174.2,
    "estimated_key": "F minor",
    "duration": 245.5,
    "beat_count": 712,
    "dominant_notes": ["F", "C", "G#"],
    "energy_balance": {
      "harmonic": 0.45,
      "percussive": 0.55,
      "dominant": "percussive"
    },
    "brightness": { "average": 2850.3 }
  },
  "tonn": {
    "loudness": {
      "integrated_lufs": -7.5,
      "loudness_range_lu": 6.2,
      "true_peak_dbfs": -0.8
    },
    "stereo": {
      "width": 85,
      "field": "WIDE",
      "mono_compatible": true,
      "phase_issues": false
    },
    "technical": {
      "sample_rate": 44100,
      "bit_depth": 16,
      "clipping": "NONE"
    }
  },
  "summary": {
    "tempo": 174.2,
    "key": "F minor",
    "duration": 245.5,
    "loudness_lufs": -7.5,
    "stereo_width": 85,
    "dynamic_range": 6.2
  },
  "genre_targets": {
    "name": "Drum & Bass",
    "lufs_target": [-8, -7],
    "stereo_width_target": [70, 100],
    "clipping_tolerance": "low",
    "characteristics": "Sharp transients, mono sub below 120Hz..."
  },
  "ai_feedback": {
    "overall_rating": "EXCELLENT",
    "genre_match_score": 9,
    "headline": "Club-ready D&B master with punchy transients and proper loudness.",
    "loudness_feedback": {
      "status": "PERFECT",
      "message": "At -7.5 LUFS you're right in the D&B sweet spot..."
    },
    "stereo_feedback": {
      "status": "PERFECT",
      "message": "85% width is ideal for D&B atmospherics..."
    },
    "dynamics_feedback": {
      "status": "ACCEPTABLE",
      "message": "Good dynamic range preserved for transient punch..."
    },
    "technical_issues": [],
    "strengths": ["Proper loudness for genre", "Wide stereo field", "No clipping"],
    "suggestions": ["Consider a touch more sub-bass presence", "..."]
  }
}
```

### Quick Analysis (Librosa Only)
```
POST /analyze
```
Fast analysis without Tonn or AI feedback.

### Music Theory
```
POST /music-theory
```
Dedicated note transcription and pitch analysis.

### Chord Extraction
```
POST /extract-chords-midi
```
Extract chords and generate MIDI file.

## Supported Genres

```
drum-and-bass, dubstep, trap, techno, baile-funk,
uk-garage, bass-house, trance, afrobeats,
hip-hop, pop, r-and-b, other
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PORT` | Server port (auto-set by Railway) | No |
| `ROEX_API_KEY` | RoEx Tonn API key for mix analysis | Yes |
| `ANTHROPIC_API_KEY` | Claude API key for AI feedback | Yes |

## Deployment

### Docker (Recommended)
```bash
docker build -t koe-api .
docker run -p 5000:5000 \
  -e ROEX_API_KEY=your_key \
  -e ANTHROPIC_API_KEY=your_key \
  koe-api
```

### Railway
1. Connect GitHub repo
2. Set environment variables
3. Deploy (Dockerfile auto-detected)

### Local Development
```bash
pip install -r requirements.txt
export ROEX_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key
python app.py
```

## Tech Stack

- **Framework**: Flask + Gunicorn
- **Audio Analysis**: Librosa, Basic Pitch
- **Mix Analysis**: RoEx Tonn API
- **AI Feedback**: Anthropic Claude
- **Audio Extraction**: yt-dlp
- **ML Runtime**: TensorFlow CPU

## Error Handling

```json
{
  "error": "Failed to extract audio from SoundCloud",
  "details": "Track may be private or removed",
  "tip": "Make sure the track is public and the URL is correct"
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad request (invalid URL, unsupported platform)
- `401`: Unauthorized (invalid API key)
- `500`: Server error

## License

Part of the TMA EngineOS ecosystem for AI-powered music production tools.
