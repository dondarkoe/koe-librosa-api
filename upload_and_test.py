#!/usr/bin/env python3
"""
Upload your own audio files and test chord extraction
"""

import os
import shutil
import requests
import json
from app import extract_chord_progression_midi

def test_uploaded_file(file_path, tracks=['chords', 'bass', 'melody']):
    """Test chord extraction with an uploaded file"""
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"🎵 Analyzing: {os.path.basename(file_path)}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    print(f"Tracks to extract: {tracks}")
    
    try:
        # Direct function call for faster testing
        result = extract_chord_progression_midi(file_path, tracks)
        
        print(f"\n=== Analysis Results ===")
        print(f"Method: {result.get('method', 'unknown')}")
        print(f"Total chords: {result.get('total_chords', 0)}")
        print(f"Tempo: {result.get('tempo', 'N/A')} BPM")
        print(f"Duration: {result.get('duration', 'N/A')} seconds")
        
        if result.get('error'):
            print(f"❌ Error: {result['error']}")
            return
        
        if result.get('chord_progression'):
            print(f"\n=== Chord Progression ===")
            for i, chord in enumerate(result['chord_progression'][:10]):  # Show first 10 chords
                time_val = chord.get('time', 'N/A')
                chord_name = chord.get('chord_name', 'Unknown')
                confidence = chord.get('confidence', 'N/A')
                notes = chord.get('notes', [])
                print(f"{i+1:2d}. {time_val:5.1f}s: {chord_name:15s} (conf: {confidence}) - {notes}")
        
        if result.get('midi_download_url'):
            midi_file = result['midi_download_url'].replace('/download-midi/', '/tmp/')
            if os.path.exists(midi_file):
                print(f"\n✅ MIDI file created: {midi_file}")
                print(f"MIDI file size: {os.path.getsize(midi_file)} bytes")
                print(f"You can drag this file into Ableton Live!")
            else:
                print(f"❌ MIDI file not found: {midi_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

def batch_test_directory(directory_path, file_extensions=['.wav', '.mp3', '.m4a', '.flac']):
    """Test all audio files in a directory"""
    
    if not os.path.exists(directory_path):
        print(f"❌ Directory not found: {directory_path}")
        return
    
    print(f"🎵 Batch testing directory: {directory_path}")
    
    audio_files = []
    for file in os.listdir(directory_path):
        if any(file.lower().endswith(ext) for ext in file_extensions):
            audio_files.append(os.path.join(directory_path, file))
    
    if not audio_files:
        print(f"❌ No audio files found in {directory_path}")
        return
    
    print(f"Found {len(audio_files)} audio files")
    
    results = []
    for file_path in audio_files:
        print(f"\n{'='*60}")
        result = test_uploaded_file(file_path, ['chords', 'bass'])
        if result:
            results.append({
                'file': os.path.basename(file_path),
                'chords': result.get('total_chords', 0),
                'tempo': result.get('tempo', 0),
                'method': result.get('method', 'unknown')
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("BATCH TEST SUMMARY")
    print(f"{'='*60}")
    for r in results:
        print(f"{r['file']:30s} | {r['chords']:3d} chords | {r['tempo']:6.1f} BPM | {r['method']}")

def setup_test_environment():
    """Set up directories for testing"""
    
    test_dir = "/tmp/audio_test"
    os.makedirs(test_dir, exist_ok=True)
    
    print(f"📁 Test directory created: {test_dir}")
    print(f"You can copy your audio files to this directory for testing.")
    print(f"Supported formats: .wav, .mp3, .m4a, .flac")
    
    return test_dir

if __name__ == "__main__":
    print("🎵 Audio File Upload and Test Utility 🎵\n")
    
    # Setup test environment
    test_dir = setup_test_environment()
    
    # Example usage
    print("\nExample usage:")
    print("1. Copy your audio files to /tmp/audio_test/")
    print("2. Run: python upload_and_test.py")
    print("3. Or test a specific file:")
    print("   python -c \"from upload_and_test import test_uploaded_file; test_uploaded_file('/path/to/your/song.wav')\"")
    
    # Check if there are any files to test
    if os.path.exists(test_dir):
        audio_files = [f for f in os.listdir(test_dir) 
                      if f.lower().endswith(('.wav', '.mp3', '.m4a', '.flac'))]
        
        if audio_files:
            print(f"\nFound {len(audio_files)} audio files in test directory:")
            for f in audio_files:
                print(f"  - {f}")
            
            response = input("\nTest all files? (y/n): ")
            if response.lower() == 'y':
                batch_test_directory(test_dir)
        else:
            print(f"\nNo audio files found in {test_dir}")
            print("Copy some audio files there and run this script again!")
    
    print("\n🎉 Testing utility ready!")