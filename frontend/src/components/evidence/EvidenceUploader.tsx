import { useRef, useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { uploadEvidence } from '../../api/evidence';
import { useToast } from '../../context/ToastContext';
import { evidenceLabel, fmtBytes, fmtDate } from '../../lib/format';
import type { Evidence } from '../../types';
import { ErrorState, KV, LoadingState } from '../common/ui';

const OK = ['mp4', 'mkv', 'avi', 'mov', 'dav', 'ifv', 'h264', '264', 'h265', 'hevc'];

export default function EvidenceUploader({ caseId, onDone }: { caseId: string; onDone: () => void }) {
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState<Evidence | null>(null);

  const start = async (file?: File) => {
    if (!file) return;
    if (!OK.includes(file.name.split('.').pop()?.toLowerCase() ?? '')) { setError(new Error('Unsupported format. Use MP4, MKV, AVI, MOV, DAV, IFV or raw H.264/H.265.')); return; }
    setError(null); setDone(null); setProgress(0);
    try {
      const ev = await uploadEvidence(caseId, file, setProgress);
      setDone(ev); toast('success', 'Evidence uploaded'); onDone();
    } catch (e) { setError(e); toast('critical', 'Acquisition failed'); }
    finally { setProgress(null); }
  };

  return (
    <div>
      {done ? (
        <div>
          <p className="font-mono text-sm tracking-[0.18em] text-ok">ACQUISITION COMPLETE</p>
          <div className="mt-4">
            <KV k="Evidence ID" v={done.id || 'NO DATA AVAILABLE'} mono /><KV k="File size" v={fmtBytes(done.file_size)} mono />
            <KV k="Created at" v={fmtDate(done.created_at)} mono /><KV k="Camera" v={done.camera_id ?? 'NO DATA AVAILABLE'} mono />
          </div>
          {['SHA-256', 'MD5'].map((n) => (
            <div key={n} className="mt-4">
              <p className="panel-title">{n}</p>
              <p className="mono text-sm break-all mt-1 text-ice">{(n === 'MD5' ? done.md5 : done.sha256) ?? 'NO DATA AVAILABLE'}</p>
            </div>
          ))}
          <div className="mt-4"><p className="panel-title">METADATA</p><pre className="mono text-[10px] text-slate-400 mt-1 max-h-40 overflow-auto whitespace-pre-wrap">{done.metadata ? JSON.stringify(done.metadata, null, 2) : 'NO DATA AVAILABLE'}</pre></div>
          <button className="btn-ghost mt-5" onClick={() => setDone(null)}>ACQUIRE ANOTHER</button>
        </div>
      ) : progress !== null ? (
        <LoadingState label={progress >= 1 ? 'HASHING EVIDENCE…' : `UPLOADING ${Math.round(progress * 100)}%`} progress={progress >= 1 ? undefined : progress} compact />
      ) : (
        <div role="button" tabIndex={0} onClick={() => input.current?.click()} onKeyDown={(e) => e.key === 'Enter' && input.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); void start(e.dataTransfer.files[0]); }}
          className={`cursor-pointer border border-dashed rounded-md py-12 text-center transition-colors ${drag ? 'border-ice bg-ice/10' : 'border-white/20 hover:border-ice/50'}`}>
          <UploadCloud className="mx-auto text-ice-dim" size={28} />
          <p className="mt-3 text-sm">Drop a surveillance recording here, or click to browse</p>
          <p className="mt-1 text-[11px] font-mono text-slate-500 tracking-wider">MP4 · MKV · AVI · MOV · DAV · IFV · H264 · H265</p>
          <input ref={input} type="file" accept=".mp4,.mkv,.avi,.mov,.dav,.ifv,.h264,.264,.h265,.hevc,video/*" hidden onChange={(e) => void start(e.target.files?.[0])} />
        </div>
      )}
      {error !== null && <div className="mt-4"><ErrorState error={error} title="ACQUISITION FAILED" /></div>}
    </div>
  );
}
