# Video Player Implementation Details

This document provides a detailed breakdown of how the video player in the SashaInfinity platform is implemented. It covers the entire process from the backend video link extraction to the frontend rendering, highlighting the key modules and code snippets involved.

## Overview

The core of the video player functionality is to display YouTube videos without YouTube's branding. This is achieved by using `yt-dlp` on the backend to extract the direct video URL and then playing it in a custom HTML5 video player on the frontend.

## Backend: Video Link Extraction

The backend is responsible for taking a YouTube video ID and returning a direct, playable video URL. This is handled by a Django view that uses the `yt-dlp` library.

### Modules Used

-   **Django REST Framework**: Used to create the API endpoint for video extraction.
-   **yt-dlp**: A powerful command-line tool and Python library to download videos and audio from YouTube and other video hosting sites. It's used here to extract video information and direct stream URLs.

### Process

1.  An API endpoint `/api/extract/` is defined in `backend/courses/urls.py` to handle video extraction requests.
2.  The `extract_video` view in `backend/courses/views.py` receives a YouTube video ID.
3.  It uses `yt-dlp` to fetch the video's metadata and direct stream URL. The quality is set to a maximum of 720p by default.
4.  The extracted URL is cached in memory for 4 hours to reduce redundant calls to `yt-dlp` and to avoid being rate-limited by YouTube.
5.  The view returns a JSON response containing the video URL, title, duration, and quality.

### Code: `backend/courses/views.py`

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
import yt_dlp
import re
import time

# In-memory cache for video URLs
video_url_cache = {}

@api_view(['GET'])
def extract_video(request):
    """Extract direct video URL from YouTube using yt-dlp"""
    video_id = request.GET.get('id')
    quality = request.GET.get('quality', '720')

    if not video_id or not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        return Response({'error': 'Invalid video ID'}, status=400)

    cache_key = f"{video_id}:{quality}"

    # Check cache first
    if cache_key in video_url_cache:
        cached = video_url_cache[cache_key]
        if cached['expires'] > time.time():
            return Response({**cached, 'cached': True})

    try:
        ydl_opts = {
            'format': f'best[height<={quality}][ext=mp4]/best[ext=mp4]/best',
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f'https://www.youtube.com/watch?v={video_id}'
            info = ydl.extract_info(url, download=False)

            result = {
                'videoId': video_id,
                'title': info.get('title'),
                'url': info.get('url'),
                'duration': info.get('duration'),
                'quality': f"{info.get('height', 'unknown')}p",
                'expires': time.time() + (4 * 60 * 60),  # 4 hours
                'cached': False
            }

            # Cache the result
            video_url_cache[cache_key] = result

            return Response(result)

    except Exception as e:
        return Response({'error': str(e)}, status=500)
```

## Frontend: Video Rendering

The frontend is a Next.js application that features a custom video player page. This page fetches the video URL from the backend and renders it using a standard HTML5 `<video>` element, with custom controls and branding.

### Modules Used

-   **React**: For building the user interface components.
-   **Next.js**: For server-side rendering and routing.
-   **axios**: For making HTTP requests to the backend API.
-   **IndexedDB**: For client-side caching of video URLs to improve performance on subsequent visits.

### Process

1.  The `CoursePlayer` component in `frontend/pages/course/[id].js` gets the course and lesson ID from the URL.
2.  It calls the `loadVideoUrl` function, which first checks for a cached video URL in the browser's IndexedDB.
3.  If not found in the local cache, it makes an API call to the backend's `/api/extract/` endpoint with the YouTube video ID.
4.  Once the direct video URL is received, it's stored in the component's state and cached in IndexedDB for future use.
5.  The video is rendered using an HTML5 `<video>` tag, with the `src` attribute set to the extracted URL.
6.  Custom controls for play, pause, volume, seek, and fullscreen are implemented using React state and event handlers that interact with the `<video>` element's API.

### Code: `frontend/pages/course/[id].js`

Here are the key parts of the `CoursePlayer` component responsible for fetching and rendering the video.

```javascript
// ... imports

export default function CoursePlayer() {
    // ... state variables for video player

    const [db, setDb] = useState(null);

    useEffect(() => {
        // Initialize IndexedDB
        const request = indexedDB.open('VideoCache', 1);
        request.onsuccess = () => setDb(request.result);
        // ... (onupgradeneeded for schema)
    }, []);


    const loadVideoUrl = async () => {
        const videoId = extractVideoId(currentLesson?.video_url);
        // ...

        // Check local cache first
        const cached = await getFromCache(videoId);
        if (cached && cached.url) {
            setVideoUrl(cached.url);
            // ...
            return;
        }

        // Fetch from Django backend
        const response = await fetch(`${API_URL}/extract/?id=${videoId}&quality=720`);
        const data = await response.json();

        // Cache locally
        await setToCache(videoId, data);

        setVideoUrl(data.url);
        // ...
    };

    // ... (getFromCache and setToCache functions for IndexedDB)

    return (
        // ...
        <div className="player-wrapper">
            {videoUrl && !error && (
                <video
                    ref={videoRef}
                    src={videoUrl}
                    // ... event handlers for play, pause, timeupdate, etc.
                />
            )}
            {/* ... custom controls UI */}
        </div>
        // ...
    );
}

```

This setup ensures that the video is streamed directly from YouTube's CDN to the user's browser, but within a custom-branded player, providing a professional and seamless viewing experience.
