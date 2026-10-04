import { fmtClock } from '../../lib/format';
import type { Detection, MotionEvent } from '../../types';

interface Props { duration: number; current: number; detections: Detection[]; motion: MotionEvent[]; onSeek: (t: number) => void; onPick?: (d: Detection) => void }

export default function VideoTimeline({ duration, current, detections, motion, onSeek, onPick }: Props) {
  if (!duration) return <p className="text-xs font-mono text-slate-500 tracking-wider">TIMELINE AVAILABLE ONCE VIDEO METADATA LOADS</p>;
  const pos = (t: number) => `${Math.min(100, Math.max(0, (t / duration) * 100))}%`;
  const color = { person: 'bg-ice', vehicle: 'bg-cool', object: 'bg-slate-500' } as const;
  return (
    <div>
      <div className="relative h-12 bg-bg2 border border-white/[0.07] rounded cursor-pointer"
        onClick={(e) => { const r = e.currentTarget.getBoundingClientRect(); onSeek(((e.clientX - r.left) / r.width) * duration); }}>
        {motion.map((m) => <div key={m.id} className="absolute top-0 bottom-0 bg-ice/15 border-x border-ice/30" style={{ left: pos(m.start), width: `max(2px, calc(${pos(m.end)} - ${pos(m.start)}))` }} title={`MOTION ${fmtClock(m.start)}–${fmtClock(m.end)}`} />)}
        {detections.map((d) => (
          <button key={d.id} title={`${d.label.toUpperCase()} ${fmtClock(d.timestamp)}`} aria-label={`${d.label} at ${fmtClock(d.timestamp)}`}
            onClick={(e) => { e.stopPropagation(); onSeek(d.timestamp); onPick?.(d); }}
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-3 w-3 rotate-45 ${color[d.category]} hover:scale-150 transition-transform`} style={{ left: pos(d.timestamp) }} />
        ))}
        <div className="absolute top-0 bottom-0 w-px bg-amber" style={{ left: pos(current) }} />
      </div>
      <div className="mt-1 flex justify-between text-[10px] font-mono text-slate-500"><span>{fmtClock(0)}</span><span>{fmtClock(duration)}</span></div>
      <div className="mt-1 flex gap-4 text-[10px] font-mono text-slate-500 tracking-wider">
        <span><i className="inline-block h-2 w-2 rotate-45 bg-ice mr-1" />PERSON</span><span><i className="inline-block h-2 w-2 rotate-45 bg-cool mr-1" />VEHICLE</span>
        <span><i className="inline-block h-2 w-3 bg-ice/25 mr-1" />MOTION</span>
      </div>
    </div>
  );
}
