from flask import Flask, request, jsonify, send_file
import librosa
import numpy as np
import tempfile
import os
import requests
import time
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
import pretty_midi
from collections import defaultdict
import json

app = Flask(__name__)

# Custom JSON encoder to handle numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

app.json_encoder = NumpyEncoder

# Helper function to convert numpy types recursively
def convert_numpy_types(obj):
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

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
        
        # Convert numpy types to JSON-serializable types
        result = convert_numpy_types(result)
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
        
        # Convert numpy types to JSON-serializable types
        result = convert_numpy_types(result)
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

def extract_chord_progression_midi(file_path, include_tracks=['chords', 'bass', 'melody']):
    """Extract chord progression and create separate downloadable MIDI files for each track"""
    try:
        # Use Basic Pitch to get precise note data
        model_output, midi_data, note_events = predict(file_path)
        
        # Get tempo from original audio for MIDI timing
        y, sr = librosa.load(file_path, sr=22050)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        
        # Analyze chord progression using Basic Pitch's recommended approach
        chord_progression = analyze_chords_from_midi(midi_data, tempo)
        
        # Create separate MIDI files for each requested track
        timestamp = int(time.time())
        midi_files = {}
        
        for track_type in include_tracks:
            midi_filename = f"{track_type}_{timestamp}.mid"
            midi_path = f"/tmp/{midi_filename}"
            
            # Create MIDI file with only this track
            create_single_track_midi(chord_progression, midi_data, midi_path, track_type, tempo)
            
            midi_files[track_type] = {
                'filename': midi_filename,
                'download_url': f'/download-midi/{midi_filename}'
            }
        
        # Also create a combined file for backward compatibility
        combined_filename = f"combined_{timestamp}.mid"
        combined_path = f"/tmp/{combined_filename}"
        create_multi_track_midi(chord_progression, midi_data, combined_path, include_tracks, tempo)
        
        return {
            'chord_progression': chord_progression,
            'midi_files': midi_files,
            'combined_midi_url': f'/download-midi/{combined_filename}',
            'total_chords': len(chord_progression),
            'tempo': float(tempo) if isinstance(tempo, (int, float, np.number)) else float(tempo.item()) if hasattr(tempo, 'item') else 120.0,
            'tracks_included': include_tracks,
            'duration': float(midi_data.get_end_time()) if midi_data.get_end_time() > 0 else 0
        }
        
    except Exception as e:
        # Fallback to Librosa-based chord analysis
        return extract_chords_librosa_fallback(file_path, include_tracks)

def analyze_chords_from_midi(midi_data, tempo, window_size=2.0):
    """Analyze chord progression from MIDI data using Basic Pitch's approach"""
    chords = []
    
    if not midi_data.instruments:
        return chords
    
    # Get all notes from all instruments
    all_notes = []
    for instrument in midi_data.instruments:
        for note in instrument.notes:
            all_notes.append({
                'pitch': note.pitch,
                'start': note.start,
                'end': note.end,
                'velocity': note.velocity
            })
    
    # Sort by start time
    all_notes.sort(key=lambda x: x['start'])
    
    if not all_notes:
        return chords
    
    # Analyze in time windows (Basic Pitch recommends 2-4 second windows)
    max_time = max(note['end'] for note in all_notes)
    current_time = 0
    
    while current_time < max_time:
        # Get notes active in this window
        active_notes = []
        for note in all_notes:
            if (note['start'] <= current_time + window_size and 
                note['end'] >= current_time):
                active_notes.append(note)
        
        if active_notes:
            # Identify chord from active notes
            chord_info = identify_chord_from_notes(active_notes, current_time, window_size)
            if chord_info:
                chords.append(chord_info)
        
        current_time += window_size
    
    return chords

def identify_chord_from_notes(notes, start_time, duration):
    """Identify chord name and type from a collection of notes"""
    if not notes:
        return None
    
    # Get unique pitch classes (remove octave information)
    pitches = [note['pitch'] for note in notes]
    pitch_classes = sorted(list(set([p % 12 for p in pitches])))
    
    # Find root note (usually the lowest or most prominent)
    root_pitch = min(pitches) % 12
    
    # Chord templates with their intervals from root
    chord_templates = {
        'Major': [0, 4, 7],
        'Minor': [0, 3, 7],
        'Dominant 7th': [0, 4, 7, 10],
        'Major 7th': [0, 4, 7, 11],
        'Minor 7th': [0, 3, 7, 10],
        'Minor Major 7th': [0, 3, 7, 11],
        'Diminished': [0, 3, 6],
        'Diminished 7th': [0, 3, 6, 9],
        'Half Diminished 7th': [0, 3, 6, 10],
        'Augmented': [0, 4, 8],
        'Suspended 2nd': [0, 2, 7],
        'Suspended 4th': [0, 5, 7],
        'Add 9': [0, 2, 4, 7],
        'Major 9th': [0, 2, 4, 7, 11],
        'Minor 9th': [0, 2, 3, 7, 10]
    }
    
    # Note names for root identification
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Find best matching chord
    best_match = None
    best_score = 0
    
    for chord_name, template in chord_templates.items():
        # Try each possible root
        for root in pitch_classes:
            transposed_template = [(interval + root) % 12 for interval in template]
            
            # Calculate match score
            matches = len(set(pitch_classes) & set(transposed_template))
            total_notes = len(set(pitch_classes) | set(transposed_template))
            score = matches / total_notes if total_notes > 0 else 0
            
            if score > best_score and matches >= 2:  # At least 2 notes must match
                best_score = score
                root_name = note_names[root]
                best_match = {
                    'time': round(start_time, 2),
                    'duration': round(duration, 2),
                    'chord_name': f"{root_name} {chord_name}",
                    'root': root_name,
                    'chord_type': chord_name,
                    'notes': [note_names[p] for p in sorted(pitch_classes)],
                    'midi_notes': sorted(pitches),
                    'confidence': round(best_score, 3)
                }
    
    # If no good match found, create a generic chord
    if not best_match:
        root_name = note_names[root_pitch]
        best_match = {
            'time': round(start_time, 2),
            'duration': round(duration, 2),
            'chord_name': f"{root_name} Unknown",
            'root': root_name,
            'chord_type': 'Unknown',
            'notes': [note_names[p] for p in sorted(pitch_classes)],
            'midi_notes': sorted(pitches),
            'confidence': 0.5
        }
    
    return best_match

def create_multi_track_midi(chord_progression, original_midi, output_path, include_tracks, tempo):
    """Create multi-track MIDI file for Ableton Live"""
    # Create new MIDI file
    midi_file = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    
    if 'chords' in include_tracks:
        # Track 1: Chord progression (block chords)
        chord_instrument = pretty_midi.Instrument(program=0, name="Chords")  # Piano
        
        for chord in chord_progression:
            start_time = chord['time']
            end_time = start_time + chord['duration']
            
            # Add all chord notes simultaneously
            for midi_note in chord['midi_notes']:
                note = pretty_midi.Note(
                    velocity=80,
                    pitch=midi_note,
                    start=start_time,
                    end=end_time
                )
                chord_instrument.notes.append(note)
        
        midi_file.instruments.append(chord_instrument)
    
    if 'bass' in include_tracks:
        # Track 2: Bass line (root notes)
        bass_instrument = pretty_midi.Instrument(program=32, name="Bass")  # Bass
        
        for chord in chord_progression:
            start_time = chord['time']
            end_time = start_time + chord['duration']
            
            # Add root note in bass register
            root_midi = min(chord['midi_notes'])
            while root_midi > 48:  # Keep in bass register (below C3)
                root_midi -= 12
            
            note = pretty_midi.Note(
                velocity=90,
                pitch=max(24, root_midi),  # Don't go below C1
                start=start_time,
                end=end_time
            )
            bass_instrument.notes.append(note)
        
        midi_file.instruments.append(bass_instrument)
    
    if 'melody' in include_tracks and original_midi.instruments:
        # Track 3: Melody line (highest notes from original)
        melody_instrument = pretty_midi.Instrument(program=73, name="Melody")  # Flute
        
        # Extract melody from original MIDI (highest notes)
        melody_notes = extract_melody_from_midi(original_midi)
        
        for note_info in melody_notes:
            note = pretty_midi.Note(
                velocity=70,
                pitch=note_info['pitch'],
                start=note_info['start'],
                end=note_info['end']
            )
            melody_instrument.notes.append(note)
        
        midi_file.instruments.append(melody_instrument)
    
    # Write MIDI file
    midi_file.write(output_path)

def create_single_track_midi(chord_progression, original_midi, output_path, track_type, tempo):
    """Create single-track MIDI file for specific track type"""
    # Create new MIDI file
    midi_file = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    
    if track_type == 'chords':
        # Chord progression (block chords)
        chord_instrument = pretty_midi.Instrument(program=0, name="Chords")  # Piano
        
        for chord in chord_progression:
            start_time = chord['time']
            end_time = start_time + chord['duration']
            
            # Add all chord notes simultaneously
            for midi_note in chord['midi_notes']:
                note = pretty_midi.Note(
                    velocity=80,
                    pitch=midi_note,
                    start=start_time,
                    end=end_time
                )
                chord_instrument.notes.append(note)
        
        midi_file.instruments.append(chord_instrument)
    
    elif track_type == 'bass':
        # Bass line (root notes)
        bass_instrument = pretty_midi.Instrument(program=32, name="Bass")  # Bass
        
        for chord in chord_progression:
            start_time = chord['time']
            end_time = start_time + chord['duration']
            
            # Add root note in bass register
            root_midi = min(chord['midi_notes'])
            while root_midi > 48:  # Keep in bass register (below C3)
                root_midi -= 12
            
            note = pretty_midi.Note(
                velocity=90,
                pitch=max(24, root_midi),  # Don't go below C1
                start=start_time,
                end=end_time
            )
            bass_instrument.notes.append(note)
        
        midi_file.instruments.append(bass_instrument)
    
    elif track_type == 'melody' and original_midi.instruments:
        # Melody line (highest notes from original)
        melody_instrument = pretty_midi.Instrument(program=73, name="Melody")  # Flute
        
        # Extract melody from original MIDI (highest notes)
        melody_notes = extract_melody_from_midi(original_midi)
        
        for note_info in melody_notes:
            note = pretty_midi.Note(
                velocity=70,
                pitch=note_info['pitch'],
                start=note_info['start'],
                end=note_info['end']
            )
            melody_instrument.notes.append(note)
        
        midi_file.instruments.append(melody_instrument)
    
    # Write MIDI file
    midi_file.write(output_path)

def extract_melody_from_midi(midi_data, window_size=0.5):
    """Extract melody line by finding highest pitch in time windows"""
    if not midi_data.instruments:
        return []
    
    # Get all notes
    all_notes = []
    for instrument in midi_data.instruments:
        for note in instrument.notes:
            all_notes.append({
                'pitch': note.pitch,
                'start': note.start,
                'end': note.end,
                'velocity': note.velocity
            })
    
    if not all_notes:
        return []
    
    # Sort by start time
    all_notes.sort(key=lambda x: x['start'])
    
    # Extract melody using time windows
    melody_notes = []
    max_time = max(note['end'] for note in all_notes)
    current_time = 0
    
    while current_time < max_time:
        # Find highest note in this window
        window_notes = [
            note for note in all_notes
            if note['start'] <= current_time + window_size and note['end'] >= current_time
        ]
        
        if window_notes:
            highest_note = max(window_notes, key=lambda x: x['pitch'])
            melody_notes.append({
                'pitch': highest_note['pitch'],
                'start': current_time,
                'end': current_time + window_size,
                'velocity': highest_note['velocity']
            })
        
        current_time += window_size
    
    return melody_notes

def extract_chords_librosa_fallback(file_path, include_tracks):
    """Fallback chord extraction using enhanced Librosa analysis"""
    try:
        # Load audio
        y, sr = librosa.load(file_path, sr=22050)
        
        # Get tempo and beats
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        
        # Enhanced chroma analysis
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
        
        # Analyze chords at beat positions
        chord_progression = []
        
        for i in range(len(beat_times) - 1):
            start_time = float(beat_times[i])
            end_time = float(beat_times[i + 1])
            duration = end_time - start_time
            
            # Get chroma for this beat
            start_frame = librosa.time_to_frames(start_time, sr=sr, hop_length=512)
            end_frame = librosa.time_to_frames(end_time, sr=sr, hop_length=512)
            
            if start_frame < chroma.shape[1] and end_frame <= chroma.shape[1]:
                beat_chroma = np.mean(chroma[:, start_frame:end_frame], axis=1)
                
                # Find dominant notes
                note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                dominant_notes = []
                
                # Get top 3-4 notes
                top_indices = np.argsort(beat_chroma)[-4:]
                for idx in top_indices:
                    if beat_chroma[idx] > 0.3:  # Threshold for significant notes
                        dominant_notes.append(note_names[idx])
                
                if len(dominant_notes) >= 2:
                    # Simple chord naming based on dominant notes
                    root = dominant_notes[0]
                    chord_name = f"{root} Chord"
                    
                    chord_progression.append({
                        'time': round(start_time, 2),
                        'duration': round(duration, 2),
                        'chord_name': chord_name,
                        'root': root,
                        'chord_type': 'Estimated',
                        'notes': dominant_notes,
                        'midi_notes': [note_names.index(note) + 60 for note in dominant_notes],  # C4 = 60
                        'confidence': 0.7
                    })
        
        # Create separate MIDI files for each requested track
        timestamp = int(time.time())
        midi_files = {}
        
        # Ensure tempo is valid
        safe_tempo = float(tempo) if isinstance(tempo, (int, float, np.number)) else float(tempo.item()) if hasattr(tempo, 'item') else 120.0
        if safe_tempo <= 0:
            safe_tempo = 120.0
        
        for track_type in include_tracks:
            midi_filename = f"{track_type}_librosa_{timestamp}.mid"
            midi_path = f"/tmp/{midi_filename}"
            
            # Create MIDI file with only this track
            create_simple_single_track_midi(chord_progression, midi_path, safe_tempo, track_type)
            
            midi_files[track_type] = {
                'filename': midi_filename,
                'download_url': f'/download-midi/{midi_filename}'
            }
        
        # Also create a combined file for backward compatibility
        combined_filename = f"combined_librosa_{timestamp}.mid"
        combined_path = f"/tmp/{combined_filename}"
        create_simple_chord_midi(chord_progression, combined_path, safe_tempo, include_tracks)
        
        return {
            'method': 'librosa_fallback',
            'chord_progression': chord_progression,
            'midi_files': midi_files,
            'combined_midi_url': f'/download-midi/{combined_filename}',
            'total_chords': len(chord_progression),
            'tempo': safe_tempo,
            'tracks_included': include_tracks,
            'duration': float(len(y) / sr)
        }
        
    except Exception as e:
        return {
            'error': f'Chord extraction failed: {str(e)}',
            'chord_progression': [],
            'midi_download_url': None,
            'total_chords': 0
        }

def create_simple_chord_midi(chord_progression, output_path, tempo, include_tracks):
    """Create simple MIDI file from Librosa chord analysis"""
    midi_file = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    
    if 'chords' in include_tracks:
        chord_instrument = pretty_midi.Instrument(program=0, name="Chords")
        
        for chord in chord_progression:
            start_time = chord['time']
            end_time = start_time + chord['duration']
            
            for midi_note in chord['midi_notes']:
                note = pretty_midi.Note(
                    velocity=80,
                    pitch=midi_note,
                    start=start_time,
                    end=end_time
                )
                chord_instrument.notes.append(note)
        
        midi_file.instruments.append(chord_instrument)
    
    midi_file.write(output_path)

def create_simple_single_track_midi(chord_progression, output_path, tempo, track_type):
    """Create simple single-track MIDI file from Librosa chord analysis"""
    midi_file = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    
    if track_type == 'chords':
        chord_instrument = pretty_midi.Instrument(program=0, name="Chords")
        
        for chord in chord_progression:
            start_time = chord['time']
            end_time = start_time + chord['duration']
            
            for midi_note in chord['midi_notes']:
                note = pretty_midi.Note(
                    velocity=80,
                    pitch=midi_note,
                    start=start_time,
                    end=end_time
                )
                chord_instrument.notes.append(note)
        
        midi_file.instruments.append(chord_instrument)
    
    elif track_type == 'bass':
        bass_instrument = pretty_midi.Instrument(program=32, name="Bass")
        
        for chord in chord_progression:
            start_time = chord['time']
            end_time = start_time + chord['duration']
            
            # Add root note in bass register
            root_midi = min(chord['midi_notes'])
            while root_midi > 48:  # Keep in bass register (below C3)
                root_midi -= 12
            
            note = pretty_midi.Note(
                velocity=90,
                pitch=max(24, root_midi),  # Don't go below C1
                start=start_time,
                end=end_time
            )
            bass_instrument.notes.append(note)
        
        midi_file.instruments.append(bass_instrument)
    
    elif track_type == 'melody':
        # For Librosa fallback, create a simple melody from the highest chord notes
        melody_instrument = pretty_midi.Instrument(program=73, name="Melody")
        
        for chord in chord_progression:
            start_time = chord['time']
            end_time = start_time + chord['duration']
            
            # Use highest note from chord as melody
            melody_note = max(chord['midi_notes'])
            
            note = pretty_midi.Note(
                velocity=70,
                pitch=melody_note,
                start=start_time,
                end=end_time
            )
            melody_instrument.notes.append(note)
        
        midi_file.instruments.append(melody_instrument)
    
    midi_file.write(output_path)

@app.route('/extract-chords-midi', methods=['POST'])
def extract_chords_midi():
    """Extract chord progression and return downloadable MIDI file"""
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
        include_tracks = data.get('include_tracks', ['chords', 'bass', 'melody'])  # User can specify which tracks
        
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
        
        # Extract chords and create MIDI
        result = extract_chord_progression_midi(tmp_path, include_tracks)
        os.unlink(tmp_path)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-midi/<filename>', methods=['GET'])
def download_midi(filename):
    """Serve the generated MIDI file for download"""
    try:
        file_path = f"/tmp/{filename}"
        if not os.path.exists(file_path):
            return jsonify({'error': 'MIDI file not found'}), 404
            
        return send_file(file_path, 
                        as_attachment=True, 
                        download_name=filename,
                        mimetype='audio/midi')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
