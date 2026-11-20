import { useState } from 'react';
import { ArrowRight, Check, HandCoins, KeyRound, DoorOpen, CalendarCheck, X } from 'lucide-react';
import { useStore } from '../store';
import type { Approval, ActivityLabel, TimeWindow, Weekday } from '../types';
import { fmtDateTime, relTime, rupees, WINDOW_LABEL } from '../logic/dates';
import { resolveApproval, updateSettings } from '../logic/workflow';
import { Drawer, LabelChip, Tabs, Toggle } from './ui';
import { BalconyDoodle } from './Doodles';

const APPROVAL_ICON = {
  alt_spend: <HandCoins className="h-5 w-5" />,
  service_spend: <HandCoins className="h-5 w-5" />,
  amc_spend: <HandCoins className="h-5 w-5" />,
  slot: <CalendarCheck className="h-5 w-5" />,
  access: <DoorOpen className="h-5 w-5" />,
  otp: <KeyRound className="h-5 w-5" />,
};

export function ApprovalCard({ a, compact = false }: { a: Approval; compact?: boolean }) {
  const { act, state, go } = useStore();
  const c = state.cases.find((x) => x.id === a.caseId);
  const yes = a.action === 'otp' ? 'I shared it myself' : a.action === 'access' ? 'Someone is home, let in' : a.amount ? `Approve ${rupees(a.amount)}` : 'Confirm';
  const no = a.action === 'otp' ? 'Hold it' : a.action === 'access' ? 'Not now' : 'Decline';
  return (
    <div className="animate-slide-up rounded-2xl border-2 border-mirchi bg-white p-4">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 flex-none place-items-center rounded-full bg-mirchi-soft text-mirchi-deep">{APPROVAL_ICON[a.action]}</span>
        <div className="min-w-0 flex-1">
          <div className="font-bold leading-snug">{a.title}</div>
          <p className="mt-0.5 text-sm text-ink-soft">{a.detail}</p>
          {!compact && c && (
            <button onClick={() => go({ screen: 'work', caseId: c.id })} className="mt-1 inline-flex items-center gap-1 text-xs font-bold text-peacock hover:underline">
              {c.title} <ArrowRight className="h-3 w-3" />
            </button>
          )}
          <div className="mt-1 text-[11px] text-ink-soft">Approver: {state.settings.approver} · asked {relTime(a.createdAt, state.clock)}</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <button className="btn-ghost !min-h-[36px] !py-1.5" onClick={() => act((s) => resolveApproval(s, a.id, false))}>
          <X className="h-4 w-4" /> {no}
        </button>
        <button className="btn-primary !min-h-[36px] !py-1.5" onClick={() => act((s) => resolveApproval(s, a.id, true))}>
          <Check className="h-4 w-4" /> {yes}
        </button>
      </div>
    </div>
  );
}

function ApprovalsPanel() {
  const { state } = useStore();
  return (
    <div className="space-y-3 p-5">
      <p className="text-sm text-ink-soft">Saathi only interrupts you for money, entry to your home, OTPs, and bookings that need someone present.</p>
      {state.approvals.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-3xl bg-white/60 p-8 text-center">
          <BalconyDoodle />
          <div className="font-display text-lg font-bold">Nothing needs you right now</div>
          <p className="text-sm text-ink-soft">Routine work is moving on its own, within your rules.</p>
        </div>
      ) : (
        state.approvals.map((a) => <ApprovalCard key={a.id} a={a} />)
      )}
    </div>
  );
}

function ActivityPanel() {
  const { state, go, openAsset } = useStore();
  const [filter, setFilter] = useState<'all' | ActivityLabel>('all');
  const labels: ActivityLabel[] = ['Handled automatically', 'Waiting for the provider', 'Your approval needed', 'Next follow-up queued', 'Completed and saved'];
  const items = state.activities.filter((a) => filter === 'all' || a.label === filter);
  return (
    <div className="p-5">
      <Tabs value={filter} onChange={setFilter} items={[{ id: 'all', label: 'All' }, ...labels.map((l) => ({ id: l, label: l, count: state.activities.filter((a) => a.label === l).length }))]} />
      <ol className="mt-4 space-y-3">
        {items.map((a) => (
          <li key={a.id} className="rounded-2xl border border-sand-deep/70 bg-white/80 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <LabelChip label={a.label} />
              <span className="text-xs text-ink-soft">{fmtDateTime(a.at)}</span>
            </div>
            <div className="mt-2 font-bold leading-snug">{a.title}</div>
            <dl className="mt-2 grid grid-cols-[72px_1fr] gap-x-2 gap-y-1 text-sm">
              <dt className="label !text-[10px] pt-0.5">Why</dt>
              <dd>{a.why}</dd>
              <dt className="label !text-[10px] pt-0.5">Evidence</dt>
              <dd>{a.evidence}</dd>
              <dt className="label !text-[10px] pt-0.5">Outcome</dt>
              <dd>{a.outcome}</dd>
              {a.next && (
                <>
                  <dt className="label !text-[10px] pt-0.5">Next</dt>
                  <dd className="font-medium text-peacock-deep">{a.next}</dd>
                </>
              )}
            </dl>
            {a.link && (
              <button
                onClick={() => (a.link!.type === 'case' ? go({ screen: 'work', caseId: a.link!.id }) : openAsset(a.link!.id))}
                className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-peacock hover:underline"
              >
                Open {a.link.type === 'case' ? 'workflow' : 'asset'} <ArrowRight className="h-3 w-3" />
              </button>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

const DAYS: Weekday[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function Row({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-dashed border-ink/15 py-4 last:border-0">
      <div>
        <div className="font-bold">{title}</div>
        {hint && <div className="mt-0.5 text-sm text-ink-soft">{hint}</div>}
      </div>
      <div className="flex-none">{children}</div>
    </div>
  );
}

function SettingsPanel() {
  const { state, act, openProvider } = useStore();
  const st = state.settings;
  const set = (patch: Partial<typeof st>) => act((s) => updateSettings(s, patch));
  const preferred = state.providers.filter((p) => p.preferred);
  return (
    <div className="p-5">
      <p className="text-sm text-ink-soft">These rules decide what Saathi does alone and when it stops to ask. Changes apply to live work immediately.</p>
      <div className="mt-2">
        <Row title="Pre-approved spend per job" hint="Anything above this waits for an approver.">
          <div className="flex items-center gap-1 rounded-xl border border-sand-deep bg-white px-2">
            <span className="text-sm font-bold">₹</span>
            <input
              type="number"
              min={0}
              step={100}
              value={st.maxSpend}
              onChange={(e) => set({ maxSpend: Math.max(0, Number(e.target.value) || 0) })}
              className="w-20 bg-transparent py-2 text-sm font-bold focus:outline-none"
              aria-label="Maximum pre-approved spend in rupees"
            />
          </div>
        </Row>
        <Row title="Who approves expenses">
          <select className="input !w-auto" value={st.approver} onChange={(e) => set({ approver: e.target.value })} aria-label="Approver">
            <option>Ananya or Rohit</option>
            <option>Ananya only</option>
            <option>Rohit only</option>
          </select>
        </Row>
        <Row title="Contact backup providers on its own" hint="Ask authorised backups for quotes when the first provider keeps failing.">
          <Toggle checked={st.autoAlternates} onChange={(v) => set({ autoAlternates: v })} label="Contact backups automatically" />
        </Row>
        <Row title="Escalate to supervisors" hint={st.escalationAllowed ? `Allowed after ${st.escalateAfter} missed visits.` : 'Off: Saathi will only follow up.'}>
          <div className="flex items-center gap-2">
            {st.escalationAllowed && (
              <select className="input !w-auto !py-1.5" value={st.escalateAfter} onChange={(e) => set({ escalateAfter: Number(e.target.value) })} aria-label="Missed visits before escalation">
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>after {n}</option>
                ))}
              </select>
            )}
            <Toggle checked={st.escalationAllowed} onChange={(v) => set({ escalationAllowed: v })} label="Allow escalation" />
          </div>
        </Row>
        <Row title="Routine reminders & follow-ups" hint="Lets queued follow-ups run as triggers without asking.">
          <Toggle checked={st.routineFollowUps} onChange={(v) => set({ routineFollowUps: v })} label="Routine follow-ups" />
        </Row>
        <Row title="Home access" hint="What happens when a technician reaches the gate.">
          <select className="input !w-auto" value={st.accessRule} onChange={(e) => set({ accessRule: e.target.value as typeof st.accessRule })} aria-label="Home access rule">
            <option value="resident_present">Ask me; someone must be home</option>
            <option value="security_desk">Security desk may let booked technicians in</option>
          </select>
        </Row>
        <div className="py-4">
          <div className="font-bold">Allowed service days</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {DAYS.map((d) => {
              const on = st.days.includes(d);
              return (
                <button key={d} onClick={() => set({ days: on ? st.days.filter((x) => x !== d) : [...st.days, d] })} className={`rounded-full border-2 px-3 py-1 text-sm font-bold ${on ? 'border-ink bg-haldi' : 'border-sand-deep bg-white text-ink-soft'}`} aria-pressed={on}>
                  {d}
                </button>
              );
            })}
          </div>
          <div className="mt-4 font-bold">Allowed time windows</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {(Object.keys(WINDOW_LABEL) as TimeWindow[]).map((w) => {
              const on = st.windows.includes(w);
              return (
                <button key={w} onClick={() => set({ windows: on ? st.windows.filter((x) => x !== w) : [...st.windows, w] })} className={`rounded-full border-2 px-3 py-1 text-sm font-bold ${on ? 'border-ink bg-peacock text-white' : 'border-sand-deep bg-white text-ink-soft'}`} aria-pressed={on}>
                  {WINDOW_LABEL[w]}
                </button>
              );
            })}
          </div>
        </div>
        <div className="border-t border-dashed border-ink/15 py-4">
          <div className="font-bold">Preferred providers</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {preferred.map((p) => (
              <button key={p.id} onClick={() => openProvider(p.id)} className="rounded-full bg-white px-3 py-1 text-sm font-medium hover:bg-sand">
                {p.name}
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs text-ink-soft">Change these from People & Providers.</p>
        </div>
        <div className="rounded-2xl bg-ink p-4 text-sm text-cream">
          <div className="font-bold">Never automatic</div>
          OTPs are never read or shared by Saathi. Payments go through links you open yourself.
        </div>
      </div>
    </div>
  );
}

export function Panels() {
  const { panel, setPanel, state } = useStore();
  const titles = {
    approvals: { t: 'Needs you', s: `${state.approvals.length} pending` },
    activity: { t: 'Agent activity', s: 'What Saathi did, why, and what is next' },
    settings: { t: 'Household rules', s: 'How much Saathi can do on its own' },
  } as const;
  if (!panel || panel === 'memory') return null;
  return (
    <Drawer
      open
      onClose={() => setPanel(null)}
      title={
        <div>
          <div className="font-display text-xl font-bold">{titles[panel].t}</div>
          <div className="text-sm text-ink-soft">{titles[panel].s}</div>
        </div>
      }
    >
      {panel === 'approvals' && <ApprovalsPanel />}
      {panel === 'activity' && <ActivityPanel />}
      {panel === 'settings' && <SettingsPanel />}
    </Drawer>
  );
}
