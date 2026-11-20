import { useMemo, useState } from 'react';
import { Plus, Search, ShieldCheck, Wrench, CalendarClock, AlertTriangle } from 'lucide-react';
import { useStore } from '../store';
import type { Asset, AssetType } from '../types';
import { daysBetween, dueText, fmtShort } from '../logic/dates';
import { nextDue, openCasesFor } from '../logic/derive';
import { ApplianceArt, BalconyDoodle } from '../components/Doodles';
import { SectionHead, Tabs } from '../components/ui';

type Filter = 'all' | 'appliances' | 'warranty' | 'due' | 'issues';

const TINT: Record<AssetType, string> = {
  ac: 'bg-peacock-soft',
  geyser: 'bg-mirchi-soft',
  ro: 'bg-[#DCEFF5]',
  washer: 'bg-haldi-soft',
  fridge: 'bg-leaf-soft',
  plumbing: 'bg-sand',
  lighting: 'bg-haldi-soft',
};

export function Memory() {
  const { state, openAsset, setPanel } = useStore();
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState<Filter>('all');

  const info = (a: Asset) => {
    const open = openCasesFor(state, a.id);
    const due = a.rule ? daysBetween(state.clock, nextDue(a.rule)) : undefined;
    const covered = (a.warrantyEnd && daysBetween(state.clock, a.warrantyEnd) >= 0) || (a.amc && daysBetween(state.clock, a.amc.end) >= 0);
    return { open, due, covered };
  };

  const list = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return state.assets.filter((a) => {
      const i = info(a);
      if (needle && !`${a.brand} ${a.name} ${a.room} ${a.model}`.toLowerCase().includes(needle)) return false;
      if (filter === 'appliances') return a.category === 'appliance';
      if (filter === 'warranty') return !!i.covered;
      if (filter === 'due') return i.due != null && i.due <= 30;
      if (filter === 'issues') return i.open.length > 0;
      return true;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, q, filter]);

  const count = (f: Filter) => state.assets.filter((a) => {
    const i = info(a);
    if (f === 'appliances') return a.category === 'appliance';
    if (f === 'warranty') return !!i.covered;
    if (f === 'due') return i.due != null && i.due <= 30;
    if (f === 'issues') return i.open.length > 0;
    return true;
  }).length;

  return (
    <div>
      <SectionHead
        kicker="Ghar Ki Memory"
        title={<>Everything your home has told me<span className="text-mirchi">.</span></>}
        action={<button className="btn-primary" onClick={() => setPanel('memory')}><Plus className="h-4 w-4" /> Add something to memory</button>}
      />
      <p className="-mt-2 mb-5 max-w-2xl text-ink-soft">Built from invoices, warranty cards, receipts and messages. You never fill a form. Every fact keeps its source, and anything uncertain stays marked until someone confirms it.</p>

      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center">
        <label className="relative md:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" />
          <input className="input !rounded-full !pl-9" placeholder="Search geyser, kitchen, LG…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search assets" />
        </label>
        <Tabs
          value={filter}
          onChange={setFilter}
          items={[
            { id: 'all', label: 'All', count: count('all') },
            { id: 'appliances', label: 'Appliances', count: count('appliances') },
            { id: 'warranty', label: 'Warranty', count: count('warranty') },
            { id: 'due', label: 'Service due', count: count('due') },
            { id: 'issues', label: 'Open issues', count: count('issues') },
          ]}
        />
      </div>

      {list.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-3xl bg-white/60 p-10 text-center">
          <BalconyDoodle />
          <div className="font-display text-lg font-bold">Nothing matches that</div>
          <p className="text-sm text-ink-soft">Try another word, or clear the filter.</p>
          <button className="btn-ghost mt-1" onClick={() => { setQ(''); setFilter('all'); }}>Show everything</button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {list.map((a) => {
            const i = info(a);
            const repair = i.open.some((c) => c.kind === 'repair');
            const lastService = [...a.history].sort((x, y) => y.date.localeCompare(x.date)).find((h) => h.kind === 'service' || h.kind === 'repair');
            const wDays = a.warrantyEnd ? daysBetween(state.clock, a.warrantyEnd) : undefined;
            return (
              <button key={a.id} onClick={() => openAsset(a.id)} className="group overflow-hidden rounded-[26px] border-2 border-ink bg-white text-left transition hover:-translate-y-1 hover:shadow-pop">
                <div className={`relative flex h-36 items-center justify-center ${TINT[a.type]} bg-dots`}>
                  <ApplianceArt type={a.type} mood={repair ? 'worried' : 'happy'} className="h-28 w-28 transition group-hover:scale-105" />
                  <span className="absolute left-3 top-3 rounded-full bg-cream px-2.5 py-0.5 text-[11px] font-bold">{a.room}</span>
                  {i.open.length > 0 && <span className="stamp absolute right-3 top-3 bg-mirchi text-white"><AlertTriangle className="h-3 w-3" />{i.open.length} open</span>}
                </div>
                <div className="p-4">
                  <div className="label !text-[10px]">{a.category === 'appliance' ? 'Appliance' : 'Fixture'} · {a.brand}</div>
                  <div className="font-display text-xl font-bold leading-tight">{a.brand} {a.name}</div>
                  <div className="text-sm text-ink-soft">{a.model}</div>
                  <ul className="mt-3 space-y-1.5 text-sm">
                    <li className="flex items-center gap-2">
                      <ShieldCheck className={`h-4 w-4 ${i.covered ? 'text-peacock' : 'text-ink-soft'}`} />
                      {a.amc && daysBetween(state.clock, a.amc.end) >= 0 ? `AMC till ${fmtShort(a.amc.end)}` : wDays != null && wDays >= 0 ? `Warranty till ${fmtShort(a.warrantyEnd!)}` : 'Out of warranty'}
                    </li>
                    <li className="flex items-center gap-2"><Wrench className="h-4 w-4 text-ink-soft" />{lastService ? `Last work ${fmtShort(lastService.date)}` : 'No service yet'}</li>
                    {i.due != null && (
                      <li className={`flex items-center gap-2 font-bold ${i.due <= 7 ? 'text-mirchi-deep' : 'text-peacock-deep'}`}><CalendarClock className="h-4 w-4" />{a.rule!.label}: {dueText(i.due)}</li>
                    )}
                    {i.open.map((c) => (
                      <li key={c.id} className="flex items-center gap-2 font-bold text-mirchi-deep"><AlertTriangle className="h-4 w-4" />{c.title}</li>
                    ))}
                  </ul>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
