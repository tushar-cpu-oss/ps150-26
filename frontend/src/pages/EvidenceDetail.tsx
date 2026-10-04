import { useParams } from 'react-router-dom';
import { getDevice } from '../api/analysis';
import { getEvidence } from '../api/evidence';
import Shell from '../components/layout/AppShell';
import DeviceFingerprint from '../components/evidence/DeviceFingerprint';
import EvidenceIntegrity from '../components/evidence/EvidenceIntegrity';
import EvidenceWorkstation from '../components/video/EvidenceWorkstation';
import {
  ErrorState,
  KV,
  LoadingState,
  Panel,
} from '../components/common/ui';
import { useAsync } from '../hooks/useAsync';
import {
  evidenceLabel,
  fmtBytes,
  fmtClock,
  fmtDate,
  fmtRes,
} from '../lib/format';

export default function EvidenceDetail() {
  const { evidenceId = '' } = useParams();

  const q = useAsync(
    () => getEvidence(evidenceId),
    [evidenceId]
  );

  const e = q.data;

  const dev = useAsync(
    () =>
      e
        ? getDevice(e.case_id, evidenceId).catch(() => undefined)
        : Promise.resolve(undefined),
    [evidenceId, e?.case_id]
  );

  return (
    <Shell caseId={e?.case_id}>
      {q.loading && !e ? (
        <LoadingState label="OPENING EVIDENCE…" />
      ) : q.error || !e ? (
        <ErrorState error={q.error} onRetry={q.reload} />
      ) : (
        <div className="space-y-4">
          <div>
            <p className="font-mono text-xs text-ice">
              {evidenceLabel(e.id)}
            </p>
            <h2 className="text-lg font-semibold">{e.filename}</h2>
          </div>

          <EvidenceWorkstation evidence={e} />

          <div className="grid lg:grid-cols-3 gap-4">
            <Panel title="METADATA">
              <KV
                k="Type"
                v={(e.media_type ?? 'VIDEO').toUpperCase()}
                mono
              />
              <KV
                k="Resolution"
                v={fmtRes(e.width, e.height)}
                mono
              />
              <KV
                k="Frame rate"
                v={e.fps ? `${e.fps.toFixed(2)} FPS` : '—'}
                mono
              />
              <KV
                k="Duration"
                v={e.duration != null ? fmtClock(e.duration) : '—'}
                mono
              />
              <KV k="Codec" v={e.codec ?? '—'} mono />
              <KV
                k="Size"
                v={fmtBytes(e.file_size)}
                mono
              />
              <KV
                k="Acquired"
                v={fmtDate(e.acquired_at)}
                mono
              />
            </Panel>

            <EvidenceIntegrity
              evidence={e}
              onChange={q.reload}
            />

            <DeviceFingerprint
              device={dev.data ?? e.device}
            />
          </div>
        </div>
      )}
    </Shell>
  );
}