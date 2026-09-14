import { useState, useEffect, useRef } from 'react';
import { useVideoPlayer } from '../../hooks/useVideoPlayer';

async function fetchStreamUrl(lessonId) {
  const token = localStorage.getItem('access_token');
  const t = await fetch(`/api/v1/video/token?lesson_id=${lessonId}`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then(r => r.json());
  const s = await fetch(`/api/v1/video/stream-url?token=${t.token}`).then(r => r.json());
  return s.url;
}

async function fetchResume(lessonId) {
  const token = localStorage.getItem('access_token');
  const r = await fetch(`/api/v1/progress/get/${lessonId}`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then(r => r.json());
  return r.watched_seconds || 0;
}

const RATES = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
const fmt = (s) => !s || isNaN(s) ? '0:00' : `${Math.floor(s/60)}:${Math.floor(s%60).toString().padStart(2,'0')}`;
const Btn = ({ onClick, children, style = {} }) => (
  <button onClick={onClick} style={{ background:'none', border:'none', color:'#fff',
    cursor:'pointer', padding:'4px 8px', fontSize:16, opacity:0.9, ...style }}>
    {children}
  </button>
);

export default function SashaPlayer({ lessonId, courseId, onComplete, onNext }) {
  const [streamUrl, setStreamUrl] = useState(null);
  const [resumeAt, setResumeAt] = useState(0);
  const [showControls, setShowControls] = useState(true);
  const [showRates, setShowRates] = useState(false);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const controlTimer = useRef(null);

  useEffect(() => {
    if (!lessonId) return;
    setLoading(true); setStreamUrl(null); setFetchError(null);
    Promise.all([fetchStreamUrl(lessonId), fetchResume(lessonId)])
      .then(([url, resume]) => { setStreamUrl(url); setResumeAt(resume); setLoading(false); })
      .catch(e => { setFetchError('Failed to load video.'); setLoading(false); });
  }, [lessonId]);

  const { videoRef, state, controls } = useVideoPlayer(streamUrl, lessonId, courseId, resumeAt);

  const resetTimer = () => {
    setShowControls(true);
    clearTimeout(controlTimer.current);
    controlTimer.current = setTimeout(() => {
      if (!videoRef.current?.paused) setShowControls(false);
    }, 3000);
  };

  const pct = state.duration > 0 ? (state.currentTime / state.duration) * 100 : 0;

  if (fetchError) return (
    <div style={{ aspectRatio:'16/9', background:'#111', display:'flex',
                  alignItems:'center', justifyContent:'center', color:'#f66', borderRadius:8 }}>
      {fetchError}
    </div>
  );

  return (
    <div className="sasha-player" onMouseMove={resetTimer}
      onMouseLeave={() => { if (!videoRef.current?.paused) setShowControls(false); }}
      onContextMenu={e => e.preventDefault()}
      style={{ position:'relative', background:'#000', borderRadius:8,
               overflow:'hidden', userSelect:'none', aspectRatio:'16/9', width:'100%' }}>

      <video ref={videoRef} style={{ width:'100%', height:'100%', display:'block' }}
        playsInline preload="metadata"
        onEnded={() => { onComplete?.(); setTimeout(() => onNext?.(), 3000); }} />

      {/* Spinner */}
      {(loading || (!state.ready && streamUrl)) && (
        <div style={{ position:'absolute', inset:0, display:'flex',
                      alignItems:'center', justifyContent:'center', background:'#000' }}>
          <div style={{ width:48, height:48, border:'4px solid #ff6b35',
                        borderTopColor:'transparent', borderRadius:'50%',
                        animation:'spin 0.8s linear infinite' }} />
        </div>
      )}

      {/* Centre play button */}
      {state.ready && !state.playing && (
        <div onClick={controls.play} style={{ position:'absolute', inset:0, display:'flex',
          alignItems:'center', justifyContent:'center', cursor:'pointer' }}>
          <div style={{ width:72, height:72, background:'rgba(255,107,53,0.92)', borderRadius:'50%',
                        display:'flex', alignItems:'center', justifyContent:'center',
                        fontSize:30, color:'#fff', paddingLeft:4 }}>▶</div>
        </div>
      )}

      {/* Controls */}
      {state.ready && (
        <div style={{ position:'absolute', bottom:0, left:0, right:0,
                      background:'linear-gradient(transparent, rgba(0,0,0,0.92))',
                      padding:'50px 14px 10px',
                      opacity: showControls ? 1 : 0, transition:'opacity 0.3s',
                      pointerEvents: showControls ? 'auto' : 'none' }}>

          {/* Seek bar */}
          <div onClick={e => {
                 const r = e.currentTarget.getBoundingClientRect();
                 controls.seek(((e.clientX - r.left) / r.width) * state.duration);
               }}
            style={{ position:'relative', height:4, background:'rgba(255,255,255,0.25)',
                     borderRadius:2, marginBottom:10, cursor:'pointer' }}>
            <div style={{ position:'absolute', height:'100%', background:'rgba(255,255,255,0.3)',
                          width:`${state.buffered}%`, borderRadius:2 }} />
            <div style={{ position:'absolute', height:'100%', background:'#ff6b35',
                          width:`${pct}%`, borderRadius:2 }} />
            <div style={{ position:'absolute', height:12, width:12, background:'#ff6b35',
                          borderRadius:'50%', top:-4, left:`${pct}%`,
                          transform:'translateX(-50%)' }} />
          </div>

          <div style={{ display:'flex', alignItems:'center', gap:8, color:'#fff' }}>
            <Btn onClick={() => state.playing ? controls.pause() : controls.play()}>
              {state.playing ? '⏸' : '▶'}
            </Btn>
            <Btn onClick={() => controls.seek(state.currentTime - 10)}>⏮10</Btn>
            <Btn onClick={() => controls.seek(state.currentTime + 10)}>10⏭</Btn>
            <span style={{ fontSize:12, opacity:0.85, minWidth:95 }}>
              {fmt(state.currentTime)} / {fmt(state.duration)}
            </span>
            <div style={{ flex:1 }} />
            <Btn onClick={() => controls.setVolume(state.muted || state.volume === 0 ? 1 : 0)}>
              {state.muted || state.volume === 0 ? '🔇' : state.volume < 0.5 ? '🔉' : '🔊'}
            </Btn>
            <input type="range" min={0} max={1} step={0.05}
              value={state.muted ? 0 : state.volume}
              onChange={e => controls.setVolume(parseFloat(e.target.value))}
              style={{ width:60, accentColor:'#ff6b35' }} />
            <div style={{ position:'relative' }}>
              <Btn onClick={() => setShowRates(r => !r)}>{state.playbackRate}x</Btn>
              {showRates && (
                <div style={{ position:'absolute', bottom:36, right:0, background:'#1c1c1c',
                              border:'1px solid #444', borderRadius:6, overflow:'hidden', minWidth:64, zIndex:10 }}>
                  {RATES.map(r => (
                    <button key={r} onClick={() => { controls.setRate(r); setShowRates(false); }}
                      style={{ display:'block', width:'100%', padding:'7px 14px', background:'none',
                               border:'none', color: r === state.playbackRate ? '#ff6b35' : '#fff',
                               cursor:'pointer', fontSize:13 }}>
                      {r}x
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Btn onClick={controls.toggleFullscreen}>{state.fullscreen ? '⊡' : '⛶'}</Btn>
          </div>
        </div>
      )}
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
