# Railway Test Deployment Setup

## Create a Test Railway Deployment

### Step 1: Create a New Railway Project
1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Choose "Deploy from GitHub repo"
4. Select your `koe-librosa-api` repository
5. Name it something like `koe-librosa-api-test`

### Step 2: Set Environment Variables
In your Railway test project dashboard:
```
LIBROSA_API_KEY=your_test_api_key_here
PORT=5000
```

### Step 3: Deploy Current Branch
```bash
# Create a test branch
git checkout -b test-chord-extraction

# Push to trigger deployment
git push origin test-chord-extraction
```

### Step 4: Get Your Test Domain
Railway will provide a domain like:
```
https://koe-librosa-api-test-production.up.railway.app
```

### Step 5: Test the API
```bash
# Test health check
curl https://your-test-domain.railway.app/

# Test chord extraction
curl -X POST https://your-test-domain.railway.app/extract-chords-midi \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_test_api_key_here" \
  -d '{"audio_url": "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav", "include_tracks": ["chords", "bass"]}'
```

### Benefits:
- ✅ Free Railway subdomain
- ✅ Same production environment
- ✅ Easy to test Basic Pitch compatibility
- ✅ No risk to production API
- ✅ Can test with Base44 frontend integration