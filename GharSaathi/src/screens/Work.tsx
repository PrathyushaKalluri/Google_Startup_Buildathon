import { useState } from 'react';
import { ArrowLeft, ArrowRight, BadgeCheck, CheckCircle2, Flag, Play, Repeat, UserCheck, Hourglass, AlertTriangle } from 'lucide-react';
import { useStore } from '../store';
import type { Case, CaseState } from '../types';
import { duration, fmtDate, fmtDateTime, fmtTime, relTime, rupees } from '../logic/dates';
import { honestStatus, isOpen, STATE_LABEL } from '../logic/derive';
import { altNeedsApproval, approveAlternative, canApproveAlternative, canEscalate, canFollowUp, canTryAnother, completeCase, escalate, runFollowUp, tryAnother, type Gate } from '../logic/workflow';
import { ApplianceArt, BalconyDoodle, Sparkle } from '../components/Doodles';
import { DemoTag, EVENT_META, Modal, SectionHead, StateBadge, Tabs } from '../components/ui';
import { ApprovalCard } from '../components/Panels';

type Filter = 'all' | 'progress' | 'waiting' | 'approval' | 'done';

const WAITING_TEXT: Record<Case['waitingOn'], string> = { provider: 'the provider', resident: 'you', saathi: 'Saathi', nobody: 'nobody' };

export function Work() {
  const { route } = useStore();
  if (route.caseId) return <CaseDetail id={route.caseId} />;
  return <WorkList />;
}

function WorkList() {
  const { state, go } = useStore();
  const [filter, setFilter] = useState<Filter>('all');
  const needsMe = (c: Case) => isOpen(c) && (c.waitingOn === 'resident' || state.approvals.some((a) => a.caseId === c.id));
  const match = (c: Case, f: Filter) =>
    f === 'all' ? true : f === 'progress' ? isOpen(c) : f === 'waiting' ? isOpen(c) && c.waitingOn === 'provider' : f === 'approval' ? needsMe(c) : !isOpen(c);
  const list = state.cases.filter((c) => match(c, filter)).sort((a, b) => Number(isOpen(b)) - Number(isOpen(a)) || b.lastActionAt.localeCompare(a.lastActionAt));

  return (
    <div>
      <SectionHead kicker="Kaam Chal Raha Hai" title={<>Every responsibility, until it's actually done<span className="text-mirchi">.</span></>} />
      <p className="-mt-2 mb-5 max-w-2xl text-ink-soft">Each job keeps its own memory: every attempt, every promise, every miss. Saathi works on it until there is proof of the outcome.</p>
      <Tabs
        value={filter}
        onChange={setFilter}
        items={[
          { id: 'all', label: 'All work', count: state.cases.length },
          { id: 'progress', label: 'In progress', count: state.cases.filter((c) => match(c, 'progress')).length },
          { id: 'waiting', label: 'Waiting for someone else', count: state.cases.filter((c) => match(c, 'waiting')).length },
          { id: 'approval', label: 'Needs my approval', count: state.cases.filter((c) => match(c, 'approval')).length },
          { id: 'done', label: 'Completed', count: state.cases.filter((c) => match(c, 'done')).length },
        ]}
      />
      <div className="mt-5 space-y-3">
        {list.length === 0 && (
          <div className="flex flex-col items-center gap-2 rounded-3xl bg-white/60 p-10 text-center">
            <BalconyDoodle />
            <div className="font-display text-lg font-bold">{filter === 'approval' ? 'Nothing needs you' : filter === 'done' ? 'Nothing closed yet' : 'All quiet here'}</div>
            <p className="max-w-sm text-sm text-ink-soft">{filter === 'done' ? 'Closed jobs land here with their receipts once you confirm the outcome.' : 'New work starts when a rule triggers or you report a problem. Try "Run next trigger" in the Service Calendar.'}</p>
          </div>
        )}
        {list.map((c) => {
          const a = state.assets.find((x) => x.id === c.assetId)!;
          const last = c.events[c.events.length - 1];
          const me = needsMe(c);
          return (
            <button key={c.id} onClick={() => go({ screen: 'work', caseId: c.id })} className={`group grid w-full gap-4 rounded-[24px] border-2 bg-white p-4 text-left transition hover:-translate-y-0.5 hover:shadow-pop sm:grid-cols-[auto_1fr_auto] sm:items-center ${me ? 'border-mirchi' : 'border-ink/15 hover:border-ink'}`}>
              <div className="hidden h-16 w-16 place-items-center rounded-2xl bg-sand/70 sm:grid">
                <ApplianceArt type={a.type} mood={c.kind === 'repair' && isOpen(c) ? 'worried' : 'happy'} className="h-14 w-14" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-display text-lg font-bold">{c.title}</span>
                  <StateBadge state={c.state} />
                  {me && <span className="rounded-full bg-mirchi px-2 py-0.5 text-[11px] font-bold text-white">You need to act</span>}
                </div>
                <div className="text-sm text-ink-soft">{a.brand} {a.name} · {a.room}</div>
                <dl className="mt-2 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
                  <div><dt className="inline text-ink-soft">Waiting on: </dt><dd className="inline font-bold">{WAITING_TEXT[c.waitingOn]}</dd></div>
                  <div><dt className="inline text-ink-soft">Follow-ups: </dt><dd className="inline font-bold">{c.followUps}{c.missed ? ` · ${c.missed} missed visits` : ''}</dd></div>
                  <div className="sm:col-span-2"><dt className="inline text-ink-soft">Last action ({relTime(c.lastActionAt, state.clock)}): </dt><dd className="inline">{last?.text}</dd></div>
                  {c.nextAction && <div className="sm:col-span-2"><dt className="inline text-ink-soft">Next: </dt><dd className="inline font-bold text-peacock-deep">{c.nextAction}{c.nextActionAt ? ` · ${fmtDateTime(c.nextActionAt)}` : ''}</dd></div>}
                </dl>
              </div>
              <ArrowRight className="hidden h-6 w-6 opacity-40 group-hover:opacity-100 sm:block" />
            </button>
          );
        })}
      </div>
    </div>
  );
}

const FLOW: CaseState[] = ['issue_received', 'checking_memory', 'contacting_provider', 'awaiting_provider', 'appointment_proposed', 'technician_missed', 'escalation', 'awaiting_approval', 'appointment_confirmed', 'technician_en_route', 'repair_in_progress', 'awaiting_verification', 'completed'];

function ControlButton({ gate, onClick, icon, label, variant = 'ghost' }: { gate: Gate; onClick: () => void; icon: JSX.Element; label: string; variant?: 'primary' | 'ghost' | 'coral' | 'teal' }) {
  const cls = variant === 'primary' ? 'btn-primary' : variant === 'coral' ? 'btn-coral' : variant === 'teal' ? 'btn-teal' : 'btn-ghost';
  return (
    <div>
      <button className={`${cls} w-full !justify-start`} onClick={onClick} disabled={!gate.ok}>
        {icon} {label}
      </button>
      {!gate.ok && gate.reason && <div className="mt-1 px-3 text-xs text-ink-soft">{gate.reason}</div>}
    </div>
  );
}

function CaseDetail({ id }: { id: string }) {
  const { state, act, go, openAsset, openProvider } = useStore();
  const [completing, setCompleting] = useState(false);
  const c = state.cases.find((x) => x.id === id);
  if (!c) {
    return (
      <div className="rounded-3xl bg-white/70 p-10 text-center">
        <div className="font-display text-xl font-bold">This case isn't here any more</div>
        <p className="text-ink-soft">The demo may have been reset.</p>
        <button className="btn-primary mt-4" onClick={() => go({ screen: 'work' })}>Back to all work</button>
      </div>
    );
  }
  const a = state.assets.find((x) => x.id === c.assetId)!;
  const provider = state.providers.find((p) => p.id === c.providerId);
  const original = state.providers.find((p) => p.id === c.originalProviderId);
  const alt = c.alternative;
  const altP = alt && state.providers.find((p) => p.id === alt.providerId);
  const approvals = state.approvals.filter((x) => x.caseId === c.id);
  const visited = new Set(c.events.length ? [] : ['issue_received']);
  // Map events to the states they evidence, for the progress strip.
  for (const e of c.events) {
    if (e.kind === 'resident' || (e.kind === 'info' && e.channel === 'Trigger')) visited.add('issue_received');
    if (e.kind === 'memory') visited.add('checking_memory');
    if (e.kind === 'attempt') visited.add('contacting_provider');
    if (e.kind === 'promise') visited.add('appointment_proposed');
    if (e.kind === 'missed') visited.add('technician_missed');
    if (e.kind === 'escalation') visited.add('escalation');
    if (e.kind === 'approval') visited.add('awaiting_approval');
    if (e.kind === 'confirmed') visited.add('appointment_confirmed');
    if (e.kind === 'arrival') visited.add('repair_in_progress');
    if (e.kind === 'completed') visited.add('completed');
  }
  visited.add(c.state);

  return (
    <div>
      <button onClick={() => go({ screen: 'work' })} className="mb-4 inline-flex items-center gap-1 text-sm font-bold text-ink-soft hover:text-ink">
        <ArrowLeft className="h-4 w-4" /> All work
      </button>

      {/* 1. Case header */}
      <section className="relative overflow-hidden rounded-[28px] border-2 border-ink bg-white p-5 shadow-pop sm:p-6">
        <div className={`absolute inset-y-0 right-0 hidden w-48 sm:block ${c.kind === 'repair' && isOpen(c) ? 'bg-mirchi-soft' : 'bg-peacock-soft'} bg-dots`} />
        <div className="relative flex items-start gap-4">
          <button onClick={() => openAsset(a.id)} className="grid h-20 w-20 flex-none place-items-center rounded-2xl bg-sand/70 sm:order-last sm:ml-auto sm:h-28 sm:w-28 sm:bg-transparent" aria-label={`Open ${a.brand} ${a.name} memory`}>
            <ApplianceArt type={a.type} mood={c.kind === 'repair' && isOpen(c) ? 'worried' : 'happy'} className="h-16 w-16 sm:h-28 sm:w-28" />
          </button>
          <div className="min-w-0">
            <div className="label">{a.brand} {a.name} · {a.room}</div>
            <h1 className="text-3xl font-black leading-tight sm:text-4xl">{c.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <StateBadge state={c.state} />
              {c.reference && <span className="rounded-full bg-sand px-2.5 py-1 text-xs font-bold">Ref {c.reference}</span>}
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
              <div><dt className="text-ink-soft">Reported</dt><dd className="font-bold">{fmtDateTime(c.reportedAt)}</dd></div>
              <div><dt className="text-ink-soft">Provider</dt><dd><button className="font-bold hover:underline" onClick={() => provider && openProvider(provider.id)}>{provider?.name}</button></dd></div>
              <div><dt className="text-ink-soft">{isOpen(c) ? 'Unresolved for' : 'Took'}</dt><dd className="font-bold">{duration(c.reportedAt, c.closedAt ?? state.clock)}</dd></div>
              <div><dt className="text-ink-soft">Follow-ups</dt><dd className="font-bold">{c.followUps}{c.missed ? ` · ${c.missed} missed` : ''}</dd></div>
            </dl>
          </div>
        </div>
      </section>

      {approvals.length > 0 && (
        <div className="mt-5 space-y-3">
          {approvals.map((ap) => <ApprovalCard key={ap.id} a={ap} compact />)}
        </div>
      )}

      {/* State strip */}
      <div className="no-scrollbar mt-5 flex gap-1.5 overflow-x-auto pb-1" aria-label="Workflow states">
        {FLOW.filter((s) => visited.has(s) || s === c.state).map((s) => (
          <span key={s} className={`whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold ${s === c.state ? 'border-2 border-ink bg-haldi' : 'bg-peacock-soft text-peacock-deep'}`}>
            {s === c.state ? '● ' : '✓ '}{STATE_LABEL[s]}
          </span>
        ))}
      </div>

      <div className="mt-5 grid gap-6 lg:grid-cols-[1fr_340px]">
        {/* 2. Timeline */}
        <section>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-2xl font-bold">What I've done</h2>
            <div className="flex flex-wrap gap-1.5 text-[11px]">
              <span className="rounded-full border border-dashed border-ink/50 bg-haldi-soft px-2 py-0.5 font-bold">Promise ≠ appointment</span>
              <span className="rounded-full bg-peacock px-2 py-0.5 font-bold text-white">Confirmed</span>
              <span className="rounded-full bg-leaf px-2 py-0.5 font-bold text-white">Verified by you</span>
            </div>
          </div>
          <ol className="relative">
            {[...c.events].reverse().map((e, i) => {
              const m = EVENT_META[e.kind];
              return (
                <li key={e.id} className={`relative flex gap-3 pb-4 ${i === 0 ? 'animate-slide-up' : ''}`}>
                  <div className="flex flex-col items-center">
                    <span className={`grid h-9 w-9 flex-none place-items-center rounded-full ${m.dot}`}>{m.icon}</span>
                    <span className="mt-1 w-0.5 flex-1 bg-sand-deep" />
                  </div>
                  <div className={`min-w-0 flex-1 rounded-2xl p-3 ${e.kind === 'missed' ? 'bg-mirchi-soft/60' : e.kind === 'promise' ? 'border border-dashed border-ink/30 bg-white' : e.kind === 'completed' ? 'bg-leaf-soft' : 'bg-white/80'}`}>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
                      <span className="font-bold">{m.label}</span>
                      <span className="text-ink-soft">· {fmtDay(e.at)} {fmtTime(e.at)} · {e.channel.replace(' · simulated', '')}</span>
                      {e.simulated ? <DemoTag /> : <span className="inline-flex items-center gap-0.5 rounded-md bg-peacock-soft px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-peacock-deep"><BadgeCheck className="h-3 w-3" />{e.kind === 'memory' ? 'From saved records' : 'Recorded'}</span>}
                    </div>
                    <p className="mt-1 text-[15px] leading-snug">{e.text}</p>
                    {e.detail && <p className="mt-1 text-xs font-bold text-ink-soft">{e.detail}</p>}
                  </div>
                </li>
              );
            })}
          </ol>
        </section>

        {/* 3. Controls */}
        <aside className="order-first space-y-4 lg:order-none lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-[24px] border-2 border-ink bg-cream p-4 shadow-pop">
            <div className="flex items-center gap-2"><Sparkle className="h-5 w-5" /><span className="label !text-ink">Saathi's status</span></div>
            <div className="mt-1 font-display text-lg font-bold leading-snug">{honestStatus(state, c)}</div>
            {c.nextAction && (
              <div className="mt-2 rounded-xl bg-white p-3 text-sm">
                <div className="flex items-center gap-1.5 font-bold"><Hourglass className="h-4 w-4 text-peacock" /> Next</div>
                {c.nextAction}
                {c.nextActionAt && <div className="text-xs text-ink-soft">{fmtDateTime(c.nextActionAt)} ({relTime(c.nextActionAt, state.clock)})</div>}
              </div>
            )}
            <div className="mt-2 text-xs text-ink-soft">Last action {relTime(c.lastActionAt, state.clock)} · waiting on {WAITING_TEXT[c.waitingOn]}</div>
          </div>

          {isOpen(c) && (
            <div className="space-y-2 rounded-[24px] bg-white/80 p-4">
              <div className="label mb-1">Move it forward</div>
              <ControlButton gate={canFollowUp(state, c)} onClick={() => act((s) => runFollowUp(s, c.id))} icon={<Play className="h-4 w-4" />} label="Run next follow-up" variant="primary" />
              {c.kind === 'repair' && (
                <>
                  <ControlButton gate={canEscalate(state, c)} onClick={() => act((s) => escalate(s, c.id))} icon={<Flag className="h-4 w-4" />} label="Escalate to supervisor" variant="coral" />
                  <ControlButton gate={canTryAnother(state, c)} onClick={() => act((s) => tryAnother(s, c.id))} icon={<Repeat className="h-4 w-4" />} label="Try another provider" />
                  <ControlButton
                    gate={canApproveAlternative(state, c)}
                    onClick={() => act((s) => approveAlternative(s, c.id))}
                    icon={<UserCheck className="h-4 w-4" />}
                    label={alt && altP && alt.status === 'pending' ? (altNeedsApproval(state, c) ? `Approve backup (${rupees(alt.quote)})` : `Book backup (${rupees(alt.quote)}, within limit)`) : 'Approve alternative technician'}
                    variant="teal"
                  />
                </>
              )}
              <ControlButton gate={{ ok: true }} onClick={() => setCompleting(true)} icon={<CheckCircle2 className="h-4 w-4" />} label={c.kind === 'repair' ? 'Mark repair complete' : 'Mark complete'} />
              <p className="pt-1 text-[11px] leading-snug text-ink-soft">The demo plays out on its own clock. Each follow-up moves time forward to when its outcome would be known.</p>
            </div>
          )}

          {alt && altP && c.kind === 'repair' && (
            <div className={`rounded-[24px] border-2 p-4 ${alt.status === 'approved' ? 'border-peacock bg-peacock-soft' : alt.status === 'declined' ? 'border-sand-deep bg-sand/50' : 'border-haldi-deep bg-haldi-soft'}`}>
              <div className="label">{alt.status === 'approved' ? 'Booked instead' : alt.status === 'declined' ? 'Backup on hold' : 'Backup lined up'}</div>
              <button className="mt-1 font-display text-lg font-bold hover:underline" onClick={() => openProvider(altP.id)}>{altP.name}</button>
              <div className="text-sm">{rupees(alt.quote)} · {alt.quoteNote}</div>
              {alt.status === 'pending' && (
                <div className={`mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold ${altNeedsApproval(state, c) ? 'bg-mirchi text-white' : 'bg-peacock text-white'}`}>
                  {altNeedsApproval(state, c) ? <><AlertTriangle className="h-3 w-3" /> Above your {rupees(state.settings.maxSpend)} limit</> : <>Within your {rupees(state.settings.maxSpend)} limit</>}
                </div>
              )}
              {original && original.id !== altP.id && <div className="mt-2 text-xs text-ink-soft">Original: {original.name}{c.missed ? `, ${c.missed} missed visits` : ''}</div>}
            </div>
          )}

          {c.appointment && (
            <div className="rounded-[24px] bg-peacock p-4 text-cream">
              <div className="label !text-cream/70">Appointment</div>
              <div className="font-display text-lg font-bold">{fmtDateTime(c.appointment.start)}–{fmtTime(c.appointment.end)}</div>
              <div className="text-sm">{state.providers.find((p) => p.id === c.appointment!.providerId)?.name} · confirmed by provider (simulated)</div>
              <div className="mt-1 text-xs opacity-80">{c.arrived ? 'Arrival recorded at the gate.' : 'No arrival recorded yet.'}</div>
            </div>
          )}

          {c.outcome && (
            <div className="rounded-[24px] bg-leaf p-4 text-white">
              <div className="label !text-white/80">Verified outcome</div>
              <div className="font-display text-lg font-bold">{c.outcome.summary}</div>
              <div className="text-sm">Receipt {c.outcome.receipt || '—'} · {rupees(c.outcome.amount)} · closed {fmtDate(c.closedAt!)}</div>
              <button className="mt-2 inline-flex items-center gap-1 text-sm font-bold underline" onClick={() => openAsset(a.id, 'history')}>See it in the history <ArrowRight className="h-4 w-4" /></button>
            </div>
          )}
        </aside>
      </div>
      {completing && <CompleteModal c={c} onClose={() => setCompleting(false)} />}
    </div>
  );
}

function fmtDay(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
}

function CompleteModal({ c, onClose }: { c: Case; onClose: () => void }) {
  const { state, act } = useStore();
  const a = state.assets.find((x) => x.id === c.assetId)!;
  const defaults = { repair: 'Thermostat replaced; geyser heating again', service: 'Preventive service done; cooling normal', renewal: 'AMC renewed for one year' };
  const [summary, setSummary] = useState(defaults[c.kind]);
  const [receipt, setReceipt] = useState('');
  const [amount, setAmount] = useState(String(c.expectedAmount ?? ''));
  const [serviced, setServiced] = useState(false);
  const [checked, setChecked] = useState(false);
  const valid = summary.trim().length > 3 && amount !== '' && checked;
  return (
    <Modal
      open
      onClose={onClose}
      title={
        <div>
          <div className="label">Closing the loop</div>
          <div className="font-display text-xl font-bold">{c.kind === 'renewal' ? 'Confirm the renewal' : 'Is it really fixed?'}</div>
        </div>
      }
    >
      <div className="space-y-3">
        {!c.arrived && c.kind !== 'renewal' && (
          <div className="flex gap-2 rounded-2xl bg-mirchi-soft p-3 text-sm">
            <AlertTriangle className="h-5 w-5 flex-none text-mirchi-deep" />
            No technician arrival is recorded on this case. Only close it if the work really happened, say if someone came without Saathi knowing.
          </div>
        )}
        <label className="block">
          <span className="label">What was done</span>
          <input className="input mt-1" value={summary} onChange={(e) => setSummary(e.target.value)} />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="label">Receipt / bill no.</span>
            <input className="input mt-1" value={receipt} onChange={(e) => setReceipt(e.target.value)} placeholder="optional" />
          </label>
          <label className="block">
            <span className="label">Amount paid (₹)</span>
            <input className="input mt-1" type="number" min={0} value={amount} onChange={(e) => setAmount(e.target.value)} />
          </label>
        </div>
        {c.kind === 'repair' && a.rule && (
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5 h-4 w-4 accent-peacock" checked={serviced} onChange={(e) => setServiced(e.target.checked)} />
            The technician also did the {a.rule.label.toLowerCase()} (resets that schedule)
          </label>
        )}
        <label className="flex items-start gap-2 rounded-2xl bg-white p-3 text-sm font-bold">
          <input type="checkbox" className="mt-0.5 h-4 w-4 accent-peacock" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
          {c.kind === 'repair' ? 'I checked it myself: hot water is back.' : c.kind === 'service' ? 'I checked it myself: it is working well.' : 'I paid and received the renewal confirmation.'}
        </label>
        <div className="flex gap-2 pt-1">
          <button className="btn-ghost flex-1" onClick={onClose}>Not yet</button>
          <button
            className="btn-primary flex-1"
            disabled={!valid}
            onClick={() => {
              act((s) => completeCase(s, c.id, { summary: summary.trim(), receipt: receipt.trim(), amount: Number(amount) || 0, serviced }));
              onClose();
            }}
          >
            <CheckCircle2 className="h-4 w-4" /> Close and save
          </button>
        </div>
      </div>
    </Modal>
  );
}
