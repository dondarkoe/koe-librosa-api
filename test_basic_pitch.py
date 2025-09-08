#!/usr/bin/env python3
"""
Test script for Basic Pitch integration
"""

import numpy as np
import soundfile as sf
import tempfile
import os
from app import analyze_basic_pitch

def create_test_audio():
    """Create a simple test audio file with known notes"""
    # Generate a simple melody: C4, E4, G4 (C major chord)
    sample_rate = 22050
    duration = 2.0  # 2 seconds
    
    # Note frequencies
    c4 = 261.63  # C4
    e4 = 329.63  # E4
    g4 = 392.00  # G4
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create simple sine waves for each note
    note1 = 0.3 * np.sin(2 * np.pi * c4 * t[:len(t)//3])  # First third
    note2 = 0.3 * np.sin(2 * np.pi * e4 * t[len(t)//3:2*len(t)//3])  # Second third
    note3 = 0.3 * np.sin(2 * np.pi * g4 * t[2*len(t)//3:])  # Last third
    
    # Combine notes
    audio = np.concatenate([note1, note2, note3])
    
    return audio, sample_rate

def test_basic_pitch():
    """Test Basic Pitch analysis with synthetic audio"""
    print("Creating test audio...")
    audio, sr = create_test_audio()
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        sf.write(tmp_file.name, audio, sr)
        tmp_path = tmp_file.name
    
    try:
        print("Running Basic Pitch analysis...")
        result = analyze_basic_pitch(tmp_path)
        
        print(f"\n=== Music Theory Analysis Results ({result.get('method', 'unknown')}) ===")
        print(f"Total notes detected: {result.get('total_notes', 0)}")
        
        if result.get('pitch_range'):
            pr = result['pitch_range']
            print(f"Pitch range: {pr.get('lowest_note', 'N/A')} to {pr.get('highest_note', 'N/A')}")
            if 'range_semitones' in pr:
                print(f"Range in semitones: {pr['range_semitones']}")
            elif 'range_octaves' in pr:
                print(f"Range in octaves: {pr['range_octaves']}")
        
        if result.get('most_common_notes'):
            print("Most common notes:")
            for item in result['most_common_notes']:
                if isinstance(item, tuple) and len(item) == 2:
                    note, count = item
                    if isinstance(count, (int, float)) and count > 1:
                        print(f"  {note}: {count} times")
                    else:
                        print(f"  {note}: strength {count:.3f}")
        
        if result.get('note_durations'):
            nd = result['note_durations']
            if 'average' in nd:
                print(f"Average note duration: {nd['average']} seconds")
            elif 'average_onset_interval' in nd:
                print(f"Average onset interval: {nd['average_onset_interval']} seconds")
        
        if result.get('melody_line'):
            print("Melody line (first 10 notes):")
            for i, note in enumerate(result['melody_line'][:10]):
                time_val = note.get('time', 'N/A')
                note_name = note.get('note_name', 'N/A')
                print(f"  {i+1}. Time {time_val}s: {note_name}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        print("\n=== Test completed successfully! ===")
        
    finally:
        # Clean up
        os.unlink(tmp_path)

if __name__ == "__main__":
    test_basic_pitch()