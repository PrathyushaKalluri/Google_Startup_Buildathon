import { ArrowRight, CalendarCheck, Phone } from 'lucide-react';
import { useStore } from '../store';
import type { Provider } from '../types';
import { fmtDate, fmtDateTime, relTime } from '../logic/dates';
import { isOpen } from '../logic/derive';
import { setProviderFlags } from '../logic/workflow';
import { Drawer, StateBadge, Toggle } from './ui';

export function reliability(p: Provider) {
  const kept = p.log.filter((l) => l.outcome === 'kept').length;
  const missed = p.log.filter((l) => l.outcome === 'missed').length;
  const silent = p.log.filter((l) => l.outcome === 'no_response').length;
  return { kept, missed, silent };
}

const OUTCOME: Record<string, string> = {
  kept: 'bg-leaf-soft text-leaf-deep',
  missed: 'bg-mirchi-soft text-mirchi-deep',
  responded: 'bg-peacock-soft text-peacock-deep',
  no_response: 'bg-sand text-ink',
  quoted: 'bg-haldi-soft text-ink',
};
const OUTCOME_TEXT: Record<string, string> = { kept: 'Kept', missed: 'Missed', responded: 'Responded', no_response: 'No reply', quoted: 'Quoted' };

export function ProviderDrawer() {
  const { providerDrawer, openProvider, state, act, openAsset, go } = useStore();
  const p = state.providers.find((x) => x.id === providerDrawer);
  if (!p) return null;
  const r = reliability(p);
  const assets = state.assets.filter((a) => p.assetIds.includes(a.id));
  const related = state.cases.filter((c) => isOpen(c) && (c.providerId === p.id || c.originalProviderId === p.id || c.alternative?.providerId === p.id));
  const commitments = state.cases.filter((c) => isOpen(c) && c.appointment?.providerId === p.id);
  const last = [...p.log].sort((a, b) => b.date.localeCompare(a.date))[0];

  return (
    <Drawer
      open
      onClose={() => openProvider(null)}
      title={
        <div>
          <div className="label">{p.category}</div>
          <div className="font-display text-xl font-bold">{p.name}</div>
          {p.contactPerson && <div className="text-sm text-ink-soft">{p.contactPerson}</div>}
        </div>
      }
    >
      <div className="space-y-5 p-5">
        <div className="flex flex-wrap gap-2">
          {p.preferred && <span className="sticker bg-peacock text-white">Preferred</span>}
          {p.backup && <span className="sticker bg-haldi">Authorised backup</span>}
          {!p.preferred && !p.backup && <span className="sticker bg-white">Saved contact</span>}
        </div>

        <div className="rounded-2xl border border-sand-deep/70 bg-white p-4">
          <div className="flex items-center gap-2 font-bold">
            <Phone className="h-4 w-4" /> {p.phone}
            <span className="rounded border border-dashed border-ink/40 px-1.5 text-[10px] font-bold uppercase text-ink-soft">Demo number</span>
          </div>
          <div className="mt-1 text-sm text-ink-soft">Reached via {p.channel}. Saathi uses channels people already answer, since most providers have no API.</div>
          {p.typicalCost && <div className="mt-2 text-sm"><span className="text-ink-soft">Typical cost:</span> <b>{p.typicalCost}</b></div>}
          {last && <div className="mt-1 text-sm"><span className="text-ink-soft">Last interaction:</span> <b>{relTime(last.date, state.clock)}</b>, {last.text.toLowerCase()}</div>}
        </div>

        <div>
          <div className="label mb-2">Track record, from this household's history only</div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-2xl bg-leaf-soft p-3"><div className="font-display text-2xl font-bold text-leaf-deep">{r.kept}</div><div className="text-xs font-bold">Kept</div></div>
            <div className="rounded-2xl bg-mirchi-soft p-3"><div className="font-display text-2xl font-bold text-mirchi-deep">{r.missed}</div><div className="text-xs font-bold">Missed</div></div>
            <div className="rounded-2xl bg-sand p-3"><div className="font-display text-2xl font-bold">{r.silent}</div><div className="text-xs font-bold">No reply</div></div>
          </div>
          <p className="mt-2 text-xs text-ink-soft">No star ratings. Only what happened with this home.</p>
        </div>

        <div className="space-y-3 rounded-2xl border border-sand-deep/70 bg-white p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="font-bold">Preferred provider</div>
              <div className="text-sm text-ink-soft">Saathi goes to them first.</div>
            </div>
            <Toggle checked={p.preferred} onChange={(v) => act((s) => setProviderFlags(s, p.id, { preferred: v }))} label="Preferred provider" />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="font-bold">Authorised backup</div>
              <div className="text-sm text-ink-soft">Saathi may ask them for quotes when the first choice fails.</div>
            </div>
            <Toggle checked={p.backup} onChange={(v) => act((s) => setProviderFlags(s, p.id, { backup: v }))} label="Authorised backup" />
          </div>
        </div>

        {commitments.length > 0 && (
          <div>
            <div className="label mb-2">Current commitments</div>
            {commitments.map((c) => (
              <div key={c.id} className="flex items-center gap-2 rounded-2xl bg-peacock-soft p-3 text-sm">
                <CalendarCheck className="h-4 w-4 text-peacock" />
                <b>{fmtDateTime(c.appointment!.start)}</b> · {c.title}
              </div>
            ))}
          </div>
        )}

        {related.length > 0 && (
          <div>
            <div className="label mb-2">Related active cases</div>
            {related.map((c) => (
              <button key={c.id} onClick={() => go({ screen: 'work', caseId: c.id })} className="mb-2 flex w-full items-center justify-between rounded-2xl border border-sand-deep/70 bg-white p-3 text-left">
                <div>
                  <div className="font-bold">{c.title}</div>
                  <StateBadge state={c.state} />
                </div>
                <ArrowRight className="h-5 w-5" />
              </button>
            ))}
          </div>
        )}

        {assets.length > 0 && (
          <div>
            <div className="label mb-2">Looks after</div>
            <div className="flex flex-wrap gap-2">
              {assets.map((a) => (
                <button key={a.id} onClick={() => openAsset(a.id)} className="rounded-full bg-sand px-3 py-1 text-sm font-bold hover:bg-sand-deep">{a.brand} {a.name}</button>
              ))}
            </div>
          </div>
        )}

        <div>
          <div className="label mb-2">Interaction log</div>
          <ol className="space-y-2">
            {[...p.log].sort((a, b) => b.date.localeCompare(a.date)).map((l) => (
              <li key={l.id} className="flex items-start gap-3 text-sm">
                <span className={`mt-0.5 w-20 flex-none rounded-full px-2 py-0.5 text-center text-[11px] font-bold ${OUTCOME[l.outcome]}`}>{OUTCOME_TEXT[l.outcome]}</span>
                <span className="flex-1">{l.text}</span>
                <span className="flex-none text-xs text-ink-soft">{fmtDate(l.date)}</span>
              </li>
            ))}
            {p.log.length === 0 && <li className="text-sm text-ink-soft">No interactions yet.</li>}
          </ol>
        </div>
      </div>
    </Drawer>
  );
}
