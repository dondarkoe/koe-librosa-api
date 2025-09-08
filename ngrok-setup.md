# Ngrok Local Testing Setup

## Expose Your Local API to the Internet

### Step 1: Install Ngrok
```bash
# Download and install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Or use snap
sudo snap install ngrok
```

### Step 2: Start Your Local API
```bash
cd /workspace/koe-librosa-api
LIBROSA_API_KEY=test123 python app.py
```

### Step 3: Expose with Ngrok (New Terminal)
```bash
# Expose port 5000
ngrok http 5000
```

### Step 4: Get Your Public URL
Ngrok will show something like:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:5000
```

### Step 5: Test Your Public API
```bash
# Test with the ngrok URL
curl https://abc123.ngrok.io/

# Test chord extraction
curl -X POST https://abc123.ngrok.io/extract-chords-midi \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test123" \
  -d '{"audio_url": "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav", "include_tracks": ["chords"]}'
```

### Benefits:
- ✅ Instant public URL
- ✅ Test locally with real internet access
- ✅ Free tier available
- ✅ Great for quick testing
- ✅ Can test with Base44 frontend

### Limitations:
- ❌ URL changes each restart (free tier)
- ❌ 2-hour session limit (free tier)
- ❌ Requires local machine running