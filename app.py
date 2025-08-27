from flask import Flask, request, jsonify
import librosa
import numpy as np
import tempfile
import os
import requests

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "KOE Librosa API is running!", "version": "1.0"})

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    try:
        # Check API key
        api_key = request.headers.get('X-API-Key')
        expected_key = os.environ.get('LIBROSA_API_KEY')
        
        if not expected_key:
            return jsonify({'error': 'API key not configured on server'}), 500
            
        if not api_key or api_key != expected_key:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        
        data = request.get_json()
        audio_url = data.get('audio_url')
        
        if not audio_url:
            return jsonify({'error': 'No audio_url provided'}), 400
        
        # Download audio
        response = requests.get(audio_url, timeout=30)
        if response.status_code != 200:
            return jsonify({'error': 'Failed to download audio file'}), 400
        
        # Save temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
        
        # Analyze
        result = analyze_audio_comprehensive(tmp_path)
        os.unlink(tmp_path)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def analyze_audio_comprehensive(file_path):
    """Comprehensive musical analysis using librosa"""
    
    # Load audio with optimal settings
    y, sr = librosa.load(file_path, sr=22050)
    duration = librosa.get_duration(y=y, sr=sr)
    
    # Tempo and beat analysis
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beats, sr=sr)
    
    # Key and harmonic analysis
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key_profile = np.mean(chroma, axis=1)
    dominant_notes = get_dominant_notes(key_profile)
    estimated_key = estimate_key(key_profile)
    
    # Harmonic vs percussive separation
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    harmonic_energy = np.mean(librosa.feature.rms(y=y_harmonic))
    percussive_energy = np.mean(librosa.feature.rms(y=y_percussive))
    energy_balance = harmonic_energy / (harmonic_energy + percussive_energy)
    
    # Spectral analysis
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
    
    return {
        "duration": round(duration, 2),
        "tempo": round(float(tempo), 1),
        "estimated_key": estimated_key,
        "dominant_notes": dominant_notes,
        "energy_balance": {
            "harmonic": round(float(harmonic_energy), 3),
            "percussive": round(float(percussive_energy), 3),
            "ratio": round(float(energy_balance), 3),
            "dominant": "harmonic" if energy_balance > 0.5 else "percussive"
        },
        "brightness": {
            "average": round(float(np.mean(spectral_centroids)), 1)
        },
        "beat_count": len(beats),
        "beat_times": beat_times[:10].tolist()  # First 10 beats
    }

def get_dominant_notes(key_profile):
    """Convert chroma values to note names"""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    top_indices = np.argsort(key_profile)[-3:][::-1]
    return [notes[i] for i in top_indices]

def estimate_key(key_profile):
    """Simple key estimation based on chroma profile"""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Major and minor key templates
    major_template = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
    minor_template = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0])
    
    best_correlation = -1
    best_key = "Unknown"
    
    for i in range(12):
        # Test major
        major_shifted = np.roll(major_template, i)
        correlation = np.corrcoef(key_profile, major_shifted)[0,1]
        if correlation > best_correlation:
            best_correlation = correlation
            best_key = f"{notes[i]} major"
        
        # Test minor  
        minor_shifted = np.roll(minor_template, i)
        correlation = np.corrcoef(key_profile, minor_shifted)[0,1]
        if correlation > best_correlation:
            best_correlation = correlation
            best_key = f"{notes[i]} minor"
    
    return best_key

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
