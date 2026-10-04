import { useRef, useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { ingestForensicImage } from '../../api/forensicImages';
import { useToast } from '../../context/ToastContext';
import { fmtBytes, fmtDate } from '../../lib/format';
import { ErrorState, KV, LoadingState } from '../common/ui';

export default function ForensicImageUploader({ caseId }: { caseId: string }) {
  const input = useRef<HTMLInputElement>(null);
  const toast = useToast();
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState<any>(null);
  const start = async (file?: File) => {
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!['dd', 'img', 'raw', 'e01', '001'].includes(ext)) { setError(new Error('Use a forensic image: DD, IMG, RAW, E01 or segmented E01 (.001).')); return; }
    setError(null); setProgress(0);
    try { setDone(await ingestForensicImage(caseId, file, setProgress)); toast('success', 'Forensic image ingested and hashed'); }
    catch (e) { setError(e); toast('critical', 'Forensic image ingestion failed'); }
    finally { setProgress(null); }
  };
  return <div>
    {done ? <div>
      <p className="font-mono text-sm tracking-[0.18em] text-ok">FORENSIC IMAGE PRESERVED</p>
      <KV k="Image ID" v={done.image_id} mono /><KV k="File" v={done.filename} /><KV k="Size" v={fmtBytes(done.size_bytes)} mono /><KV k="Type" v={done.image_type ?? 'UNKNOWN'} /><KV k="Parser" v={done.parser_status} /><KV k="Created" v={fmtDate(done.created_at)} mono />
      <p className="panel-title mt-4">SHA-256</p><p className="mono text-xs break-all text-ice mt-1">{done.sha256}</p>
      <p className="panel-title mt-4">MD5</p><p className="mono text-xs break-all text-ice mt-1">{done.md5}</p>
    </div> : progress !== null ? <LoadingState compact label={`INGESTING ${Math.round(progress * 100)}%`} progress={progress} /> :
      <div role="button" tabIndex={0} onClick={() => input.current?.click()} onKeyDown={(e) => e.key === 'Enter' && input.current?.click()} className="cursor-pointer border border-dashed rounded-md py-10 text-center border-white/20 hover:border-ice/50">
        <UploadCloud className="mx-auto text-ice-dim" size={28} /><p className="mt-3 text-sm">Drop a forensic image here, or click to browse</p><p className="mt-1 text-[11px] font-mono text-slate-500">DD · IMG · RAW · E01 · E01 SEGMENTS</p>
        <input ref={input} type="file" accept=".dd,.img,.raw,.e01,.001" hidden onChange={(e) => void start(e.target.files?.[0])} />
      </div>}
    {error !== null && <div className="mt-4"><ErrorState error={error} title="IMAGE INGESTION FAILED" /></div>}
  </div>;
}
