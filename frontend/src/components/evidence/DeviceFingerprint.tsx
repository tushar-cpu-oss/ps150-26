import type { DeviceFingerprint as DF } from '../../types';
import { KV, Panel } from '../common/ui';

export default function DeviceFingerprint({ device }: { device?: DF }) {
  return (
    <Panel title="DEVICE FINGERPRINT">
      {device?.known ? (
        <>
          <KV k="Vendor" v={device.vendor} /><KV k="Model" v={device.model ?? '—'} />
          <KV k="Identification method" v={device.method ?? '—'} /><KV k="Confidence" v={device.confidence ?? "NO DATA AVAILABLE"} mono />
        </>
      ) : (
        <div>
          <p className="panel-title">VENDOR</p>
          <p className="mt-1 font-mono text-lg">UNKNOWN</p>
          <p className="mt-1 text-xs text-slate-500 font-mono tracking-wider">INSUFFICIENT EVIDENCE</p>
        </div>
      )}
    </Panel>
  );
}
