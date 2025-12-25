from flask import Flask, request, jsonify, send_file, after_this_request
import librosa
import numpy as np
import tempfile
import os
import requests
import time
import subprocess
import shutil
import re
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
import pretty_midi
from collections import defaultdict
import json
import anthropic

app = Flask(__name__)

# =============================================================================
# GENRE-SPECIFIC PRODUCTION TARGETS
# =============================================================================

GENRE_TARGETS = {
    'electronic': {
        'name': 'Electronic/EDM',
        'lufs_target': (-8, -6),
        'lufs_description': 'Loud masters are standard for club play',
        'clipping_tolerance': 'moderate',
        'stereo_width_target': (60, 100),
        'dynamic_range_target': (4, 8),
        'bass_emphasis': 'high',
        'characteristics': 'Heavy compression, loud masters, wide stereo, punchy kicks, sustained bass'
    },
    'dubstep': {
        'name': 'Dubstep/Bass Music',
        'lufs_target': (-6, -4),
        'lufs_description': 'Very loud masters are expected - louder is often better',
        'clipping_tolerance': 'high',
        'stereo_width_target': (70, 100),
        'dynamic_range_target': (3, 6),
        'bass_emphasis': 'extreme',
        'characteristics': 'Aggressive limiting, heavy sub-bass, clipping can be intentional for grit, extreme loudness'
    },
    'hip-hop': {
        'name': 'Hip-Hop/Trap',
        'lufs_target': (-10, -7),
        'lufs_description': 'Punchy but not overly crushed to preserve vocal clarity',
        'clipping_tolerance': 'low',
        'stereo_width_target': (40, 70),
        'dynamic_range_target': (5, 9),
        'bass_emphasis': 'high',
        'characteristics': '808 sub-bass clarity, punchy drums, clear vocals, moderate loudness'
    },
    'pop': {
        'name': 'Pop',
        'lufs_target': (-10, -8),
        'lufs_description': 'Radio-ready loudness while preserving dynamics for streaming',
        'clipping_tolerance': 'none',
        'stereo_width_target': (50, 80),
        'dynamic_range_target': (6, 10),
        'bass_emphasis': 'moderate',
        'characteristics': 'Clean masters, no clipping, balanced frequency response, streaming-optimized'
    },
    'rock': {
        'name': 'Rock',
        'lufs_target': (-11, -8),
        'lufs_description': 'Dynamic range preserved for energy, moderate loudness',
        'clipping_tolerance': 'low',
        'stereo_width_target': (60, 90),
        'dynamic_range_target': (7, 12),
        'bass_emphasis': 'moderate',
        'characteristics': 'Natural dynamics, guitar clarity, punchy drums, analog warmth'
    },
    'r-and-b': {
        'name': 'R&B/Soul',
        'lufs_target': (-12, -9),
        'lufs_description': 'Warmth and dynamics prioritized over loudness',
        'clipping_tolerance': 'none',
        'stereo_width_target': (40, 70),
        'dynamic_range_target': (8, 14),
        'bass_emphasis': 'moderate',
        'characteristics': 'Warm low-end, smooth vocals, natural dynamics, minimal compression'
    },
    'classical': {
        'name': 'Classical/Orchestral',
        'lufs_target': (-18, -14),
        'lufs_description': 'Maximum dynamic range is essential',
        'clipping_tolerance': 'none',
        'stereo_width_target': (80, 100),
        'dynamic_range_target': (14, 20),
        'bass_emphasis': 'natural',
        'characteristics': 'Full dynamic range, natural stereo imaging, no limiting, pristine clarity'
    },
    'jazz': {
        'name': 'Jazz',
        'lufs_target': (-16, -12),
        'lufs_description': 'Natural dynamics and room ambience preserved',
        'clipping_tolerance': 'none',
        'stereo_width_target': (60, 90),
        'dynamic_range_target': (10, 16),
        'bass_emphasis': 'natural',
        'characteristics': 'Natural dynamics, acoustic clarity, minimal processing, warm tone'
    },
    'country': {
        'name': 'Country',
        'lufs_target': (-12, -9),
        'lufs_description': 'Radio-friendly but natural sounding',
        'clipping_tolerance': 'none',
        'stereo_width_target': (50, 80),
        'dynamic_range_target': (7, 12),
        'bass_emphasis': 'moderate',
        'characteristics': 'Natural acoustic instruments, clear vocals, moderate loudness'
    },
    'metal': {
        'name': 'Metal',
        'lufs_target': (-8, -5),
        'lufs_description': 'Loud and aggressive is expected',
        'clipping_tolerance': 'moderate',
        'stereo_width_target': (70, 100),
        'dynamic_range_target': (4, 8),
        'bass_emphasis': 'high',
        'characteristics': 'Heavy compression, loud masters, tight low-end, aggressive limiting'
    },
    'ambient': {
        'name': 'Ambient/Experimental',
        'lufs_target': (-18, -12),
        'lufs_description': 'Dynamics and space are essential',
        'clipping_tolerance': 'none',
        'stereo_width_target': (80, 100),
        'dynamic_range_target': (12, 20),
        'bass_emphasis': 'variable',
        'characteristics': 'Wide stereo field, full dynamics, atmospheric space, no aggressive limiting'
    },
    'other': {
        'name': 'General/Mixed',
        'lufs_target': (-14, -9),
        'lufs_description': 'Balanced approach for streaming platforms',
        'clipping_tolerance': 'low',
        'stereo_width_target': (50, 80),
        'dynamic_range_target': (6, 12),
        'bass_emphasis': 'moderate',
        'characteristics': 'Balanced frequency response, streaming-optimized loudness'
    }
}

def generate_ai_feedback(analysis_result, genre):
    """Generate AI-powered production feedback based on genre expectations"""

    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if not anthropic_key:
        return {'skipped': 'ANTHROPIC_API_KEY not configured'}

    try:
        client = anthropic.Anthropic(api_key=anthropic_key)

        # Get genre targets
        targets = GENRE_TARGETS.get(genre, GENRE_TARGETS['other'])

        # Extract key metrics from analysis
        librosa_data = analysis_result.get('librosa', {})
        tonn_data = analysis_result.get('tonn', {})

        tempo = librosa_data.get('tempo', 'Unknown')
        key = librosa_data.get('estimated_key', 'Unknown')
        duration = librosa_data.get('duration', 0)
        energy_balance = librosa_data.get('energy_balance', {})

        loudness = tonn_data.get('loudness', {})
        stereo = tonn_data.get('stereo', {})
        technical = tonn_data.get('technical', {})
        master_eval = tonn_data.get('master_eval', {})

        lufs = loudness.get('integrated_lufs', 'N/A')
        true_peak = loudness.get('true_peak_dbfs', 'N/A')
        stereo_width = stereo.get('width', 'N/A')
        clipping = technical.get('clipping', 'NONE')
        drc_rating = master_eval.get('drc', 'N/A')

        prompt = f"""You are KOE, an expert AI music production mentor. Analyze this track and provide personalized feedback.

## Artist's Genre: {targets['name']}
Genre characteristics: {targets['characteristics']}
Target LUFS range: {targets['lufs_target'][0]} to {targets['lufs_target'][1]} LUFS ({targets['lufs_description']})
Clipping tolerance for this genre: {targets['clipping_tolerance']}
Expected stereo width: {targets['stereo_width_target'][0]}-{targets['stereo_width_target'][1]}%
Expected dynamic range: {targets['dynamic_range_target'][0]}-{targets['dynamic_range_target'][1]} dB

## Track Analysis Results:
- Tempo: {tempo} BPM
- Key: {key}
- Duration: {duration}s
- Energy: {energy_balance.get('ratio', 'N/A')} harmonic ratio ({energy_balance.get('dominant', 'N/A')} dominant)
- Integrated Loudness: {lufs} LUFS
- True Peak: {true_peak} dBFS
- Stereo Width: {stereo_width}%
- Clipping Detection: {clipping}
- Dynamic Range Rating: {drc_rating}
- Mono Compatible: {stereo.get('mono_compatible', 'N/A')}
- Phase Issues: {stereo.get('phase_issues', 'N/A')}

## Your Task:
Provide feedback in this exact JSON format:
{{
    "overall_rating": "EXCELLENT/GOOD/NEEDS_WORK/CONCERNING",
    "genre_match_score": 1-10,
    "headline": "One punchy sentence summary",
    "loudness_feedback": {{
        "status": "PERFECT/TOO_LOUD/TOO_QUIET/ACCEPTABLE",
        "message": "Specific feedback about loudness for this genre"
    }},
    "stereo_feedback": {{
        "status": "PERFECT/TOO_WIDE/TOO_NARROW/ACCEPTABLE",
        "message": "Feedback about stereo width and imaging"
    }},
    "dynamics_feedback": {{
        "status": "PERFECT/OVER_COMPRESSED/TOO_DYNAMIC/ACCEPTABLE",
        "message": "Feedback about dynamic range for this genre"
    }},
    "technical_issues": ["List any technical problems"],
    "strengths": ["List what's working well"],
    "suggestions": ["3-5 actionable production tips specific to their genre"]
}}

Be encouraging but honest. Frame everything through the lens of {targets['name']} production standards. If something would be a problem in pop but is fine for their genre, say so!"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the response
        response_text = message.content[0].text

        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            feedback = json.loads(json_match.group())
            return feedback
        else:
            return {'error': 'Failed to parse AI response', 'raw': response_text}

    except anthropic.APIError as e:
        return {'error': f'Anthropic API error: {str(e)}'}
    except json.JSONDecodeError as e:
        return {'error': f'JSON parse error: {str(e)}', 'raw': response_text}
    except Exception as e:
        return {'error': f'AI feedback error: {str(e)}'}

# =============================================================================
# STREAMING PLATFORM EXTRACTION (yt-dlp)
# =============================================================================

STREAMING_PLATFORMS = [
    'soundcloud.com',
    'youtube.com',
    'youtu.be',
    'spotify.com',
    'bandcamp.com',
    'audiomack.com',
    'tiktok.com',
    'instagram.com',
    'twitter.com',
    'x.com'
]

def is_streaming_url(url):
    """Check if URL is from a supported streaming platform"""
    lower_url = url.lower()
    return any(platform in lower_url for platform in STREAMING_PLATFORMS)

def get_platform_name(url):
    """Get friendly name of streaming platform"""
    lower_url = url.lower()
    if 'soundcloud.com' in lower_url:
        return 'SoundCloud'
    elif 'youtube.com' in lower_url or 'youtu.be' in lower_url:
        return 'YouTube'
    elif 'spotify.com' in lower_url:
        return 'Spotify'
    elif 'bandcamp.com' in lower_url:
        return 'Bandcamp'
    elif 'audiomack.com' in lower_url:
        return 'Audiomack'
    elif 'tiktok.com' in lower_url:
        return 'TikTok'
    elif 'instagram.com' in lower_url:
        return 'Instagram'
    elif 'twitter.com' in lower_url or 'x.com' in lower_url:
        return 'Twitter/X'
    return 'Unknown'

def extract_audio_from_url(url, output_dir):
    """
    Extract audio from streaming platform URL using yt-dlp
    Returns path to downloaded audio file
    """
    try:
        # Create output path
        output_template = os.path.join(output_dir, 'audio.%(ext)s')

        # yt-dlp command for audio extraction
        cmd = [
            'yt-dlp',
            '--no-playlist',
            '-x',  # Extract audio
            '--audio-format', 'wav',  # Convert to WAV for analysis
            '--audio-quality', '0',  # Best quality
            '-o', output_template,
            '--no-warnings',
            '--quiet',
            url
        ]

        # Run yt-dlp
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            error_msg = result.stderr or 'Unknown error'
            return None, f"yt-dlp failed: {error_msg}"

        # Find the downloaded file
        for f in os.listdir(output_dir):
            if f.startswith('audio.'):
                return os.path.join(output_dir, f), None

        return None, "No audio file was extracted"

    except subprocess.TimeoutExpired:
        return None, "Audio extraction timed out (120s limit)"
    except FileNotFoundError:
        return None, "yt-dlp not installed"
    except Exception as e:
        return None, str(e)

# =============================================================================
# TONN API INTEGRATION (Mix Analysis)
# =============================================================================

TONN_API_BASE = 'https://tonn.roexaudio.com'

# Musical style mapping
GENRE_TO_STYLE = {
    'electronic': 'ELECTRONIC',
    'edm': 'ELECTRONIC',
    'house': 'ELECTRONIC',
    'techno': 'ELECTRONIC',
    'dubstep': 'ELECTRONIC',
    'dnb': 'ELECTRONIC',
    'drum and bass': 'ELECTRONIC',
    'trance': 'ELECTRONIC',
    'hip hop': 'HIPHOP_GRIME',
    'hip-hop': 'HIPHOP_GRIME',
    'rap': 'HIPHOP_GRIME',
    'trap': 'HIPHOP_GRIME',
    'grime': 'HIPHOP_GRIME',
    'r&b': 'HIPHOP_GRIME',
    'indie': 'ROCK_INDIE',
    'alternative': 'ROCK_INDIE',
    'rock': 'ROCK',
    'metal': 'ROCK',
    'punk': 'ROCK',
    'acoustic': 'ACOUSTIC',
    'folk': 'ACOUSTIC',
    'singer-songwriter': 'SINGER_SONGWRITER',
    'jazz': 'JAZZ',
    'classical': 'CLASSICAL',
    'orchestral': 'CLASSICAL',
    'pop': 'POP',
    'dance': 'POP'
}

def map_genre_to_style(genre):
    """Map user genre to Tonn musical style"""
    if not genre:
        return 'ELECTRONIC'
    lower = genre.lower()
    for key, style in GENRE_TO_STYLE.items():
        if key in lower:
            return style
    return 'ELECTRONIC'

def upload_to_tonn(audio_path, api_key):
    """Upload audio file to Tonn and get readable URL"""
    try:
        filename = os.path.basename(audio_path)

        # Determine content type
        ext = os.path.splitext(audio_path)[1].lower()
        content_types = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4'
        }
        content_type = content_types.get(ext, 'audio/wav')

        # Step 1: Get upload URLs
        response = requests.post(
            f'{TONN_API_BASE}/upload',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key
            },
            json={'filename': filename, 'contentType': content_type},
            timeout=30
        )

        if response.status_code != 200:
            return None, f"Failed to get upload URL: {response.text}"

        data = response.json()
        signed_url = data.get('signed_url')
        readable_url = data.get('readable_url')

        if not signed_url or not readable_url:
            return None, "Missing URLs in Tonn response"

        # Step 2: Upload file to signed URL
        with open(audio_path, 'rb') as f:
            audio_data = f.read()

        put_response = requests.put(
            signed_url,
            headers={'Content-Type': content_type},
            data=audio_data,
            timeout=60
        )

        if put_response.status_code not in [200, 201]:
            return None, f"Failed to upload to Tonn: {put_response.status_code}"

        return readable_url, None

    except Exception as e:
        return None, str(e)

def analyze_with_tonn(readable_url, musical_style, is_master, api_key):
    """Run Tonn mix analysis with polling"""
    try:
        payload = {
            'mixDiagnosisData': {
                'audioFileLocation': readable_url,
                'musicalStyle': musical_style,
                'isMaster': is_master
            }
        }

        response = requests.post(
            f'{TONN_API_BASE}/mixanalysis',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key
            },
            json=payload,
            timeout=30
        )

        # Handle async processing
        if response.status_code == 202:
            # Poll for results
            for attempt in range(30):  # Max 2.5 minutes
                time.sleep(5)
                poll_response = requests.post(
                    f'{TONN_API_BASE}/mixanalysis',
                    headers={
                        'Content-Type': 'application/json',
                        'x-api-key': api_key
                    },
                    json=payload,
                    timeout=30
                )

                if poll_response.status_code == 200:
                    data = poll_response.json()
                    if data.get('mixDiagnosisResults'):
                        return data, None

            return None, "Tonn analysis timed out"

        if response.status_code != 200:
            return None, f"Tonn analysis failed: {response.text}"

        return response.json(), None

    except Exception as e:
        return None, str(e)

def normalize_tonn_response(tonn_data):
    """Normalize Tonn API response to our format"""
    result = {}

    if not tonn_data or 'mixDiagnosisResults' not in tonn_data:
        return result

    payload = tonn_data['mixDiagnosisResults'].get('payload', {})

    # Loudness metrics
    if payload.get('integrated_loudness_lufs') is not None:
        result['loudness'] = {
            'integrated_lufs': payload.get('integrated_loudness_lufs'),
            'loudness_range_lu': payload.get('loudness_range_lu', 0),
            'true_peak_dbfs': payload.get('true_peak_dbfs') or payload.get('peak_loudness_dbfs', 0)
        }

    # Stereo field
    stereo_field = payload.get('stereo_field', '')
    width = 50  # Default
    if 'mono' in stereo_field.lower():
        width = 0
    elif 'narrow' in stereo_field.lower():
        width = 25
    elif 'wide' in stereo_field.lower():
        width = 75
    elif 'very wide' in stereo_field.lower():
        width = 90

    result['stereo'] = {
        'width': width,
        'field': stereo_field,
        'mono_compatible': payload.get('mono_compatible', True),
        'phase_issues': payload.get('phase_issues', False)
    }

    # Dynamics
    if payload.get('dynamic_range_db') is not None:
        result['dynamics'] = {
            'dynamic_range_db': payload.get('dynamic_range_db'),
            'crest_factor_db': payload.get('crest_factor_db', 0)
        }

    # Frequency balance
    if payload.get('frequency_balance'):
        fb = payload['frequency_balance']
        result['frequency_balance'] = {
            'low': fb.get('low', 0),
            'mid': fb.get('mid', 0),
            'high': fb.get('high', 0)
        }

    # Technical info
    result['technical'] = {
        'bit_depth': payload.get('bit_depth'),
        'sample_rate': payload.get('sample_rate'),
        'clipping': payload.get('clipping', False)
    }

    # Issues
    issues = []
    if payload.get('clipping') in [True, 'true', 'YES']:
        issues.append({
            'type': 'clipping',
            'severity': 'error',
            'message': 'Digital clipping detected'
        })
    if payload.get('phase_issues'):
        issues.append({
            'type': 'phase',
            'severity': 'warning',
            'message': 'Phase issues detected'
        })
    if not payload.get('mono_compatible', True):
        issues.append({
            'type': 'mono_compatibility',
            'severity': 'warning',
            'message': 'Mix may not translate well to mono'
        })

    if issues:
        result['issues'] = issues

    # Master evaluation
    if payload.get('if_master_drc'):
        result['master_eval'] = {
            'drc': payload.get('if_master_drc'),
            'loudness': payload.get('if_master_loudness')
        }

    return result

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
    return jsonify({
        "status": "KOE Audio Analysis API is running!",
        "version": "2.0",
        "endpoints": {
            "/analyze": "Librosa music analysis (tempo, key, energy)",
            "/analyze-full": "Full analysis with SoundCloud/YouTube support + Tonn mix analysis",
            "/music-theory": "Basic Pitch music theory analysis",
            "/extract-chords-midi": "Chord extraction and MIDI generation"
        },
        "supported_platforms": ["SoundCloud", "YouTube", "Bandcamp", "Audiomack", "TikTok", "Instagram", "Twitter/X"]
    })

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    tmp_path = None
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

        # Convert numpy types to JSON-serializable types
        result = convert_numpy_types(result)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Always cleanup temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

@app.route('/music-theory', methods=['POST'])
def analyze_music_theory():
    """Dedicated endpoint for Basic Pitch music theory analysis"""
    tmp_path = None  # Track file for cleanup
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

        # Convert numpy types to JSON-serializable types
        result = convert_numpy_types(result)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Always cleanup temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

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

def generate_midi_filename(track_type, custom_names={}, song_name='', naming_style='descriptive', timestamp=None):
    """Generate custom MIDI filename in format: 'Song name_TrackType_MIDI by Don Darkoe.mid'"""
    if timestamp is None:
        timestamp = int(time.time())
    
    # Clean song name for filename
    if song_name:
        clean_song = "".join(c for c in song_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_song = clean_song.replace(' ', '_')
    else:
        clean_song = "Unknown_Song"
    
    # Track type mapping for better names
    track_names = {
        'chords': 'Chords',
        'bass': 'Bass',
        'melody': 'Melody',
        'combined': 'Full_Arrangement'
    }
    
    track_name = track_names.get(track_type, track_type.title())
    
    # Format: "Song name_TrackType_MIDI by Don Darkoe.mid"
    filename = f"{clean_song}_{track_name}_MIDI_by_Don_Darkoe.mid"
    
    return filename

def extract_chord_progression_midi(file_path, include_tracks=['chords', 'bass', 'melody'], custom_names={}, song_name='', naming_style='descriptive'):
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
            midi_filename = generate_midi_filename(track_type, custom_names, song_name, naming_style, timestamp)
            midi_path = f"/tmp/{midi_filename}"
            
            # Create MIDI file with only this track
            create_single_track_midi(chord_progression, midi_data, midi_path, track_type, tempo)
            
            midi_files[track_type] = {
                'filename': midi_filename,
                'download_url': f'/download-midi/{midi_filename}'
            }
        
        # Also create a combined file for backward compatibility
        combined_filename = generate_midi_filename('combined', custom_names, song_name, naming_style, timestamp)
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
        return extract_chords_librosa_fallback(file_path, include_tracks, custom_names, song_name, naming_style)

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

def extract_chords_librosa_fallback(file_path, include_tracks, custom_names={}, song_name='', naming_style='descriptive'):
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
            midi_filename = generate_midi_filename(track_type, custom_names, song_name, naming_style, timestamp)
            midi_path = f"/tmp/{midi_filename}"
            
            # Create MIDI file with only this track
            create_simple_single_track_midi(chord_progression, midi_path, safe_tempo, track_type)
            
            midi_files[track_type] = {
                'filename': midi_filename,
                'download_url': f'/download-midi/{midi_filename}'
            }
        
        # Also create a combined file for backward compatibility
        combined_filename = generate_midi_filename('combined', custom_names, song_name, naming_style, timestamp)
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
    tmp_path = None  # Track file for cleanup
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

        # Custom naming options
        custom_names = data.get('custom_names', {})  # e.g., {"chords": "MyChords", "bass": "MyBass"}
        song_name = data.get('song_name', '')  # Optional song name for better file naming
        naming_style = data.get('naming_style', 'descriptive')  # 'descriptive', 'simple', 'timestamp'

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

        # Extract chords and create MIDI with custom naming
        result = extract_chord_progression_midi(tmp_path, include_tracks, custom_names, song_name, naming_style)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Always cleanup temp audio file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

@app.route('/download-midi/<filename>', methods=['GET'])
def download_midi(filename):
    """Serve the generated MIDI file for download and cleanup after"""
    try:
        # Security: Only allow .mid files, no path traversal
        if not filename.endswith('.mid') or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400

        file_path = f"/tmp/{filename}"
        if not os.path.exists(file_path):
            return jsonify({'error': 'MIDI file not found'}), 404

        # Schedule cleanup after response is sent
        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass
            return response

        return send_file(file_path,
                        as_attachment=True,
                        download_name=filename,
                        mimetype='audio/midi')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# UNIFIED ANALYSIS ENDPOINT
# =============================================================================

@app.route('/analyze-full', methods=['POST'])
def analyze_full():
    """
    Full audio analysis combining:
    - Streaming platform extraction (yt-dlp)
    - Librosa music analysis (tempo, key, energy)
    - Tonn mix analysis (loudness, stereo, dynamics)

    Supports: SoundCloud, YouTube, Bandcamp, and direct audio URLs
    """
    tmp_dir = None
    audio_path = None

    try:
        # Check API key
        api_key = request.headers.get('X-API-Key')
        expected_key = os.environ.get('LIBROSA_API_KEY')

        if not expected_key:
            return jsonify({'error': 'API key not configured on server'}), 500

        if not api_key or api_key != expected_key:
            return jsonify({'error': 'Invalid or missing API key'}), 401

        # Get request data
        data = request.get_json()
        audio_url = data.get('audio_url')
        genre = data.get('genre', 'electronic')
        is_master = data.get('is_master', False)

        if not audio_url:
            return jsonify({'error': 'No audio_url provided'}), 400

        # Get Tonn API key (optional - if not set, skip Tonn analysis)
        tonn_api_key = os.environ.get('ROEX_API_KEY')

        # Create temp directory for processing
        tmp_dir = tempfile.mkdtemp()

        # Step 1: Get audio file (extract from streaming or download directly)
        platform_name = None

        if is_streaming_url(audio_url):
            platform_name = get_platform_name(audio_url)
            audio_path, extract_error = extract_audio_from_url(audio_url, tmp_dir)

            if extract_error:
                return jsonify({
                    'error': f'Failed to extract audio from {platform_name}',
                    'details': extract_error,
                    'tip': 'Make sure the track is public and the URL is correct.'
                }), 400
        else:
            # Direct audio URL - download it
            try:
                response = requests.get(audio_url, timeout=60)
                if response.status_code != 200:
                    return jsonify({'error': f'Failed to download audio: HTTP {response.status_code}'}), 400

                # Determine extension from URL or content type
                ext = '.wav'
                if '.mp3' in audio_url.lower():
                    ext = '.mp3'
                elif '.flac' in audio_url.lower():
                    ext = '.flac'
                elif '.m4a' in audio_url.lower():
                    ext = '.m4a'

                audio_path = os.path.join(tmp_dir, f'audio{ext}')
                with open(audio_path, 'wb') as f:
                    f.write(response.content)

            except requests.Timeout:
                return jsonify({'error': 'Audio download timed out'}), 400
            except Exception as e:
                return jsonify({'error': f'Failed to download audio: {str(e)}'}), 400

        # Step 2: Run Librosa analysis
        librosa_result = None
        try:
            librosa_result = analyze_audio_comprehensive(audio_path)
            librosa_result = convert_numpy_types(librosa_result)
        except Exception as e:
            librosa_result = {'error': f'Librosa analysis failed: {str(e)}'}

        # Step 3: Run Tonn analysis (if API key is set)
        tonn_result = None
        if tonn_api_key:
            try:
                # Upload to Tonn
                readable_url, upload_error = upload_to_tonn(audio_path, tonn_api_key)

                if upload_error:
                    tonn_result = {'error': f'Tonn upload failed: {upload_error}'}
                else:
                    # Run analysis
                    musical_style = map_genre_to_style(genre)
                    tonn_data, analysis_error = analyze_with_tonn(
                        readable_url, musical_style, is_master, tonn_api_key
                    )

                    if analysis_error:
                        tonn_result = {'error': f'Tonn analysis failed: {analysis_error}'}
                    else:
                        tonn_result = normalize_tonn_response(tonn_data)

            except Exception as e:
                tonn_result = {'error': f'Tonn analysis error: {str(e)}'}
        else:
            tonn_result = {'skipped': 'ROEX_API_KEY not configured'}

        # Combine results
        result = {
            'source': {
                'url': audio_url,
                'platform': platform_name,
                'genre': genre,
                'is_master': is_master
            },
            'librosa': librosa_result,
            'tonn': tonn_result
        }

        # Add summary if both analyses succeeded
        if librosa_result and not librosa_result.get('error'):
            if tonn_result and not tonn_result.get('error') and not tonn_result.get('skipped'):
                result['summary'] = {
                    'tempo': librosa_result.get('tempo'),
                    'key': librosa_result.get('estimated_key'),
                    'duration': librosa_result.get('duration'),
                    'loudness_lufs': tonn_result.get('loudness', {}).get('integrated_lufs'),
                    'stereo_width': tonn_result.get('stereo', {}).get('width'),
                    'dynamic_range': tonn_result.get('dynamics', {}).get('dynamic_range_db'),
                    'issues': tonn_result.get('issues', [])
                }
            else:
                result['summary'] = {
                    'tempo': librosa_result.get('tempo'),
                    'key': librosa_result.get('estimated_key'),
                    'duration': librosa_result.get('duration')
                }

        # Step 4: Generate AI feedback based on genre expectations
        result['genre_targets'] = GENRE_TARGETS.get(genre, GENRE_TARGETS['other'])
        result['ai_feedback'] = generate_ai_feedback(result, genre)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Cleanup temp files
        if tmp_dir and os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except:
                pass


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
