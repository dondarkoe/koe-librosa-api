# Testing Chord Extraction with Real Songs

This guide shows you how to test the chord extraction and MIDI export functionality with real songs.

## 🎵 Quick Start - Test with Sample Files

We've created realistic test files for you:

```bash
# Test the realistic chord progression (Am-F-C-G)
python -c "from upload_and_test import test_uploaded_file; test_uploaded_file('/tmp/test_song_realistic.wav')"

# Test melody with chords
python -c "from upload_and_test import test_uploaded_file; test_uploaded_file('/tmp/test_melody_chords.wav')"
```

## 📁 Method 1: Upload Your Own Audio Files

### Step 1: Copy your audio files
```bash
# Create test directory
mkdir -p /tmp/audio_test

# Copy your files (supports .wav, .mp3, .m4a, .flac)
cp /path/to/your/song.wav /tmp/audio_test/
cp /path/to/your/song.mp3 /tmp/audio_test/
```

### Step 2: Test individual files
```bash
python -c "from upload_and_test import test_uploaded_file; test_uploaded_file('/tmp/audio_test/your_song.wav', ['chords', 'bass', 'melody'])"
```

### Step 3: Batch test all files
```bash
python upload_and_test.py
```

## 🌐 Method 2: Test with Public Audio URLs

### Using the API endpoint:
```bash
# Start the server
LIBROSA_API_KEY=test123 python app.py &

# Test with a public audio URL
curl -X POST http://localhost:5000/extract-chords-midi \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test123" \
  -d '{
    "audio_url": "https://example.com/your-audio-file.wav",
    "include_tracks": ["chords", "bass", "melody"]
  }'
```

### Using the test script:
```bash
python test_real_songs.py
```

## 🎬 Method 3: YouTube Audio (Advanced)

⚠️ **WARNING**: Only use with copyright-free content or your own videos!

### Install yt-dlp:
```bash
pip install yt-dlp
```

### Test with YouTube:
```python
from test_youtube import test_youtube_song

# Test with a copyright-free video
test_youtube_song("https://www.youtube.com/watch?v=YOUR_VIDEO_ID", ["chords", "bass"])
```

## 🎹 What You Get

### API Response Format:
```json
{
  "method": "basic_pitch|librosa_fallback",
  "total_chords": 12,
  "tempo": 120.0,
  "duration": 180.5,
  "tracks_included": ["chords", "bass", "melody"],
  "midi_download_url": "/download-midi/chords_1234567890.mid",
  "chord_progression": [
    {
      "time": 0.0,
      "duration": 2.0,
      "chord_name": "C Major",
      "root": "C",
      "chord_type": "Major",
      "notes": ["C", "E", "G"],
      "midi_notes": [60, 64, 67],
      "confidence": 0.85
    }
  ]
}
```

### MIDI File Structure:
- **Track 1 (Chords)**: Block chords for rhythm guitar/piano
- **Track 2 (Bass)**: Root notes in bass register
- **Track 3 (Melody)**: Main melodic line

## 🎛️ Track Selection Options

You can choose which tracks to include:

```python
# Only chords
test_uploaded_file("song.wav", ["chords"])

# Chords and bass
test_uploaded_file("song.wav", ["chords", "bass"])

# All tracks
test_uploaded_file("song.wav", ["chords", "bass", "melody"])
```

## 🎯 Best Practices for Testing

### Audio Quality:
- **Best**: Uncompressed WAV files
- **Good**: High-quality MP3 (320kbps)
- **Okay**: Standard MP3 (128kbps)

### Song Types:
- **Excellent**: Piano/guitar with clear chords
- **Good**: Pop/rock with distinct chord progressions
- **Challenging**: Heavy metal, electronic, or very complex jazz

### File Length:
- **Optimal**: 30 seconds to 5 minutes
- **Maximum**: 10 minutes (Railway timeout limits)

## 🔧 Troubleshooting

### Common Issues:

**1. "Basic Pitch failed" - Using Librosa fallback**
- This is normal! The fallback system ensures analysis always works
- Librosa fallback provides good chord detection

**2. "No chords detected"**
- Try with a clearer recording
- Ensure the audio has harmonic content (not just drums/percussion)

**3. "Download failed"**
- Check the audio URL is publicly accessible
- Ensure the file format is supported

**4. "Tempo seems wrong"**
- This is common with complex rhythms
- The MIDI will still have correct chord timing

## 📊 Example Test Results

### Pop Song (C-Am-F-G progression):
```
Method: librosa_fallback
Total chords: 16
Tempo: 128.0 BPM
Duration: 180.0 seconds

Chord Progression:
1.   0.0s: C Major    - [C, E, G]
2.   4.0s: A Minor    - [A, C, E]  
3.   8.0s: F Major    - [F, A, C]
4.  12.0s: G Major    - [G, B, D]
```

### Jazz Standard:
```
Method: basic_pitch
Total chords: 32
Tempo: 120.0 BPM

Chord Progression:
1.   0.0s: C Major 7th     - [C, E, G, B]
2.   2.0s: A Minor 7th     - [A, C, E, G]
3.   4.0s: D Dominant 7th  - [D, F#, A, C]
4.   6.0s: G Dominant 7th  - [G, B, D, F]
```

## 🎹 Using MIDI in Ableton Live

1. **Download the MIDI file** from the API response
2. **Open Ableton Live**
3. **Drag the .mid file** into a MIDI track
4. **Choose your instrument** (piano, synth, etc.)
5. **Play and edit** as needed!

### MIDI Track Layout:
- **Track 1**: Chord progression (great for pad sounds)
- **Track 2**: Bass line (perfect for bass synths)
- **Track 3**: Melody (ideal for lead instruments)

## 🚀 Advanced Usage

### Custom Analysis:
```python
from app import extract_chord_progression_midi

# Analyze with custom settings
result = extract_chord_progression_midi(
    "your_song.wav", 
    include_tracks=["chords", "bass"],
    # Additional parameters can be added here
)

# Access detailed results
for chord in result['chord_progression']:
    print(f"{chord['time']}s: {chord['chord_name']} ({chord['confidence']})")
```

### Batch Processing:
```python
from upload_and_test import batch_test_directory

# Process all audio files in a directory
batch_test_directory("/path/to/your/music/folder")
```

## 🎉 Ready to Test!

1. **Start simple**: Use the provided test files
2. **Upload your own**: Copy files to `/tmp/audio_test/`
3. **Test with URLs**: Use publicly accessible audio
4. **Drag to Ableton**: Use the generated MIDI files

The system works with both Basic Pitch (when available) and Librosa fallback, ensuring you always get results!

Happy chord extraction! 🎵