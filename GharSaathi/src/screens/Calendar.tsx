import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Play, Zap, ArrowRight } from 'lucide-react';
import { useStore } from '../store';
import type { Asset, MaintenanceRule, TimeWindow, Weekday } from '../types';
import { addDays, addMonths, daysBetween, dueText, fmtDate, fmtShort, fmtTime, rupees, sameDay, WINDOW_LABEL } from '../logic/dates';
import { isOpen, nextDue, pendingTriggers } from '../logic/derive';
import { runTrigger, updateRule } from '../logic/workflow';
import { ApplianceArt, Rangoli } from '../components/Doodles';
import { SectionHead, Tabs } from '../components/ui';

type Kind = 'service' | 'warranty' | 'amc' | 'visit' | 'followup' | 'done' | 'open';

interface Item {
  id: string;
  date: string;
  title: string;
  kind: Kind;
  link: { type: 'asset' | 'case'; id: string };
}

const KIND: Record<Kind, { label: string; cls: string; dot: string }> = {
  service: { label: 'Maintenance due', cls: 'bg-peacock-soft text-peacock-deep', dot: 'bg-peacock' },
  visit: { label: 'Technician visit', cls: 'bg-peacock text-white', dot: 'bg-peacock-deep' },
  warranty: { label: 'Warranty ends', cls: 'bg-haldi-soft text-ink', dot: 'bg-haldi' },
  amc: { label: 'AMC renewal', cls: 'bg-haldi text-ink', dot: 'bg-haldi-deep' },
  followup: { label: 'Follow-up deadline', cls: 'border border-dashed border-mirchi bg-white text-mirchi-deep', dot: 'bg-mirchi-soft border border-mirchi' },
  open: { label: 'Unresolved repair', cls: 'bg-mirchi text-white', dot: 'bg-mirchi' },
  done: { label: 'Completed', cls: 'bg-leaf-soft text-leaf-deep', dot: 'bg-leaf' },
};

function useItems(): Item[] {
  const { state } = useStore();
  return useMemo(() => {
    const out: Item[] = [];
    for (const a of state.assets) {
      const n = `${a.brand} ${a.name}`;
      if (a.rule) out.push({ id: `r-${a.id}`, date: nextDue(a.rule), title: `${n}: ${a.rule.label.toLowerCase()}`, kind: 'service', link: { type: 'asset', id: a.id } });
      if (a.warrantyEnd && a.category === 'appliance' && daysBetween(state.clock, a.warrantyEnd) >= -30)
        out.push({ id: `w-${a.id}`, date: a.warrantyEnd, title: `${n} warranty ends`, kind: 'warranty', link: { type: 'asset', id: a.id } });
      if (a.partWarrantyEnd && daysBetween(state.clock, a.partWarrantyEnd) >= 0)
        out.push({ id: `pw-${a.id}`, date: a.partWarrantyEnd, title: `${n} repair part warranty ends`, kind: 'warranty', link: { type: 'asset', id: a.id } });
      if (a.amc) out.push({ id: `amc-${a.id}`, date: a.amc.end, title: `${a.brand} AMC ends (${rupees(a.amc.cost)})`, kind: 'amc', link: { type: 'asset', id: a.id } });
      for (const h of a.history) if (h.kind === 'service' || h.kind === 'repair' || h.kind === 'renewal') out.push({ id: `h-${h.id}`, date: h.date, title: `${n}: ${h.title}`, kind: 'done', link: { type: 'asset', id: a.id } });
    }
    for (const c of state.cases) {
      if (!isOpen(c)) continue;
      if (c.appointment) out.push({ id: `v-${c.id}`, date: c.appointment.start, title: `${fmtTime(c.appointment.start)} ${state.providers.find((p) => p.id === c.appointment!.providerId)?.name} visit`, kind: 'visit', link: { type: 'case', id: c.id } });
      if (c.nextActionAt) out.push({ id: `f-${c.id}`, date: c.nextActionAt, title: `${fmtTime(c.nextActionAt)} follow-up: ${c.title}`, kind: 'followup', link: { type: 'case', id: c.id } });
      if (c.kind === 'repair') out.push({ id: `o-${c.id}`, date: state.clock, title: `${c.title} (day ${daysBetween(c.reportedAt, state.clock) + 1})`, kind: 'open', link: { type: 'case', id: c.id } });
    }
    return out.sort((x, y) => x.date.localeCompare(y.date));
  }, [state]);
}

export function Calendar() {
  const { state, act, go, openAsset } = useStore();
  const [view, setView] = useState<'month' | 'agenda'>('month');
  const [offset, setOffset] = useState(0);
  const items = useItems();
  const triggers = pendingTriggers(state);
  const open = (it: Item) => (it.link.type === 'case' ? go({ screen: 'work', caseId: it.link.id }) : openAsset(it.link.id, 'triggers'));

  const monthStart = useMemo(() => {
    const d = new Date(addMonths(state.clock, offset));
    d.setDate(1);
    d.setHours(12, 0, 0, 0);
    return d.toISOString();
  }, [state.clock, offset]);
  const grid = useMemo(() => {
    const first = new Date(monthStart);
    const lead = (first.getDay() + 6) % 7;
    const start = addDays(monthStart, -lead);
    return Array.from({ length: 42 }, (_, i) => addDays(start, i));
  }, [monthStart]);
  const month = new Date(monthStart).getMonth();
  const agenda = items.filter((i) => daysBetween(state.clock, i.date) >= -14 && daysBetween(state.clock, i.date) <= 120);

  return (
    <div className="space-y-8">
      <SectionHead kicker="Service Calendar" title={<>Work that starts before you remember it<span className="text-mirchi">.</span></>} />

      {/* Triggers */}
      <section className="relative overflow-hidden rounded-[28px] border-2 border-ink bg-ink p-5 text-cream sm:p-6">
        <Rangoli className="absolute -right-8 -top-8 h-36 w-36 opacity-25" />
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-xl">
            <div className="flex items-center gap-2 text-haldi"><Zap className="h-5 w-5" /><span className="text-xs font-black tracking-[0.18em]">TRIGGERS READY</span></div>
            <h2 className="mt-1 text-2xl font-bold">{triggers.length ? `${triggers.length} thing${triggers.length === 1 ? '' : 's'} Saathi would start now` : 'Nothing due right now'}</h2>
            <p className="mt-1 text-sm text-cream/75">In the real product these run on schedule. In the demo, nothing runs in the background. Press the button to let the next one fire.</p>
          </div>
          <button className="btn-primary" onClick={() => act((s) => runTrigger(s))} disabled={!triggers.length}>
            <Play className="h-4 w-4" /> Run next trigger
          </button>
        </div>
        {triggers.length > 0 && (
          <ol className="relative mt-4 grid gap-2 md:grid-cols-2">
            {triggers.map((t, i) => (
              <li key={t.id} className={`flex items-start gap-3 rounded-2xl p-3 ${i === 0 ? 'bg-haldi text-ink' : 'bg-cream/10'}`}>
                <span className={`grid h-7 w-7 flex-none place-items-center rounded-full text-xs font-black ${i === 0 ? 'bg-ink text-haldi' : 'bg-cream/20'}`}>{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <div className="font-bold leading-snug">{t.title}</div>
                  <div className={`text-xs ${i === 0 ? 'text-ink/70' : 'text-cream/70'}`}>{fmtDate(t.date)} · {t.detail}</div>
                </div>
                {i > 0 && <button className="text-xs font-bold underline" onClick={() => act((s) => runTrigger(s, t.id))}>Run</button>}
              </li>
            ))}
          </ol>
        )}
      </section>

      {/* Calendar */}
      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Tabs value={view} onChange={setView} items={[{ id: 'month', label: 'Month' }, { id: 'agenda', label: 'Agenda' }]} />
          {view === 'month' && (
            <div className="flex items-center gap-2">
              <button className="rounded-full border border-ink/20 bg-white p-2 hover:bg-sand" onClick={() => setOffset(offset - 1)} aria-label="Previous month"><ChevronLeft className="h-4 w-4" /></button>
              <div className="min-w-36 text-center font-display text-lg font-bold">{new Date(monthStart).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</div>
              <button className="rounded-full border border-ink/20 bg-white p-2 hover:bg-sand" onClick={() => setOffset(offset + 1)} aria-label="Next month"><ChevronRight className="h-4 w-4" /></button>
              {offset !== 0 && <button className="text-sm font-bold text-peacock" onClick={() => setOffset(0)}>Today</button>}
            </div>
          )}
        </div>
        <div className="mb-3 flex flex-wrap gap-3 text-xs">
          {(Object.keys(KIND) as Kind[]).map((k) => (
            <span key={k} className="inline-flex items-center gap-1.5"><span className={`h-2.5 w-2.5 rounded-full ${KIND[k].dot}`} />{KIND[k].label}</span>
          ))}
        </div>
        {view === 'month' ? (
          <div className="overflow-hidden rounded-[24px] border-2 border-ink bg-white">
            <div className="grid grid-cols-7 border-b-2 border-ink bg-haldi text-center text-xs font-black uppercase tracking-wider">
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => <div key={d} className="py-2">{d}</div>)}
            </div>
            <div className="grid grid-cols-7">
              {grid.map((day) => {
                const its = items.filter((i) => sameDay(i.date, day));
                const today = sameDay(day, state.clock);
                const inMonth = new Date(day).getMonth() === month;
                return (
                  <div key={day} className={`min-h-[76px] border-b border-r border-sand p-1 sm:min-h-[104px] sm:p-1.5 ${inMonth ? '' : 'bg-cream/60 text-ink-soft/50'} ${today ? 'bg-haldi-soft/50' : ''}`}>
                    <div className={`mb-1 grid h-6 w-6 place-items-center rounded-full text-xs font-bold ${today ? 'bg-ink text-cream' : ''}`}>{new Date(day).getDate()}</div>
                    <div className="space-y-0.5">
                      {its.slice(0, 3).map((it) => (
                        <button key={it.id} onClick={() => open(it)} title={it.title} className={`block w-full truncate rounded px-1 py-0.5 text-left text-[10px] font-bold leading-tight sm:text-[11px] ${KIND[it.kind].cls}`}>
                          <span className="hidden sm:inline">{it.title}</span>
                          <span className="sm:hidden">●</span>
                        </button>
                      ))}
                      {its.length > 3 && <div className="px-1 text-[10px] font-bold text-ink-soft">+{its.length - 3} more</div>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <ol className="space-y-2">
            {agenda.map((it) => {
              const d = daysBetween(state.clock, it.date);
              return (
                <li key={it.id}>
                  <button onClick={() => open(it)} className="flex w-full items-center gap-3 rounded-2xl border border-sand-deep/70 bg-white p-3 text-left hover:border-ink/40">
                    <div className="w-14 flex-none text-center">
                      <div className="font-display text-2xl font-black leading-none">{new Date(it.date).getDate()}</div>
                      <div className="text-[11px] font-bold uppercase">{new Date(it.date).toLocaleDateString('en-IN', { month: 'short' })}</div>
                    </div>
                    <span className={`h-10 w-1.5 flex-none rounded-full ${KIND[it.kind].dot}`} />
                    <div className="min-w-0 flex-1">
                      <div className="font-bold leading-snug">{it.title}</div>
                      <div className="text-xs text-ink-soft">{KIND[it.kind].label} · {d === 0 ? 'today' : d > 0 ? `in ${d} day${d === 1 ? '' : 's'}` : `${-d} day${d === -1 ? '' : 's'} ago`}</div>
                    </div>
                    <ArrowRight className="h-4 w-4 flex-none opacity-40" />
                  </button>
                </li>
              );
            })}
          </ol>
        )}
      </section>

      {/* Rules */}
      <section>
        <SectionHead kicker="Recurring maintenance rules" title="What should happen next?" />
        <div className="grid gap-4 lg:grid-cols-3">
          {state.assets.filter((a): a is Asset & { rule: MaintenanceRule } => !!a.rule).map((a) => <RuleCard key={a.id} a={a} />)}
        </div>
      </section>
    </div>
  );
}

const DAYS: Weekday[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function RuleCard({ a }: { a: Asset & { rule: MaintenanceRule } }) {
  const { state, act, openAsset } = useStore();
  const r = a.rule;
  const due = nextDue(r);
  const days = daysBetween(state.clock, due);
  const pros = state.providers.filter((p) => p.handles.includes(a.type));
  const pro = state.providers.find((p) => p.id === r.providerId);
  const set = (patch: Partial<MaintenanceRule>) => act((s) => updateRule(s, a.id, patch));
  const hasCase = state.cases.some((c) => c.assetId === a.id && c.kind === 'service' && isOpen(c));
  const auto = r.estCost <= r.maxCost;
  const triggerDay = addDays(due, -7);

  return (
    <div className="flex flex-col rounded-[24px] border-2 border-ink bg-white">
      <div className="flex items-center gap-3 border-b-2 border-dashed border-ink/15 p-4">
        <button onClick={() => openAsset(a.id)} className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-sand/70" aria-label={`Open ${a.brand} ${a.name}`}>
          <ApplianceArt type={a.type} className="h-12 w-12" />
        </button>
        <div className="min-w-0">
          <div className="font-display text-lg font-bold leading-tight">{a.brand} {a.name}</div>
          <div className="text-sm text-ink-soft">{r.label}</div>
        </div>
      </div>
      <div className="space-y-3 p-4 text-sm">
        <div className="flex flex-wrap items-center gap-1 font-bold">
          {a.brand} {a.type === 'ac' ? 'AC' : a.name} <span className="text-ink-soft">→</span> every
          <select className="input !w-auto !py-1" value={r.intervalMonths} onChange={(e) => set({ intervalMonths: Number(e.target.value) })} aria-label="Service interval in months">
            {[1, 2, 3, 4, 6, 9, 12].map((n) => <option key={n} value={n}>{n} month{n === 1 ? '' : 's'}</option>)}
          </select>
        </div>
        <label className="flex items-center justify-between gap-2">
          <span className="text-ink-soft">Channel</span>
          <select className="input !w-auto !py-1" value={r.providerId} onChange={(e) => set({ providerId: e.target.value })}>
            {pros.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
        <div>
          <span className="text-ink-soft">Preferred days</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {DAYS.map((d) => {
              const on = r.days.includes(d);
              return (
                <button key={d} onClick={() => set({ days: on ? r.days.filter((x) => x !== d) : [...r.days, d] })} className={`rounded-full border px-2 py-0.5 text-xs font-bold ${on ? 'border-ink bg-haldi' : 'border-sand-deep text-ink-soft'}`} aria-pressed={on}>{d}</button>
              );
            })}
          </div>
        </div>
        <label className="flex items-center justify-between gap-2">
          <span className="text-ink-soft">Time window</span>
          <select className="input !w-auto !py-1" value={r.window} onChange={(e) => set({ window: e.target.value as TimeWindow })}>
            {(Object.keys(WINDOW_LABEL) as TimeWindow[]).map((w) => <option key={w} value={w}>{WINDOW_LABEL[w]}</option>)}
          </select>
        </label>
        <label className="flex items-center justify-between gap-2">
          <span className="text-ink-soft">Pre-authorised up to</span>
          <span className="flex items-center gap-1 rounded-xl border border-sand-deep px-2">₹<input type="number" min={0} step={100} className="w-16 bg-transparent py-1 font-bold focus:outline-none" value={r.maxCost} onChange={(e) => set({ maxCost: Math.max(0, Number(e.target.value) || 0) })} aria-label="Maximum pre-authorised cost" /></span>
        </label>
      </div>
      <div className="mt-auto rounded-b-[22px] bg-cream p-4 text-sm">
        <div className="flex items-center justify-between gap-2">
          <span className="label">Next trigger</span>
          <span className={`font-bold ${days <= 7 ? 'text-mirchi-deep' : 'text-peacock-deep'}`}>{dueText(days)} · {fmtShort(due)}</span>
        </div>
        <p className="mt-2 leading-snug">
          {hasCase
            ? 'Already being arranged. See it in Kaam Chal Raha Hai.'
            : <>On <b>{fmtShort(days <= 7 ? state.clock : triggerDay)}</b>, Saathi asks <b>{pro?.contactPerson ?? pro?.name}</b> for a {r.days.join('/')} {r.window} slot. {r.maxCost === 0 && r.estCost === 0 ? <>It's covered by the AMC, so it <b>books without asking</b>.</> : auto ? <>Expected {rupees(r.estCost)} is within {rupees(r.maxCost)}, so it <b>books without asking</b>.</> : <>Expected {rupees(r.estCost)} is above {rupees(r.maxCost)}, so it <b>asks you first</b>.</>}</>}
        </p>
      </div>
    </div>
  );
}
