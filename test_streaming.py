#!/usr/bin/env python3
"""
Test script for YouTube video streaming endpoints
"""
import requests
import json
import time

def test_streaming_endpoints():
    """Test the new streaming endpoints"""
    base_url = "http://localhost:8000/api/v1"

    # Test video extraction endpoint
    print("🔍 Testing video extraction endpoint...")

    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    try:
        response = requests.get(
            f"{base_url}/extract/video",
            params={"url": test_url, "quality": "720"}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data", {}).get("videoId"):
                video_id = data["data"]["videoId"]
                print(f"✅ Video extraction successful! Video ID: {video_id}")

                # Test video info endpoint
                print("🔍 Testing video info endpoint...")
                info_response = requests.get(f"{base_url}/stream/info/{video_id}")
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    print(f"✅ Video info retrieved: {info_data.get('title', 'Unknown')}")

                # Test cache status endpoint
                print("🔍 Testing cache status endpoint...")
                cache_response = requests.get(f"{base_url}/stream/cache/status")
                if cache_response.status_code == 200:
                    cache_data = cache_response.json()
                    print(f"✅ Cache status: {cache_data.get('cache_size', 0)} cached videos")

                return True
            else:
                print(f"❌ Video extraction failed: {data}")
                return False
        else:
            print(f"❌ Video extraction request failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error testing video extraction: {e}")
        return False

def test_streaming_root():
    """Test the streaming root endpoint"""
    print("🔍 Testing streaming root endpoint...")

    try:
        response = requests.get("http://localhost:8000/api/v1/stream/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Streaming root endpoint working: {data}")
            return True
        else:
            print(f"❌ Streaming root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing streaming root: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing YouTube Video Streaming Proxy")
    print("=" * 50)

    # Wait for backend to be ready
    print("⏳ Waiting for backend to start...")
    time.sleep(5)

    # Test streaming root endpoint
    streaming_ok = test_streaming_root()

    # Test video extraction endpoints
    extraction_ok = test_streaming_endpoints()

    print("\n📊 Test Results:")
    print(f"Streaming Root: {'✅' if streaming_ok else '❌'}")
    print(f"Video Extraction: {'✅' if extraction_ok else '❌'}")

    if streaming_ok and extraction_ok:
        print("\n🎉 All tests passed! YouTube streaming proxy is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the backend logs for details.")