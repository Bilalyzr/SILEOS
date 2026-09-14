import { useRef, useState, useEffect, useCallback } from 'react';
import Hls from 'hls.js';

export function useVideoPlayer(streamUrl, lessonId, courseId, resumeAt = 0) {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const progressTimerRef = useRef(null);

  const [state, setState] = useState({
    playing: false, currentTime: 0, duration: 0,
    volume: 1, muted: false, playbackRate: 1,
    buffered: 0, fullscreen: false, ready: false, error: null
  });

  useEffect(() => {
    if (!streamUrl || !videoRef.current) return;
    const video = videoRef.current;
    if (hlsRef.current) hlsRef.current.destroy();

    if (Hls.isSupported()) {
      const hls = new Hls({ enableWorker: true, maxBufferLength: 30, progressive: true });
      hls.loadSource(streamUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setState(s => ({ ...s, ready: true }));
        if (resumeAt > 5) video.currentTime = resumeAt;
      });
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) setState(s => ({ ...s, error: 'Stream error. Please refresh.' }));
      });
      hlsRef.current = hls;
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl;
      video.addEventListener('loadedmetadata', () => {
        setState(s => ({ ...s, ready: true }));
        if (resumeAt > 5) video.currentTime = resumeAt;
      });
    }
    return () => hlsRef.current?.destroy();
  }, [streamUrl]);

  const saveProgress = useCallback(async (currentTime, duration) => {
    if (!lessonId || currentTime < 2) return;
    try {
      const token = localStorage.getItem('access_token');
      await fetch('/api/v1/progress/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ lesson_id: lessonId, course_id: courseId,
          watched_seconds: currentTime, total_seconds: duration })
      });
    } catch (_) {}
  }, [lessonId, courseId]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onTime = () => setState(s => ({ ...s, currentTime: video.currentTime, duration: video.duration || 0 }));
    const onBuf = () => {
      if (video.buffered.length > 0)
        setState(s => ({ ...s, buffered: (video.buffered.end(video.buffered.length-1) / video.duration) * 100 }));
    };
    video.addEventListener('timeupdate', onTime);
    video.addEventListener('progress', onBuf);
    video.addEventListener('play', () => setState(s => ({ ...s, playing: true })));
    video.addEventListener('pause', () => setState(s => ({ ...s, playing: false })));
    video.addEventListener('volumechange', () => setState(s => ({ ...s, volume: video.volume, muted: video.muted })));
    video.addEventListener('ended', () => saveProgress(video.duration, video.duration));
    progressTimerRef.current = setInterval(() => {
      if (!video.paused && video.currentTime > 0) saveProgress(video.currentTime, video.duration);
    }, 5000);
    return () => {
      clearInterval(progressTimerRef.current);
      video.removeEventListener('timeupdate', onTime);
      video.removeEventListener('progress', onBuf);
    };
  }, [saveProgress]);

  useEffect(() => {
    const handle = (e) => {
      const video = videoRef.current;
      if (!video || ['INPUT','TEXTAREA'].includes(e.target.tagName)) return;
      switch(e.key) {
        case ' ': case 'k': e.preventDefault(); video.paused ? video.play() : video.pause(); break;
        case 'ArrowRight': video.currentTime = Math.min(video.currentTime+10, video.duration); break;
        case 'ArrowLeft': video.currentTime = Math.max(video.currentTime-10, 0); break;
        case 'ArrowUp': e.preventDefault(); video.volume = Math.min(video.volume+0.1, 1); break;
        case 'ArrowDown': e.preventDefault(); video.volume = Math.max(video.volume-0.1, 0); break;
        case 'f': toggleFullscreen(); break;
        case 'm': video.muted = !video.muted; break;
      }
    };
    document.addEventListener('keydown', handle);
    return () => document.removeEventListener('keydown', handle);
  }, []);

  const toggleFullscreen = () => {
    const container = videoRef.current?.closest('.sasha-player');
    if (!document.fullscreenElement) {
      container?.requestFullscreen();
      setState(s => ({ ...s, fullscreen: true }));
    } else {
      document.exitFullscreen();
      setState(s => ({ ...s, fullscreen: false }));
    }
  };

  useEffect(() => {
    const onFsChange = () => {
      if (!document.fullscreenElement) setState(s => ({ ...s, fullscreen: false }));
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  const controls = {
    play: () => videoRef.current?.play(),
    pause: () => videoRef.current?.pause(),
    seek: (t) => { if (videoRef.current) videoRef.current.currentTime = t; },
    setVolume: (v) => { if (videoRef.current) { videoRef.current.volume = v; videoRef.current.muted = v === 0; } },
    setRate: (r) => { if (videoRef.current) { videoRef.current.playbackRate = r; setState(s => ({ ...s, playbackRate: r })); } },
    toggleFullscreen
  };

  return { videoRef, state, controls };
}
