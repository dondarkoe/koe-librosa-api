from flask import Flask, request, jsonify
import librosa
import numpy as np
import tempfile
import os
import requests
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
import pretty_midi

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

@app.route('/music-theory', methods=['POST'])
def analyze_music_theory():
    """Dedicated endpoint for Basic Pitch music theory analysis"""
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
        
        # Analyze with Basic Pitch only
        result = analyze_basic_pitch(tmp_path)
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
    
    # Basic Pitch analysis for music theory insights
    basic_pitch_analysis = analyze_basic_pitch(file_path)
    
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
        "beat_times": beat_times[:10].tolist(),  # First 10 beats
        "music_theory": basic_pitch_analysis
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

def analyze_basic_pitch(file_path):
    """Analyze audio using Basic Pitch for music theory insights"""
    try:
        # Try Basic Pitch prediction
        model_output, midi_data, note_events = predict(file_path)
        
        # Extract notes from MIDI data
        notes = []
        for instrument in midi_data.instruments:
            for note in instrument.notes:
                notes.append({
                    'pitch': note.pitch,
                    'note_name': pretty_midi.note_number_to_name(note.pitch),
                    'start': round(note.start, 3),
                    'end': round(note.end, 3),
                    'duration': round(note.end - note.start, 3),
                    'velocity': note.velocity
                })
        
        # Sort notes by start time
        notes.sort(key=lambda x: x['start'])
        
        # Analyze note statistics
        if notes:
            pitches = [note['pitch'] for note in notes]
            durations = [note['duration'] for note in notes]
            
            # Find most common notes
            pitch_counts = {}
            for pitch in pitches:
                note_name = pretty_midi.note_number_to_name(pitch)
                pitch_counts[note_name] = pitch_counts.get(note_name, 0) + 1
            
            most_common_notes = sorted(pitch_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Calculate pitch range
            pitch_range = {
                'lowest': min(pitches),
                'highest': max(pitches),
                'lowest_note': pretty_midi.note_number_to_name(min(pitches)),
                'highest_note': pretty_midi.note_number_to_name(max(pitches)),
                'range_semitones': max(pitches) - min(pitches)
            }
            
            # Analyze rhythm patterns
            note_durations_stats = {
                'average': round(np.mean(durations), 3),
                'shortest': round(min(durations), 3),
                'longest': round(max(durations), 3),
                'std_dev': round(np.std(durations), 3)
            }
            
            # Extract melody line (highest notes in time windows)
            melody_line = extract_melody_line(notes)
            
            return {
                'method': 'basic_pitch',
                'total_notes': len(notes),
                'pitch_range': pitch_range,
                'most_common_notes': most_common_notes,
                'note_durations': note_durations_stats,
                'melody_line': melody_line[:20],  # First 20 melody notes
                'all_notes': notes[:50] if len(notes) <= 50 else notes[:50]  # Limit to first 50 notes
            }
        else:
            # Fallback to librosa-based analysis
            return analyze_music_theory_librosa(file_path)
            
    except Exception as e:
        print(f"Basic Pitch failed: {e}")
        # Fallback to librosa-based analysis
        return analyze_music_theory_librosa(file_path)

def extract_melody_line(notes, window_size=0.5):
    """Extract melody line by finding highest pitch in time windows"""
    if not notes:
        return []
    
    melody = []
    current_time = 0
    max_time = max(note['end'] for note in notes)
    
    while current_time < max_time:
        window_end = current_time + window_size
        
        # Find notes in current window
        window_notes = [note for note in notes 
                       if note['start'] <= window_end and note['end'] >= current_time]
        
        if window_notes:
            # Get highest pitch note in window
            highest_note = max(window_notes, key=lambda x: x['pitch'])
            melody.append({
                'time': round(current_time, 2),
                'pitch': highest_note['pitch'],
                'note_name': highest_note['note_name']
            })
        
        current_time += window_size
    
    return melody

def analyze_music_theory_librosa(file_path):
    """Fallback music theory analysis using Librosa when Basic Pitch fails"""
    try:
        # Load audio
        y, sr = librosa.load(file_path, sr=22050)
        
        # Enhanced chroma analysis for better note detection
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
        
        # Onset detection for note timing
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=512)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
        
        # Pitch tracking using piptrack
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=512)
        
        # Extract dominant pitches over time
        pitch_sequence = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:  # Valid pitch
                pitch_sequence.append({
                    'time': librosa.frames_to_time(t, sr=sr, hop_length=512),
                    'frequency': pitch,
                    'pitch_class': librosa.hz_to_note(pitch) if pitch > 0 else 'N/A'
                })
        
        # Analyze chroma features for note distribution
        chroma_mean = np.mean(chroma, axis=1)
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        note_strengths = [(note_names[i], float(chroma_mean[i])) for i in range(12)]
        note_strengths.sort(key=lambda x: x[1], reverse=True)
        
        # Estimate pitch range from valid pitches
        valid_pitches = [p['frequency'] for p in pitch_sequence if p['frequency'] > 0]
        
        if valid_pitches:
            min_freq = min(valid_pitches)
            max_freq = max(valid_pitches)
            
            pitch_range = {
                'lowest_freq': round(min_freq, 2),
                'highest_freq': round(max_freq, 2),
                'lowest_note': librosa.hz_to_note(min_freq),
                'highest_note': librosa.hz_to_note(max_freq),
                'range_octaves': round(np.log2(max_freq / min_freq), 2)
            }
        else:
            pitch_range = None
        
        # Create melody line from pitch sequence (simplified)
        melody_line = []
        if pitch_sequence:
            # Sample every 0.5 seconds
            for i in range(0, len(pitch_sequence), max(1, len(pitch_sequence) // 40)):
                p = pitch_sequence[i]
                if p['frequency'] > 0:
                    melody_line.append({
                        'time': round(p['time'], 2),
                        'note_name': p['pitch_class'],
                        'frequency': round(p['frequency'], 2)
                    })
        
        return {
            'method': 'librosa_fallback',
            'total_notes': len([p for p in pitch_sequence if p['frequency'] > 0]),
            'pitch_range': pitch_range,
            'most_common_notes': note_strengths[:5],
            'note_durations': {
                'estimated_from_onsets': len(onset_times),
                'average_onset_interval': round(np.mean(np.diff(onset_times)), 3) if len(onset_times) > 1 else 0
            },
            'melody_line': melody_line[:20],
            'onset_times': onset_times[:20].tolist() if len(onset_times) > 0 else []
        }
        
    except Exception as e:
        return {
            'method': 'librosa_fallback',
            'error': f'Librosa analysis failed: {str(e)}',
            'total_notes': 0,
            'pitch_range': None,
            'most_common_notes': [],
            'note_durations': None,
            'melody_line': [],
            'onset_times': []
        }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
