import yt_dlp
import json

# Test with a known safe video (Rick Roll or similar stable video)
url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 

print(f"Attempting to extract video from: {url}")
print(f"Using yt-dlp version: {yt_dlp.version.__version__}")

opts = {
    'quiet': True,
    'format': 'best[ext=mp4]/best',
    'no_warnings': True,
    # 'proxy': '...', # Uncomment if testing proxy
}

try:
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("\nSUCCESS! Extraction worked.")
        print(f"Title: {info.get('title')}")
        print(f"Direct URL: {info.get('url')[:50]}...")
        print(f"Duration: {info.get('duration')}s")
except Exception as e:
    print(f"\nFAILED: {e}")
