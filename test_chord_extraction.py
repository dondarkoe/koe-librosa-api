#!/usr/bin/env python3
"""
Test script for chord extraction and MIDI export functionality
"""

import numpy as np
import soundfile as sf
import tempfile
import os
import requests
import json
from app import extract_chord_progression_midi

def create_chord_progression_audio():
    """Create test audio with a simple chord progression: C - F - G - C"""
    sample_rate = 22050
    chord_duration = 2.0  # 2 seconds per chord
    
    # Chord definitions (frequencies in Hz)
    chords = {
        'C_major': [261.63, 329.63, 392.00],  # C4, E4, G4
        'F_major': [349.23, 440.00, 523.25],  # F4, A4, C5
        'G_major': [392.00, 493.88, 587.33],  # G4, B4, D5
        'C_major_end': [261.63, 329.63, 392.00]  # C4, E4, G4
    }
    
    progression = ['C_major', 'F_major', 'G_major', 'C_major_end']
    
    # Generate audio for each chord
    full_audio = []
    
    for chord_name in progression:
        frequencies = chords[chord_name]
        t = np.linspace(0, chord_duration, int(sample_rate * chord_duration))
        
        # Create chord by summing sine waves
        chord_audio = np.zeros_like(t)
        for freq in frequencies:
            chord_audio += 0.2 * np.sin(2 * np.pi * freq * t)
        
        # Add some envelope to make it more realistic
        envelope = np.exp(-t * 0.5)  # Decay envelope
        chord_audio *= envelope
        
        full_audio.extend(chord_audio)
    
    return np.array(full_audio), sample_rate

def test_chord_extraction_direct():
    """Test chord extraction directly with synthetic audio"""
    print("Creating test chord progression audio (C-F-G-C)...")
    audio, sr = create_chord_progression_audio()
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        sf.write(tmp_file.name, audio, sr)
        tmp_path = tmp_file.name
    
    try:
        print("Running chord extraction...")
        
        # Test with all tracks
        result = extract_chord_progression_midi(tmp_path, ['chords', 'bass', 'melody'])
        
        print(f"\n=== Chord Extraction Results ({result.get('method', 'unknown')}) ===")
        print(f"Total chords detected: {result.get('total_chords', 0)}")
        print(f"Tempo: {result.get('tempo', 'N/A')} BPM")
        print(f"Duration: {result.get('duration', 'N/A')} seconds")
        print(f"Tracks included: {result.get('tracks_included', [])}")
        
        if result.get('midi_download_url'):
            print(f"MIDI file: {result['midi_download_url']}")
        
        if result.get('chord_progression'):
            print("\nDetected Chord Progression:")
            for i, chord in enumerate(result['chord_progression'][:8]):  # Show first 8 chords
                time_val = chord.get('time', 'N/A')
                chord_name = chord.get('chord_name', 'Unknown')
                confidence = chord.get('confidence', 'N/A')
                notes = chord.get('notes', [])
                print(f"  {i+1}. Time {time_val}s: {chord_name} (confidence: {confidence}) - Notes: {notes}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        print("\n=== Direct test completed! ===")
        
        return result.get('midi_download_url') is not None
        
    finally:
        # Clean up
        os.unlink(tmp_path)

def test_api_endpoint():
    """Test the API endpoint with a local server"""
    print("\n=== Testing API Endpoint ===")
    
    # Create test audio
    audio, sr = create_chord_progression_audio()
    
    # Save to a temporary file that can be served
    test_file = "/tmp/test_chord_progression.wav"
    sf.write(test_file, audio, sr)
    
    try:
        # Test the API endpoint
        api_url = "http://localhost:5000/extract-chords-midi"
        
        # Create a mock audio URL (in real usage, this would be from Tonn.roexaudio.com)
        payload = {
            "audio_url": f"file://{test_file}",  # Local file for testing
            "include_tracks": ["chords", "bass"]  # Test selective track inclusion
        }
        
        headers = {
            "X-API-Key": "test123",
            "Content-Type": "application/json"
        }
        
        print("Making API request...")
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API request successful!")
            print(f"Chord progression detected: {result.get('total_chords', 0)} chords")
            print(f"MIDI download URL: {result.get('midi_download_url', 'N/A')}")
            
            # Test MIDI download
            if result.get('midi_download_url'):
                midi_url = f"http://localhost:5000{result['midi_download_url']}"
                midi_response = requests.get(midi_url, headers={"X-API-Key": "test123"})
                
                if midi_response.status_code == 200:
                    print("✅ MIDI file download successful!")
                    print(f"MIDI file size: {len(midi_response.content)} bytes")
                else:
                    print(f"❌ MIDI download failed: {midi_response.status_code}")
            
            return True
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Make sure it's running on localhost:5000")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)

def test_track_selection():
    """Test different track combinations"""
    print("\n=== Testing Track Selection ===")
    
    audio, sr = create_chord_progression_audio()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        sf.write(tmp_file.name, audio, sr)
        tmp_path = tmp_file.name
    
    try:
        # Test different track combinations
        track_combinations = [
            ['chords'],
            ['bass'],
            ['melody'],
            ['chords', 'bass'],
            ['chords', 'melody'],
            ['bass', 'melody'],
            ['chords', 'bass', 'melody']
        ]
        
        for tracks in track_combinations:
            print(f"\nTesting tracks: {tracks}")
            result = extract_chord_progression_midi(tmp_path, tracks)
            
            if result.get('tracks_included'):
                print(f"✅ Successfully created MIDI with tracks: {result['tracks_included']}")
            else:
                print(f"❌ Failed to create MIDI for tracks: {tracks}")
                if result.get('error'):
                    print(f"   Error: {result['error']}")
    
    finally:
        os.unlink(tmp_path)

if __name__ == "__main__":
    print("🎵 Testing Chord Extraction and MIDI Export Functionality 🎵\n")
    
    # Test 1: Direct function call
    direct_success = test_chord_extraction_direct()
    
    # Test 2: Track selection
    test_track_selection()
    
    # Test 3: API endpoint (only if server is running)
    api_success = test_api_endpoint()
    
    print(f"\n=== Test Summary ===")
    print(f"Direct chord extraction: {'✅ PASSED' if direct_success else '❌ FAILED'}")
    print(f"API endpoint test: {'✅ PASSED' if api_success else '❌ FAILED (server may not be running)'}")
    print("\n🎉 Chord extraction testing completed!")