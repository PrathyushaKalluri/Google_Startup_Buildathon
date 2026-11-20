import { useEffect, useState } from 'react';
import { ArrowRight, Check, FileText, Pencil, Receipt, ShieldCheck, Wrench, CalendarClock, PackageOpen, NotebookPen, RefreshCw } from 'lucide-react';
import { useStore } from '../store';
import type { Asset, Fact, HistoryEvent } from '../types';
import { daysBetween, dueText, fmtDate, fmtShort, rupees } from '../logic/dates';
import { nextDue, openCasesFor } from '../logic/derive';
import { confirmFact } from '../logic/workflow';
import { ApplianceArt } from './Doodles';
import { ConfidenceBadge, Drawer, StateBadge, Tabs } from './ui';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'warranty', label: 'Purchase & warranty' },
  { id: 'history', label: 'Service history' },
  { id: 'docs', label: 'Documents' },
  { id: 'providers', label: 'Providers' },
  { id: 'cases', label: 'Open cases' },
  { id: 'triggers', label: 'Upcoming' },
] as const;
type TabId = (typeof TABS)[number]['id'];

const HISTORY_ICON: Record<HistoryEvent['kind'], JSX.Element> = {
  purchase: <PackageOpen className="h-4 w-4" />,
  install: <Wrench className="h-4 w-4" />,
  service: <Wrench className="h-4 w-4" />,
  repair: <Wrench className="h-4 w-4" />,
  note: <NotebookPen className="h-4 w-4" />,
  renewal: <RefreshCw className="h-4 w-4" />,
};

export function FactRow({ asset, f }: { asset: Asset; f: Fact }) {
  const { act, openSource } = useStore();
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(f.value);
  useEffect(() => setVal(f.value), [f.value]);
  const uncertain = f.confidence === 'needs_confirmation' || f.confidence === 'extracted';
  return (
    <div className={`rounded-2xl border p-3 ${f.confidence === 'needs_confirmation' ? 'border-mirchi/50 bg-mirchi-soft/30' : 'border-sand-deep/60 bg-white/80'}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="label !text-[10px]">{f.label}</div>
          {editing ? (
            <input className="input mt-1" value={val} onChange={(e) => setVal(e.target.value)} aria-label={`Correct ${f.label}`} autoFocus />
          ) : (
            <div className="mt-0.5 font-bold">{f.value}</div>
          )}
        </div>
        <ConfidenceBadge c={f.confidence} />
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        {f.docId ? (
          <button onClick={() => openSource(f.docId!, f.label)} className="inline-flex items-center gap-1 text-xs font-bold text-peacock hover:underline">
            <FileText className="h-3.5 w-3.5" /> {f.sourceLabel}
          </button>
        ) : (
          <span className="text-xs text-ink-soft">{f.sourceLabel}</span>
        )}
        {uncertain && (
          <div className="flex gap-1.5">
            {editing ? (
              <button className="btn-teal !min-h-[30px] !px-3 !py-1 !text-xs" onClick={() => { act((s) => confirmFact(s, asset.id, f.id, val.trim() || f.value)); setEditing(false); }}>
                <Check className="h-3.5 w-3.5" /> Save
              </button>
            ) : (
              <>
                <button className="btn-ghost !min-h-[30px] !px-3 !py-1 !text-xs" onClick={() => setEditing(true)}>
                  <Pencil className="h-3.5 w-3.5" /> Correct
                </button>
                <button className="btn-teal !min-h-[30px] !px-3 !py-1 !text-xs" onClick={() => act((s) => confirmFact(s, asset.id, f.id, f.value))}>
                  <Check className="h-3.5 w-3.5" /> Looks right
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function AssetDrawer() {
  const { assetDrawer, openAsset, state, openSource, openProvider, go } = useStore();
  const [tab, setTab] = useState<TabId>('overview');
  useEffect(() => setTab((assetDrawer?.tab as TabId) || 'overview'), [assetDrawer?.id, assetDrawer?.tab]);
  const a = state.assets.find((x) => x.id === assetDrawer?.id);
  if (!a) return null;
  const cases = openCasesFor(state, a.id);
  const docs = state.docs.filter((d) => d.assetId === a.id).sort((x, y) => y.date.localeCompare(x.date));
  const providers = state.providers.filter((p) => a.providerIds.includes(p.id));
  const history = [...a.history].sort((x, y) => y.date.localeCompare(x.date));
  const triggers: { title: string; date: string; note: string }[] = [];
  if (a.rule) triggers.push({ title: a.rule.label, date: nextDue(a.rule), note: `Every ${a.rule.intervalMonths} months · ${state.providers.find((p) => p.id === a.rule!.providerId)?.name} · up to ${rupees(a.rule.maxCost)} pre-approved` });
  if (a.amc) triggers.push({ title: 'AMC renewal', date: a.amc.end, note: `${rupees(a.amc.cost)}/year · renewal prepared 30 days ahead` });
  if (a.warrantyEnd && daysBetween(state.clock, a.warrantyEnd) > 0) triggers.push({ title: 'Warranty ends', date: a.warrantyEnd, note: a.warrantyNote });
  if (a.partWarrantyEnd && daysBetween(state.clock, a.partWarrantyEnd) > 0) triggers.push({ title: 'Repair part warranty ends', date: a.partWarrantyEnd, note: 'Report any repeat fault before this date' });
  triggers.sort((x, y) => x.date.localeCompare(y.date));

  return (
    <Drawer
      open
      wide
      onClose={() => openAsset(null)}
      title={
        <div className="flex items-center gap-3">
          <div className="grid h-16 w-16 flex-none place-items-center rounded-2xl bg-sand/70">
            <ApplianceArt type={a.type} mood={cases.some((c) => c.kind === 'repair') ? 'worried' : 'happy'} className="h-14 w-14" />
          </div>
          <div className="min-w-0">
            <div className="label">{a.room}</div>
            <div className="truncate font-display text-xl font-bold">{a.brand} {a.name}</div>
            <div className="text-sm text-ink-soft">{a.model}</div>
          </div>
        </div>
      }
    >
      <div className="sticky top-0 z-10 border-b border-sand-deep/50 bg-cream px-5 py-3">
        <Tabs value={tab} onChange={setTab} items={TABS.map((t) => ({ id: t.id, label: t.label, count: t.id === 'cases' ? cases.length : t.id === 'docs' ? docs.length : undefined }))} />
      </div>
      <div className="space-y-3 p-5">
        {tab === 'overview' && (
          <>
            {cases.map((c) => (
              <button key={c.id} onClick={() => go({ screen: 'work', caseId: c.id })} className="flex w-full items-center justify-between gap-3 rounded-2xl border-2 border-mirchi bg-white p-3 text-left">
                <div>
                  <div className="font-bold">{c.title}</div>
                  <StateBadge state={c.state} />
                </div>
                <ArrowRight className="h-5 w-5" />
              </button>
            ))}
            <p className="text-sm text-ink-soft">What Saathi knows, and where each fact came from. Tap a source to see it.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {a.facts.map((f) => (
                <FactRow key={f.id} asset={a} f={f} />
              ))}
            </div>
          </>
        )}
        {tab === 'warranty' && (
          <div className="space-y-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <Info icon={<Receipt className="h-4 w-4" />} label="Purchased" value={a.purchaseDate ? fmtDate(a.purchaseDate) : 'Not recorded'} />
              <Info icon={<ShieldCheck className="h-4 w-4" />} label="Longest cover till" value={a.warrantyEnd ? fmtDate(a.warrantyEnd) : 'None'} />
              {a.partWarrantyEnd && <Info icon={<Wrench className="h-4 w-4" />} label="Repair part warranty" value={`${daysBetween(state.clock, a.partWarrantyEnd) < 0 ? 'Ended' : 'Till'} ${fmtDate(a.partWarrantyEnd)}`} />}
              {a.amc && <Info icon={<RefreshCw className="h-4 w-4" />} label="AMC" value={`${fmtShort(a.amc.start)} – ${fmtDate(a.amc.end)} · ${rupees(a.amc.cost)}`} />}
            </div>
            <p className="rounded-2xl bg-haldi-soft/60 p-3 text-sm">{a.warrantyNote}</p>
            {a.facts.filter((f) => /warranty|amc|purchase/i.test(f.label)).map((f) => (
              <FactRow key={f.id} asset={a} f={f} />
            ))}
          </div>
        )}
        {tab === 'history' && (
          <ol className="relative ml-3 border-l-2 border-dashed border-ink/20">
            {history.map((h) => (
              <li key={h.id} className="relative mb-4 pl-6">
                <span className="absolute -left-[13px] top-0.5 grid h-6 w-6 place-items-center rounded-full border-2 border-ink bg-cream">{HISTORY_ICON[h.kind]}</span>
                <div className="text-xs font-bold text-ink-soft">{fmtDate(h.date)}</div>
                <div className="font-bold">{h.title}</div>
                {h.detail && <div className="text-sm text-ink-soft">{h.detail}</div>}
                <div className="mt-1 flex flex-wrap gap-2 text-xs">
                  {h.providerId && (
                    <button onClick={() => openProvider(h.providerId!)} className="rounded-full bg-sand px-2 py-0.5 font-bold hover:bg-sand-deep">
                      {state.providers.find((p) => p.id === h.providerId)?.name}
                    </button>
                  )}
                  {h.amount != null && <span className="rounded-full bg-white px-2 py-0.5 font-bold">{rupees(h.amount)}</span>}
                  {h.docId && (
                    <button onClick={() => openSource(h.docId!)} className="inline-flex items-center gap-1 font-bold text-peacock hover:underline">
                      <FileText className="h-3.5 w-3.5" /> Receipt
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
        {tab === 'docs' && (
          <div className="grid gap-2 sm:grid-cols-2">
            {docs.map((d) => (
              <button key={d.id} onClick={() => openSource(d.id)} className="flex items-start gap-3 rounded-2xl border border-sand-deep/70 bg-white p-3 text-left hover:border-ink/40">
                <span className="grid h-10 w-10 flex-none place-items-center rounded-xl bg-haldi-soft"><FileText className="h-5 w-5" /></span>
                <span className="min-w-0">
                  <span className="block font-bold leading-snug">{d.title}</span>
                  <span className="block text-xs text-ink-soft">{d.issuer} · {fmtDate(d.date)}</span>
                  <span className="mt-1 block text-[11px] font-bold uppercase tracking-wider text-ink-soft">{d.addedBy === 'resident' ? 'Added by you' : 'Filed by Saathi'}</span>
                </span>
              </button>
            ))}
          </div>
        )}
        {tab === 'providers' && (
          <div className="space-y-2">
            {providers.map((p) => (
              <button key={p.id} onClick={() => openProvider(p.id)} className="flex w-full items-center justify-between gap-3 rounded-2xl border border-sand-deep/70 bg-white p-3 text-left hover:border-ink/40">
                <div>
                  <div className="font-bold">{p.name}</div>
                  <div className="text-sm text-ink-soft">{p.category}{p.contactPerson ? ` · ${p.contactPerson}` : ''}</div>
                </div>
                <div className="flex gap-1">
                  {p.preferred && <span className="rounded-full bg-peacock px-2 py-0.5 text-[11px] font-bold text-white">Preferred</span>}
                  {p.backup && <span className="rounded-full bg-haldi px-2 py-0.5 text-[11px] font-bold">Backup</span>}
                </div>
              </button>
            ))}
          </div>
        )}
        {tab === 'cases' && (cases.length ? cases.map((c) => (
          <button key={c.id} onClick={() => go({ screen: 'work', caseId: c.id })} className="flex w-full items-center justify-between rounded-2xl border border-sand-deep/70 bg-white p-3 text-left">
            <div>
              <div className="font-bold">{c.title}</div>
              <div className="mt-1"><StateBadge state={c.state} /></div>
            </div>
            <ArrowRight className="h-5 w-5" />
          </button>
        )) : <p className="rounded-2xl bg-white/70 p-4 text-sm text-ink-soft">No open work on this one. Saathi will open a case when a rule triggers or you report a problem.</p>)}
        {tab === 'triggers' && (
          <div className="space-y-2">
            {triggers.length === 0 && <p className="rounded-2xl bg-white/70 p-4 text-sm text-ink-soft">No dates to watch for this item yet.</p>}
            {triggers.map((t) => {
              const days = daysBetween(state.clock, t.date);
              return (
                <div key={t.title} className="flex items-start gap-3 rounded-2xl border border-sand-deep/70 bg-white p-3">
                  <CalendarClock className="mt-0.5 h-5 w-5 text-peacock" />
                  <div className="flex-1">
                    <div className="flex flex-wrap justify-between gap-2">
                      <span className="font-bold">{t.title}</span>
                      <span className={`text-sm font-bold ${days < 0 ? 'text-mirchi-deep' : days <= 7 ? 'text-mirchi' : 'text-peacock'}`}>{dueText(days)}</span>
                    </div>
                    <div className="text-sm text-ink-soft">{fmtDate(t.date)} · {t.note}</div>
                  </div>
                </div>
              );
            })}
            {a.rule && (
              <button onClick={() => go({ screen: 'calendar' })} className="btn-ghost mt-2">Edit the maintenance rule <ArrowRight className="h-4 w-4" /></button>
            )}
          </div>
        )}
      </div>
    </Drawer>
  );
}

function Info({ icon, label, value }: { icon: JSX.Element; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-sand-deep/60 bg-white p-3">
      <div className="label flex items-center gap-1.5 !text-[10px]">{icon}{label}</div>
      <div className="mt-1 font-bold">{value}</div>
    </div>
  );
}
