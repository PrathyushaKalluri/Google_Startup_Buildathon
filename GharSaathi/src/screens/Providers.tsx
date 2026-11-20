import { useState } from 'react';
import { ArrowRight, Phone, Search } from 'lucide-react';
import { useStore } from '../store';
import type { Provider } from '../types';
import { relTime } from '../logic/dates';
import { isOpen } from '../logic/derive';
import { reliability } from '../components/ProviderDrawer';
import { SectionHead, Tabs } from '../components/ui';

type Filter = 'all' | 'brand' | 'individual' | 'society' | 'backup';

const KIND_TINT: Record<Provider['kind'], string> = {
  brand_centre: 'bg-peacock-soft',
  individual: 'bg-haldi-soft',
  society: 'bg-leaf-soft',
};

export function Providers() {
  const { state, openProvider } = useStore();
  const [filter, setFilter] = useState<Filter>('all');
  const [q, setQ] = useState('');
  const match = (p: Provider, f: Filter) =>
    f === 'all' ? true : f === 'brand' ? p.kind === 'brand_centre' : f === 'individual' ? p.kind === 'individual' : f === 'society' ? p.kind === 'society' : p.backup;
  const needle = q.trim().toLowerCase();
  const list = state.providers.filter((p) => match(p, filter) && (!needle || `${p.name} ${p.category} ${p.contactPerson ?? ''}`.toLowerCase().includes(needle)));

  return (
    <div>
      <SectionHead kicker="People & Providers" title={<>The people who keep this home running<span className="text-mirchi">.</span></>} />
      <p className="-mt-2 mb-5 max-w-2xl text-ink-soft">Every name here comes from a real interaction in this home's history: who came on time, who didn't, and what they charged. There are no star ratings from strangers.</p>
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center">
        <label className="relative md:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" />
          <input className="input !rounded-full !pl-9" placeholder="Search plumber, Havells…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search providers" />
        </label>
        <Tabs
          value={filter}
          onChange={setFilter}
          items={[
            { id: 'all', label: 'All', count: state.providers.length },
            { id: 'brand', label: 'Service centres', count: state.providers.filter((p) => match(p, 'brand')).length },
            { id: 'individual', label: 'Technicians', count: state.providers.filter((p) => match(p, 'individual')).length },
            { id: 'society', label: 'Apartment', count: state.providers.filter((p) => match(p, 'society')).length },
            { id: 'backup', label: 'Authorised backups', count: state.providers.filter((p) => match(p, 'backup')).length },
          ]}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {list.map((p) => {
          const r = reliability(p);
          const last = [...p.log].sort((a, b) => b.date.localeCompare(a.date))[0];
          const active = state.cases.filter((c) => isOpen(c) && (c.providerId === p.id || c.alternative?.providerId === p.id)).length;
          const assets = state.assets.filter((a) => p.assetIds.includes(a.id));
          return (
            <button key={p.id} onClick={() => openProvider(p.id)} className="group flex flex-col rounded-[24px] border-2 border-ink/15 bg-white text-left transition hover:-translate-y-0.5 hover:border-ink hover:shadow-pop">
              <div className={`flex items-start justify-between gap-2 rounded-t-[22px] p-4 ${KIND_TINT[p.kind]}`}>
                <div className="min-w-0">
                  <div className="label !text-[10px]">{p.category}</div>
                  <div className="font-display text-lg font-bold leading-tight">{p.name}</div>
                  {p.contactPerson && <div className="text-sm text-ink-soft">{p.contactPerson}</div>}
                </div>
                <span className="grid h-11 w-11 flex-none place-items-center rounded-full border-2 border-ink bg-cream font-display text-lg font-bold">{p.name[0]}</span>
              </div>
              <div className="flex flex-1 flex-col gap-2 p-4 text-sm">
                <div className="flex flex-wrap gap-1.5">
                  {p.preferred && <span className="rounded-full bg-peacock px-2 py-0.5 text-[11px] font-bold text-white">Preferred</span>}
                  {p.backup && <span className="rounded-full bg-haldi px-2 py-0.5 text-[11px] font-bold">Authorised backup</span>}
                  {r.kept > 0 && <span className="rounded-full bg-leaf-soft px-2 py-0.5 text-[11px] font-bold text-leaf-deep">Previously used</span>}
                  {r.missed > 0 && <span className="rounded-full bg-mirchi-soft px-2 py-0.5 text-[11px] font-bold text-mirchi-deep">Missed {r.missed} visit{r.missed === 1 ? '' : 's'}</span>}
                  {active > 0 && <span className="rounded-full bg-ink px-2 py-0.5 text-[11px] font-bold text-cream">{active} active case</span>}
                </div>
                <div className="flex items-center gap-1.5 text-ink-soft"><Phone className="h-3.5 w-3.5" /> {p.phone} <span className="text-[10px] font-bold uppercase">(demo)</span></div>
                {p.typicalCost && <div><span className="text-ink-soft">Typical:</span> <b>{p.typicalCost}</b></div>}
                {last && <div className="text-ink-soft">Last: {relTime(last.date, state.clock)}, {last.text.toLowerCase()}</div>}
                {assets.length > 0 && <div className="text-ink-soft">For: {assets.map((a) => `${a.brand} ${a.name}`).join(', ')}</div>}
                <div className="mt-auto flex items-center gap-1 pt-1 text-xs font-bold text-peacock opacity-70 group-hover:opacity-100">Open profile <ArrowRight className="h-3.5 w-3.5" /></div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
