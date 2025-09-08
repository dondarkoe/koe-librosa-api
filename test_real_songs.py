#!/usr/bin/env python3
"""
Test chord extraction with real songs using public audio URLs
"""

import requests
import json
import time

def test_with_public_audio():
    """Test with publicly available audio files"""
    
    # Public domain / Creative Commons audio files for testing
    test_songs = [
        {
            "name": "Classical Piano",
            "url": "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
            "tracks": ["chords", "bass"]
        },
        {
            "name": "Simple Melody",
            "url": "https://www.soundjay.com/misc/sounds/fail-buzzer-02.wav", 
            "tracks": ["chords", "melody"]
        }
    ]
    
    api_url = "http://localhost:5000/extract-chords-midi"
    headers = {
        "X-API-Key": "test123",
        "Content-Type": "application/json"
    }
    
    print("🎵 Testing Chord Extraction with Real Audio Files 🎵\n")
    
    for song in test_songs:
        print(f"Testing: {song['name']}")
        print(f"URL: {song['url']}")
        print(f"Tracks: {song['tracks']}")
        
        payload = {
            "audio_url": song['url'],
            "include_tracks": song['tracks']
        }
        
        try:
            print("Making API request...")
            response = requests.post(api_url, json=payload, headers=headers, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Success!")
                print(f"Method: {result.get('method', 'unknown')}")
                print(f"Chords detected: {result.get('total_chords', 0)}")
                print(f"Tempo: {result.get('tempo', 'N/A')} BPM")
                print(f"Duration: {result.get('duration', 'N/A')} seconds")
                
                if result.get('chord_progression'):
                    print("Chord progression:")
                    for i, chord in enumerate(result['chord_progression'][:5]):
                        print(f"  {i+1}. {chord['time']}s: {chord['chord_name']} - {chord['notes']}")
                
                if result.get('midi_download_url'):
                    print(f"MIDI download: {result['midi_download_url']}")
                    
                    # Test MIDI download
                    midi_url = f"http://localhost:5000{result['midi_download_url']}"
                    midi_response = requests.get(midi_url)
                    if midi_response.status_code == 200:
                        print(f"✅ MIDI file downloaded ({len(midi_response.content)} bytes)")
                    else:
                        print("❌ MIDI download failed")
                
            else:
                print(f"❌ API request failed: {response.status_code}")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
        
        print("-" * 50)
        time.sleep(2)  # Brief pause between tests

def test_with_local_file():
    """Test with a local audio file"""
    print("\n🎵 Testing with Local File 🎵")
    
    # You can place your own audio files here
    local_files = [
        "/tmp/my_song.wav",
        "/tmp/my_song.mp3",
        # Add your file paths here
    ]
    
    for file_path in local_files:
        import os
        if os.path.exists(file_path):
            print(f"Testing local file: {file_path}")
            
            # For local testing, we can call the function directly
            from app import extract_chord_progression_midi
            
            try:
                result = extract_chord_progression_midi(file_path, ['chords', 'bass', 'melody'])
                print("✅ Local file analysis complete!")
                print(f"Method: {result.get('method', 'unknown')}")
                print(f"Chords: {result.get('total_chords', 0)}")
                print(f"Tempo: {result.get('tempo', 'N/A')} BPM")
                
                if result.get('chord_progression'):
                    print("First few chords:")
                    for chord in result['chord_progression'][:3]:
                        print(f"  {chord['time']}s: {chord['chord_name']}")
                        
            except Exception as e:
                print(f"❌ Local file test failed: {e}")
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    # Test with public URLs
    test_with_public_audio()
    
    # Test with local files
    test_with_local_file()
    
    print("\n🎉 Real song testing completed!")