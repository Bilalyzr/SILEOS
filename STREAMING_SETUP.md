# YouTube Video Streaming Setup

## Overview

This document explains the new YouTube video streaming proxy implementation for SashaInfinity LMS. The setup includes a standalone streaming service that handles YouTube video extraction and streaming server-side.

## Architecture

### New Architecture (Current)
```
Frontend → Nginx → Streaming Service (Port 8001)
```

### Old Architecture (Deprecated)
```
Frontend → Nginx → Backend (Port 8000) → YouTube Extraction
```

## Components

### 1. Streaming Service (`/streaming-service/`)
- **Dockerfile**: Container configuration
- **requirements.txt**: Python dependencies
- **video_streaming.py**: Main streaming application

**Features:**
- FastAPI-based streaming service
- yt-dlp integration for video extraction
- HTTP Range request support
- 10-minute caching
- Health monitoring

### 2. Nginx Configuration (`/nginx/conf.d/default.conf`)
Updated routing:
- `/api/v1/stream/` → Streaming Service (Port 8001)
- `/api/v1/extract/` → Commented out (old method)
- Other `/api/v1/` → Backend (Port 8000)

### 3. Frontend Updates (`/frontend/`)
- **YouTube Extracted Player**: Updated to use `stream/{video_id}` endpoints
- **Media Utils**: Enhanced URL resolution for streaming endpoints

### 4. Backend Updates (`/backend/`)
- **Video Router**: Old method commented out for reference
- **Main App**: Updated video_streaming router integration

## API Endpoints

### New Streaming Endpoints
All endpoints accessible via: `http://localhost:8000/api/v1/stream/`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service status and usage info |
| `/stream/{video_id}` | GET | Direct video streaming with range support |
| `/info/{video_id}` | GET | Video metadata (title, duration, thumbnail) |
| `/extract` | GET | Video extraction with caching |
| `/cache/status` | GET | Cache status information |
| `/health` | GET | Health check |

### Example Usage

#### Stream Video
```bash
curl -I "http://localhost:8000/api/v1/stream/dQw4w9WgXcQ"
```

#### Get Video Info
```bash
curl "http://localhost:8000/api/v1/stream/info/dQw4w9WgXcQ"
```

#### Extract Video
```bash
curl "http://localhost:8000/api/v1/stream/extract?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Deployment

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- yt-dlp
- FFmpeg

### Quick Deployment
```bash
./deploy_streaming.sh
```

### Manual Deployment
```bash
# Build streaming service
cd streaming-service
docker build -t sashainfinity-streaming-service .

# Build frontend
cd ../frontend
docker build -t sashainfinity-frontend .

# Build backend
cd ../backend
docker build -t sashainfinity-backend .

# Start services
cd ..
docker-compose up -d
```

## Configuration

### Environment Variables
```bash
# Streaming Service
PYTHONIOENCODING=utf-8
PYTHONUTF8=1

# Cache TTL (seconds)
CACHE_TTL=600

# Video quality
DEFAULT_QUALITY=720
```

### Nginx Stream Configuration
```nginx
location /api/v1/stream/ {
    proxy_pass http://streaming-service:8001/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Stream-specific headers
    proxy_buffering off;
    proxy_cache off;
    proxy_request_buffering off;
    proxy_max_temp_file_size 0;

    # Timeouts
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    client_max_body_size 1G;
}
```

## Features

### 1. Server-Side Streaming
- **No YouTube Branding**: Videos stream through your server
- **IP Protection**: Your backend IP is used for extraction
- **No Token Issues**: Eliminates YouTube API token expiration

### 2. Performance Optimizations
- **Caching**: 10-minute cache for extracted URLs
- **Range Requests**: Proper seeking functionality
- **Chunked Streaming**: 64KB chunks for efficient streaming
- **Concurrent Processing**: Async HTTP client for better performance

### 3. Error Handling
- **Retry Logic**: Multiple extraction attempts
- **Fallback URLs**: Progressive MP4 fallback
- **Health Monitoring**: Service health checks
- **Graceful Degradation**: Fallback to old method if needed

### 4. Security
- **CORS Support**: Proper cross-origin configuration
- **Header Masking**: User-Agent and Referer headers
- **Rate Limiting**: Nginx rate limiting support
- **Access Control**: Proper proxy headers

## Troubleshooting

### Common Issues

#### 1. Service Not Starting
```bash
# Check container logs
docker-compose logs streaming-service

# Check service health
curl http://localhost:8001/health
```

#### 2. Video Extraction Failing
```bash
# Test extraction directly
curl "http://localhost:8000/api/v1/stream/extract?url=https://www.youtube.com/watch?v=VIDEO_ID"

# Check streaming service logs
docker-compose logs streaming-service
```

#### 3. Frontend Not Loading
```bash
# Check frontend build
cd frontend && npm run build

# Check container status
docker-compose ps
```

### Debug Commands

#### Test Streaming Service
```bash
# Health check
curl http://localhost:8001/health

# Root endpoint
curl http://localhost:8001/

# Cache status
curl http://localhost:8001/cache/status
```

#### Test Video Streaming
```bash
# Get video info
curl "http://localhost:8000/api/v1/stream/info/dQw4w9WgXcQ"

# Stream video (range request)
curl -I -H "Range: bytes=0-1024" "http://localhost:8000/api/v1/stream/dQw4w9WgXcQ"
```

## Monitoring

### Service Health
```bash
# Check all services
docker-compose ps

# Check streaming service specifically
docker-compose logs streaming-service --tail=50

# Check resource usage
docker stats
```

### Performance Metrics
- **Cache Hit Rate**: Monitor `/cache/status` endpoint
- **Response Time**: Track streaming response times
- **Error Rates**: Monitor HTTP error codes
- **Bandwidth Usage**: Monitor container network traffic

## Backup and Recovery

### Configuration Backup
```bash
# Backup important files
tar -czf streaming_backup.tar.gz \
  streaming-service/ \
  nginx/conf.d/ \
  backend/app/routers/video.py \
  deploy_streaming.sh
```

### Service Recovery
```bash
# Stop and remove containers
docker-compose down

# Remove old images
docker system prune -f

# Restart services
docker-compose up -d
```

## Future Improvements

### 1. Scaling
- **Horizontal Scaling**: Multiple streaming service instances
- **Load Balancing**: Nginx upstream configuration
- **Redis Caching**: Centralized cache management

### 2. Enhanced Features
- **Video Transcoding**: On-the-fly format conversion
- **DRM Support**: Content protection
- **Analytics**: Usage statistics and monitoring
- **CDN Integration**: Cloud-based streaming

### 3. Performance
- **Edge Caching**: CDN edge caching
- **Protocol Optimization**: HLS/DASH support
- **Adaptive Streaming**: Quality adjustment based on bandwidth

## Migration Guide

### From Old to New Method
1. **Deploy New Service**: Run deployment script
2. **Update Frontend**: Ensure using new endpoints
3. **Monitor Performance**: Check streaming quality
4. **Decommission Old**: Remove old method when stable

### Rollback Procedure
```bash
# Stop new service
docker-compose down

# Remove streaming service
docker-compose rm streaming-service

# Uncomment old method in backend/app/routers/video.py

# Restart services
docker-compose up -d
```

## Support

For technical support:
1. Check service logs: `docker-compose logs streaming-service`
2. Test endpoints manually using curl
3. Verify Nginx configuration
4. Check network connectivity between services

## License

This setup is part of SashaInfinity LMS and follows the project's licensing terms.