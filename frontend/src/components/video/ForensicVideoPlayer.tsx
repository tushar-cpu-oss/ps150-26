import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { Maximize, Pause, Play, Volume2, VolumeX } from 'lucide-react';
import { fetchBlob } from '../../api/client';
import { streamPath, streamUrl } from '../../api/evidence';
import { fmtClock } from '../../lib/format';
import type { Detection } from '../../types';
import { ErrorState } from '../common/ui';

export interface PlayerHandle { seek: (t: number) => void; current: () => number }
interface Props { evidenceId: string; selected?: Detection | null; initialTime?: number; onTime?: (t: number) => void; onDuration?: (d: number) => void }

const ForensicVideoPlayer = forwardRef<PlayerHandle, Props>(function Player({ evidenceId, selected, initialTime, onTime, onDuration }, ref) {
  const v = useRef<HTMLVideoElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const [src, setSrc] = useState(() => streamUrl(evidenceId));
  const [triedBlob, setTriedBlob] = useState(false);
  const [failed, setFailed] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [cur, setCur] = useState(0);
  const [dur, setDur] = useState(0);
  const [vol, setVol] = useState(1);
  const [muted, setMuted] = useState(false);
  const [dims, setDims] = useState({ w: 0, h: 0 });

  useImperativeHandle(ref, () => ({
    seek: (t: number) => { if (v.current) { v.current.currentTime = t; setCur(t); } },
    current: () => v.current?.currentTime ?? 0,
  }));
  useEffect(() => { setSrc(streamUrl(evidenceId)); setTriedBlob(false); setFailed(false); }, [evidenceId]);

  const onError = async () => {
    if (triedBlob) { setFailed(true); return; }
    setTriedBlob(true);
    try { setSrc(URL.createObjectURL(await fetchBlob(streamPath(evidenceId)))); } catch { setFailed(true); }
  };

  const toggle = () => { const el = v.current; if (!el) return; if (el.paused) void el.play(); else el.pause(); };
  const near = selected && selected.bbox && Math.abs(cur - selected.timestamp) <= 1.5;
  let rect: { l: number; t: number; w: number; h: number } | null = null;
  if (near && selected?.bbox && dims.w) {
    const b = selected.bbox; const norm = Math.max(b.x1, b.y1, b.x2, b.y2) <= 1.5;
    const fx = norm ? 1 : 1 / dims.w, fy = norm ? 1 : 1 / dims.h;
    rect = { l: b.x1 * fx * 100, t: b.y1 * fy * 100, w: (b.x2 - b.x1) * fx * 100, h: (b.y2 - b.y1) * fy * 100 };
  }

  if (failed) return <ErrorState title="EVIDENCE STREAM UNAVAILABLE" text="The original evidence file could not be accessed." onRetry={() => { setFailed(false); setTriedBlob(false); setSrc(streamUrl(evidenceId)); }} />;

  return (
    <div ref={box} className="panel overflow-hidden bg-black scanline">
      <div className="relative">
        <video ref={v} src={src} className="w-full max-h-[62vh] bg-black block mx-auto" onClick={toggle} playsInline preload="metadata"
          onLoadedMetadata={(e) => {
            const el = e.currentTarget; setDur(el.duration); setDims({ w: el.videoWidth, h: el.videoHeight }); onDuration?.(el.duration);
            if (initialTime) { el.currentTime = initialTime; }
          }}
          onTimeUpdate={(e) => { setCur(e.currentTarget.currentTime); onTime?.(e.currentTarget.currentTime); }}
          onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onError={() => void onError()} />
        {rect && selected && (
          <div className="absolute pointer-events-none border-2 border-ice" style={{ left: `${rect.l}%`, top: `${rect.t}%`, width: `${rect.w}%`, height: `${rect.h}%` }}>
            <span className="absolute -top-6 left-[-2px] bg-ice text-bg0 text-[10px] font-mono px-1.5 py-0.5 whitespace-nowrap">{selected.label.toUpperCase()}{selected.confidence != null ? ` ${Math.round(selected.confidence <= 1 ? selected.confidence * 100 : selected.confidence)}%` : ''}</span>
          </div>
        )}
      </div>
      <div className="flex items-center gap-3 px-3 py-2 bg-bg1 border-t border-white/[0.07]">
        <button onClick={toggle} aria-label={playing ? 'Pause' : 'Play'} className="text-cool hover:text-ice">{playing ? <Pause size={18} /> : <Play size={18} />}</button>
        <input type="range" aria-label="Seek" min={0} max={dur || 1} step={0.1} value={cur} className="flex-1 accent-[#7CD4F7]"
          onChange={(e) => { const t = Number(e.target.value); if (v.current) v.current.currentTime = t; setCur(t); }} />
        <span className="mono text-xs text-slate-300 tabular-nums">{fmtClock(cur)} / {fmtClock(dur)}</span>
        <button aria-label={muted ? 'Unmute' : 'Mute'} onClick={() => { setMuted(!muted); if (v.current) v.current.muted = !muted; }} className="text-slate-300 hover:text-ice">{muted || vol === 0 ? <VolumeX size={16} /> : <Volume2 size={16} />}</button>
        <input type="range" aria-label="Volume" min={0} max={1} step={0.05} value={vol} className="w-20 accent-[#7CD4F7]"
          onChange={(e) => { const x = Number(e.target.value); setVol(x); if (v.current) { v.current.volume = x; } }} />
        <button aria-label="Fullscreen" className="text-slate-300 hover:text-ice" onClick={() => { void box.current?.requestFullscreen?.(); }}><Maximize size={16} /></button>
      </div>
    </div>
  );
});
export default ForensicVideoPlayer;
