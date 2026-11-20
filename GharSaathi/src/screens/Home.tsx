import { ArrowRight, CalendarClock, Check, CircleDot, Wrench, PartyPopper } from 'lucide-react';
import { useStore } from '../store';
import { daysBetween, dueText, fmtDate, fmtDateTime, fmtShort, relTime, rupees, WINDOW_LABEL } from '../logic/dates';
import { honestStatus, isOpen, JOURNEY, journeyIndex, nextDue, stats } from '../logic/derive';
import { bookServiceNow } from '../logic/workflow';
import { ApplianceArt, HandArrow, Rangoli, SaathiHero, Sparkle, Squiggle } from '../components/Doodles';
import { LabelChip, StateBadge } from '../components/ui';
import { ApprovalCard } from '../components/Panels';

export function Home() {
  const { state, go, openAsset, setPanel, act } = useStore();
  const st = stats(state);
  const repair = state.cases.find((c) => c.kind === 'repair' && isOpen(c));
  const lastClosed = [...state.cases].filter((c) => c.kind === 'repair' && !isOpen(c)).sort((a, b) => (b.closedAt ?? '').localeCompare(a.closedAt ?? ''))[0];
  const ac = state.assets.find((a) => a.id === 'ac')!;
  const acCase = state.cases.find((c) => c.assetId === 'ac' && c.kind === 'service' && isOpen(c));
  const acDue = ac.rule ? nextDue(ac.rule) : undefined;
  const acDays = acDue ? daysBetween(state.clock, acDue) : 0;
  const acLast = [...ac.history].reverse().find((h) => h.kind === 'service');
  const acPro = state.providers.find((p) => p.id === ac.rule?.providerId);
  const sorted = state.activities.filter((a) => a.label === 'Handled automatically' || a.label === 'Completed and saved').slice(0, 4);
  const firstName = state.household.residents[0].split(' ')[0];

  return (
    <div className="space-y-10">
      {/* A. Hero */}
      <section className="relative overflow-hidden rounded-[32px] border-2 border-ink bg-haldi bg-tile">
        <Rangoli className="absolute -right-10 -top-10 h-40 w-40 opacity-30" />
        <div className="relative grid items-center gap-4 p-6 sm:p-8 md:grid-cols-[1.1fr_0.9fr]">
          <div>
            <span className="stamp bg-cream text-mirchi-deep">Namaste, {firstName}</span>
            <h1 className="mt-3 text-[40px] font-black leading-[0.95] tracking-tight sm:text-[56px]">
              Your ghar is in <span className="relative inline-block">good hands.<Squiggle className="absolute -bottom-2 left-0 h-4 w-full" color="#157A78" /></span>
            </h1>
            <p className="mt-4 max-w-md text-lg">While you get on with life, I'm keeping the home running.</p>
            <div className="mt-6 inline-block rounded-3xl border-2 border-ink bg-cream p-4 shadow-pop">
              <div className="flex items-center gap-2 text-xs font-black tracking-[0.18em]">
                <span className="pulse-live h-2.5 w-2.5 rounded-full bg-peacock" /> SAATHI IS ON IT
              </div>
              <ul className="mt-2 space-y-1 text-[15px]">
                <li className="flex items-center gap-2"><Check className="h-4 w-4 text-peacock" /><b>{st.handled}</b> task{st.handled === 1 ? '' : 's'} handled automatically this week</li>
                <li className="flex items-center gap-2"><Wrench className="h-4 w-4 text-mirchi" /><b>{st.chasing}</b> repair{st.chasing === 1 ? '' : 's'} being chased</li>
                <li className="flex items-center gap-2"><CalendarClock className="h-4 w-4 text-ink" /><b>{st.upcoming}</b> service{st.upcoming === 1 ? '' : 's'} coming up</li>
              </ul>
              <div className="mt-2 text-xs text-ink-soft">Last checked {relTime(state.lastCheckedAt, state.clock)}</div>
            </div>
          </div>
          <div className="flex justify-center md:justify-end">
            <SaathiHero />
          </div>
        </div>
      </section>

      {state.approvals.length > 0 && (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-bold">Only you can decide this</h2>
            {state.approvals.length > 1 && <button className="text-sm font-bold text-peacock hover:underline" onClick={() => setPanel('approvals')}>See all {state.approvals.length}</button>}
          </div>
          <ApprovalCard a={state.approvals[0]} />
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        {/* B. Important work in progress */}
        {repair ? (
          <section className="relative rounded-[28px] border-2 border-ink bg-white p-5 shadow-pop sm:p-6">
            <span className="stamp absolute -top-3 left-6 bg-mirchi text-white">Being chased</span>
            <div className="flex items-start gap-4">
              <button onClick={() => openAsset(repair.assetId)} className="grid h-20 w-20 flex-none place-items-center rounded-2xl bg-mirchi-soft" aria-label="Open geyser memory">
                <ApplianceArt type="geyser" mood="worried" className="h-16 w-16" />
              </button>
              <div className="min-w-0">
                <h2 className="text-2xl font-bold leading-tight sm:text-3xl">{repair.title}</h2>
                <div className="mt-1 text-sm text-ink-soft">Reported {relTime(repair.reportedAt, state.clock)} · {state.providers.find((p) => p.id === repair.providerId)?.name}</div>
                <div className="mt-2"><StateBadge state={repair.state} /></div>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-2xl bg-mirchi-soft p-2.5"><div className="font-display text-2xl font-bold text-mirchi-deep">{repair.missed}</div><div className="text-[11px] font-bold leading-tight">promised visits missed</div></div>
              <div className="rounded-2xl bg-sand p-2.5"><div className="font-display text-2xl font-bold">{repair.followUps}</div><div className="text-[11px] font-bold leading-tight">follow-ups sent</div></div>
              <div className="rounded-2xl bg-peacock-soft p-2.5"><div className="font-display text-2xl font-bold text-peacock-deep">{repair.alternative && repair.alternative.status !== 'declined' ? 1 : 0}</div><div className="text-[11px] font-bold leading-tight">backup technician lined up</div></div>
            </div>
            {/* journey */}
            <ol className="mt-5 grid grid-cols-5 gap-1" aria-label="Repair journey">
              {JOURNEY.map((step, i) => {
                const cur = journeyIndex(repair);
                const done = i < cur;
                const now = i === cur;
                return (
                  <li key={step} className="flex flex-col items-center text-center">
                    <div className="flex w-full items-center">
                      <span className={`h-0.5 flex-1 ${i === 0 ? 'opacity-0' : done || now ? 'bg-peacock' : 'bg-sand-deep'}`} />
                      <span className={`grid h-7 w-7 flex-none place-items-center rounded-full border-2 ${done ? 'border-peacock bg-peacock text-white' : now ? (step === 'Visit missed' ? 'border-ink bg-mirchi text-white' : 'border-ink bg-haldi') : 'border-sand-deep bg-cream text-ink-soft'}`}>
                        {done ? <Check className="h-4 w-4" /> : <CircleDot className="h-3.5 w-3.5" />}
                      </span>
                      <span className={`h-0.5 flex-1 ${i === JOURNEY.length - 1 ? 'opacity-0' : done ? 'bg-peacock' : 'bg-sand-deep'}`} />
                    </div>
                    <span className={`mt-1.5 text-[11px] leading-tight ${now ? 'font-bold' : 'text-ink-soft'}`}>{step}</span>
                  </li>
                );
              })}
            </ol>
            <div className="mt-5 rounded-2xl bg-cream p-4">
              <div className="label">Right now</div>
              <div className="mt-0.5 font-bold">{honestStatus(state, repair)}</div>
              {repair.nextAction && <div className="mt-1 text-sm text-ink-soft">Next: {repair.nextAction}{repair.nextActionAt ? ` · ${fmtDateTime(repair.nextActionAt)}` : ''}</div>}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button className="btn-primary" onClick={() => go({ screen: 'work', caseId: repair.id })}>
                See what I'm doing <ArrowRight className="h-4 w-4" />
              </button>
              <HandArrow className="hidden h-8 w-14 -scale-x-100 sm:block" />
            </div>
          </section>
        ) : (
          <section className="relative flex flex-col items-start gap-3 rounded-[28px] border-2 border-ink bg-leaf-soft p-6 shadow-pop">
            <span className="stamp absolute -top-3 left-6 bg-leaf text-white">Sorted</span>
            <PartyPopper className="h-8 w-8 text-leaf-deep" />
            <h2 className="text-2xl font-bold">No repairs stuck anywhere.</h2>
            {lastClosed && (
              <p className="text-ink-soft">
                <b className="text-ink">{lastClosed.title}</b> was closed {relTime(lastClosed.closedAt!, state.clock)} after {lastClosed.followUps} follow-ups. Receipt saved to memory.
              </p>
            )}
            {lastClosed && <button className="btn-ghost" onClick={() => go({ screen: 'work', caseId: lastClosed.id })}>See the closed case <ArrowRight className="h-4 w-4" /></button>}
          </section>
        )}

        {/* C. Upcoming maintenance */}
        <section className="relative overflow-hidden rounded-[28px] bg-peacock p-5 text-cream sm:p-6">
          <div className="pointer-events-none absolute bottom-3 right-3 hidden opacity-90 sm:block"><ApplianceArt type="ac" className="h-28 w-28" /></div>
          <div className="relative">
            <div className="label !text-cream/70">Coming up</div>
            <h2 className="mt-1 text-2xl font-bold leading-tight">{ac.brand} {ac.name}</h2>
            <div className="text-sm text-cream/80">{ac.room}</div>
            <div className="mt-4 flex items-center gap-4">
              <div className="grid h-24 w-24 flex-none place-items-center rounded-full border-2 border-cream bg-cream text-ink" aria-label={dueText(acDays)}>
                <div className="text-center leading-none">
                  <div className="font-display text-4xl font-black">{Math.abs(acDays)}</div>
                  <div className="text-[11px] font-bold">{acDays >= 0 ? (acDays === 1 ? 'day left' : 'days left') : 'days late'}</div>
                </div>
              </div>
              <ul className="space-y-1 text-sm">
                <li>Service {dueText(acDays)} · {acDue && fmtShort(acDue)}</li>
                {acLast && <li>Last service {relTime(acLast.date, state.clock)}, {rupees(acLast.amount ?? 0)}</li>}
                <li>Previous technician: {acPro?.contactPerson} ({acPro?.name})</li>
              </ul>
            </div>
            <div className="mt-4 max-w-[85%] rounded-2xl bg-peacock-deep/60 p-3 text-sm">
              {acCase?.appointment ? (
                <><b>Booked:</b> {fmtDateTime(acCase.appointment.start)} with {acPro?.contactPerson}. <span className="opacity-80">Simulated booking.</span></>
              ) : acCase ? (
                <><b>Waiting:</b> {acCase.nextAction}</>
              ) : (
                <>Saathi books it on its own within your rules: {ac.rule?.days.join('/')} {ac.rule && WINDOW_LABEL[ac.rule.window].toLowerCase()}, up to {rupees(ac.rule?.maxCost ?? 0)}.</>
              )}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="btn bg-cream text-ink hover:bg-white" onClick={() => go({ screen: 'calendar' })}>View service plan <ArrowRight className="h-4 w-4" /></button>
              {!acCase && <button className="btn border border-cream/60 text-cream hover:bg-peacock-deep" onClick={() => act((s) => bookServiceNow(s, 'ac'))}>Let Saathi book now</button>}
              {acCase && <button className="btn border border-cream/60 text-cream hover:bg-peacock-deep" onClick={() => go({ screen: 'work', caseId: acCase.id })}>Open booking</button>}
            </div>
          </div>
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        {/* D. Sorted by Saathi */}
        <section>
          <div className="mb-3 flex items-end justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkle className="h-6 w-6" />
              <h2 className="text-2xl font-bold">Sorted by Saathi</h2>
            </div>
            <button className="text-sm font-bold text-peacock hover:underline" onClick={() => setPanel('activity')}>All activity</button>
          </div>
          <ul className="space-y-2.5">
            {sorted.map((a, i) => (
              <li key={a.id}>
                <button
                  onClick={() => (a.link?.type === 'case' ? go({ screen: 'work', caseId: a.link.id }) : a.link && openAsset(a.link.id, 'overview'))}
                  className={`group flex w-full items-start gap-3 rounded-2xl border border-sand-deep/60 bg-white/80 p-4 text-left transition hover:-translate-y-0.5 hover:border-ink/40 ${i % 2 ? 'sm:ml-6' : ''}`}
                >
                  <span className="mt-0.5 grid h-9 w-9 flex-none place-items-center rounded-full border-2 border-ink bg-leaf-soft"><Check className="h-4 w-4 text-leaf-deep" /></span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2"><LabelChip label={a.label} /><span className="text-xs text-ink-soft">{relTime(a.at, state.clock)}</span></span>
                    <span className="mt-1 block font-bold leading-snug">{a.title}</span>
                    <span className="mt-0.5 block text-sm text-ink-soft">{a.outcome}</span>
                  </span>
                  <ArrowRight className="mt-2 h-4 w-4 flex-none opacity-40 group-hover:opacity-100" />
                </button>
              </li>
            ))}
          </ul>
        </section>

        {/* E. Household overview */}
        <section className="rounded-[28px] bg-sand/70 bg-dots p-5 sm:p-6">
          <h2 className="text-2xl font-bold">The house at a glance</h2>
          <p className="text-sm text-ink-soft">{state.household.society}</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <Tile n={st.assets} label="things Saathi remembers" onClick={() => go({ screen: 'memory' })} cls="bg-cream" />
            <Tile n={st.active} label={`active case${st.active === 1 ? '' : 's'}`} onClick={() => go({ screen: 'work' })} cls="bg-mirchi-soft" />
            <Tile n={st.maintenance30} label="services in the next 30 days" onClick={() => go({ screen: 'calendar' })} cls="bg-peacock-soft" />
            <Tile n={st.contracts} label="warranties / AMCs to watch" onClick={() => go({ screen: 'calendar' })} cls="bg-haldi-soft" />
          </div>
          <p className="mt-4 text-xs text-ink-soft">Counts come straight from the household's memory and open work. Today in the demo: {fmtDate(state.clock)}.</p>
        </section>
      </div>
    </div>
  );
}

function Tile({ n, label, onClick, cls }: { n: number; label: string; onClick: () => void; cls: string }) {
  return (
    <button onClick={onClick} className={`rounded-2xl border border-ink/10 p-4 text-left transition hover:-translate-y-0.5 hover:border-ink/40 ${cls}`}>
      <div className="font-display text-4xl font-black leading-none">{n}</div>
      <div className="mt-1 text-sm font-bold leading-tight">{label}</div>
    </button>
  );
}
