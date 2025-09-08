#!/usr/bin/env python3
"""
Test chord extraction with YouTube audio (requires yt-dlp)
WARNING: Only use this with copyright-free or your own content!
"""

import os
import subprocess
import tempfile
from app import extract_chord_progression_midi

def download_youtube_audio(youtube_url, output_path="/tmp/youtube_audio.wav"):
    """Download audio from YouTube using yt-dlp"""
    
    try:
        # Check if yt-dlp is installed
        subprocess.run(["yt-dlp", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ yt-dlp not installed. Install with: pip install yt-dlp")
        return None
    
    try:
        print(f"📥 Downloading audio from: {youtube_url}")
        
        # Download audio only, convert to wav
        cmd = [
            "yt-dlp",
            "-x",  # Extract audio only
            "--audio-format", "wav",
            "--audio-quality", "0",  # Best quality
            "-o", output_path.replace('.wav', '.%(ext)s'),
            youtube_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Download completed!")
            return output_path
        else:
            print(f"❌ Download failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Download timed out (5 minutes)")
        return None
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None

def test_youtube_song(youtube_url, tracks=['chords', 'bass']):
    """Test chord extraction with a YouTube video"""
    
    print(f"🎵 Testing YouTube URL: {youtube_url}")
    
    # Download audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        audio_path = download_youtube_audio(youtube_url, tmp_file.name)
    
    if not audio_path or not os.path.exists(audio_path):
        print("❌ Failed to download audio")
        return None
    
    try:
        print(f"🎵 Analyzing downloaded audio...")
        print(f"File size: {os.path.getsize(audio_path)} bytes")
        
        # Analyze the audio
        result = extract_chord_progression_midi(audio_path, tracks)
        
        print(f"\n=== Analysis Results ===")
        print(f"Method: {result.get('method', 'unknown')}")
        print(f"Total chords: {result.get('total_chords', 0)}")
        print(f"Tempo: {result.get('tempo', 'N/A')} BPM")
        print(f"Duration: {result.get('duration', 'N/A')} seconds")
        
        if result.get('chord_progression'):
            print(f"\n=== First 8 Chords ===")
            for i, chord in enumerate(result['chord_progression'][:8]):
                time_val = chord.get('time', 'N/A')
                chord_name = chord.get('chord_name', 'Unknown')
                notes = chord.get('notes', [])
                print(f"{i+1}. {time_val:5.1f}s: {chord_name:15s} - {notes}")
        
        if result.get('midi_download_url'):
            midi_file = result['midi_download_url'].replace('/download-midi/', '/tmp/')
            if os.path.exists(midi_file):
                print(f"\n✅ MIDI file: {midi_file}")
                print("🎹 Ready to drag into Ableton Live!")
        
        return result
        
    finally:
        # Clean up downloaded file
        if os.path.exists(audio_path):
            os.unlink(audio_path)

if __name__ == "__main__":
    print("🎵 YouTube Audio Chord Extraction Test 🎵")
    print("⚠️  WARNING: Only use with copyright-free or your own content!")
    print()
    
    # Example copyright-free/public domain URLs for testing
    test_urls = [
        # Add copyright-free YouTube URLs here for testing
        # "https://www.youtube.com/watch?v=EXAMPLE_ID",
    ]
    
    if not test_urls:
        print("No test URLs configured.")
        print("Add copyright-free YouTube URLs to the test_urls list.")
        print()
        print("Example usage:")
        print("python -c \"from test_youtube import test_youtube_song; test_youtube_song('YOUR_URL')\"")
    else:
        for url in test_urls:
            test_youtube_song(url)
            print("-" * 60)
    
    print("\n🎉 YouTube testing utility ready!")