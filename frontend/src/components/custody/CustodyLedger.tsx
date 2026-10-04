import { evidenceLabel, fmtDate } from '../../lib/format';
import type { ChainOfCustodyEvent } from '../../types';

export default function CustodyLedger({ events }: { events: ChainOfCustodyEvent[] }) {
  return (
    <ol className="relative border-l border-ice/30 ml-2 space-y-6">
      {events.map((e) => (
        <li key={e.id} className="pl-6 relative">
          <span className="absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full bg-ice" />
          <p className="font-mono text-xs tracking-[0.14em] text-ice">{e.action.toUpperCase().replace(/_/g, ' ')}</p>
          {e.description && <p className="text-sm mt-1">{e.description}</p>}
          <p className="mt-1 font-mono text-[11px] text-slate-500">
            {e.actor} · {fmtDate(e.timestamp)}{e.evidence_id ? ` · ${evidenceLabel(e.evidence_id)}` : ''}
          </p>
        </li>
      ))}
    </ol>
  );
}
