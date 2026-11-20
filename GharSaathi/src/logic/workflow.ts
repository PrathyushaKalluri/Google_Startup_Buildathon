import type { Activity, ActivityLabel, Approval, AppState, Asset, Case, CaseEvent, Doc, DocField, EventKind, MaintenanceRule, ProviderLog, Settings } from '../types';
import { addMinutes, addMonths, fmtDate, fmtDateTime, fmtDay, fmtShort, fmtTime, nextSlot, rupees, WINDOW_LABEL } from './dates';
import { blockingApproval, nextDue, pendingTriggers } from './derive';

export interface Result {
  state: AppState;
  toast?: string;
}

let counter = 0;
const uid = (p: string) => `${p}-${Date.now().toString(36)}-${(counter++).toString(36)}`;

const later = (a: string, b: string) => (new Date(a) > new Date(b) ? a : b);
const roundUpHour = (iso: string) => {
  const d = new Date(iso);
  if (d.getMinutes() || d.getSeconds()) d.setHours(d.getHours() + 1, 0, 0, 0);
  return d.toISOString();
};
const windowText = (start: string, end: string) => `${fmtDay(start)}, ${fmtTime(start)}–${fmtTime(end)}`;

// ---------- small mutators (operate on a cloned state) ----------

function tick(s: AppState, minutes: number) {
  s.clock = addMinutes(s.clock, minutes);
  s.lastCheckedAt = s.clock;
}

function jumpTo(s: AppState, iso: string) {
  s.clock = later(s.clock, iso);
  s.lastCheckedAt = s.clock;
}

function event(s: AppState, c: Case, kind: EventKind, channel: string, text: string, simulated = true, detail?: string) {
  const e: CaseEvent = { id: uid('ev'), at: s.clock, kind, channel, text, simulated, detail };
  c.events.push(e);
  c.lastActionAt = s.clock;
}

function activity(s: AppState, label: ActivityLabel, title: string, why: string, evidence: string, outcome: string, link?: Activity['link'], next?: string) {
  s.activities.unshift({ id: uid('act'), at: s.clock, label, title, why, evidence, outcome, link, next });
}

function providerLog(s: AppState, providerId: string, outcome: ProviderLog['outcome'], text: string, caseId?: string) {
  const p = s.providers.find((x) => x.id === providerId);
  if (p) p.log.push({ id: uid('pl'), date: s.clock, text, outcome, caseId });
}

function approval(s: AppState, a: Omit<Approval, 'id' | 'createdAt'>) {
  s.approvals = s.approvals.filter((x) => !(x.caseId === a.caseId && x.action === a.action));
  s.approvals.push({ ...a, id: uid('ap'), createdAt: s.clock });
}

const dropApprovals = (s: AppState, caseId: string, action?: Approval['action']) => {
  s.approvals = s.approvals.filter((x) => !(x.caseId === caseId && (!action || x.action === action)));
};

const pName = (s: AppState, id: string) => s.providers.find((p) => p.id === id)?.name ?? 'Provider';
const person = (s: AppState, id: string) => {
  const p = s.providers.find((x) => x.id === id);
  if (!p) return 'the technician';
  if (p.id === 'p-havells') return 'Mahesh';
  return p.kind === 'individual' && p.contactPerson ? p.contactPerson : 'the technician';
};
const assetOf = (s: AppState, c: Case) => s.assets.find((a) => a.id === c.assetId) as Asset;

function edit(state: AppState, caseId: string, fn: (s: AppState, c: Case) => string | undefined): Result {
  const s = structuredClone(state);
  const c = s.cases.find((x) => x.id === caseId);
  if (!c) return { state };
  const toast = fn(s, c);
  return { state: s, toast };
}

// ---------- availability (used by the UI to enable buttons and explain why not) ----------

export interface Gate {
  ok: boolean;
  reason?: string;
}

export function canFollowUp(s: AppState, c: Case): Gate {
  if (c.state === 'completed') return { ok: false, reason: 'Case is closed' };
  if (blockingApproval(s, c.id)) return { ok: false, reason: 'Waiting for your approval first' };
  if (c.state === 'awaiting_verification') return { ok: false, reason: 'Nothing to chase. Check the work and mark it complete.' };
  if (c.kind === 'renewal') return { ok: false, reason: 'Nothing to chase on a renewal' };
  return { ok: true };
}

export function canEscalate(s: AppState, c: Case): Gate {
  if (c.kind !== 'repair' || c.state === 'completed') return { ok: false, reason: 'Only open repairs can be escalated' };
  if (c.escalated) return { ok: false, reason: 'Already escalated' };
  if (c.track === 'visit') return { ok: false, reason: 'A visit is already booked' };
  if (!s.settings.escalationAllowed) return { ok: false, reason: 'Escalation is switched off in your rules' };
  if (c.missed < s.settings.escalateAfter)
    return { ok: false, reason: `Your rule: escalate after ${s.settings.escalateAfter} missed visits (${c.missed} so far)` };
  return { ok: true };
}

function altCandidates(s: AppState, c: Case) {
  const type = assetOf(s, c).type;
  return s.providers.filter((p) => p.id !== c.originalProviderId && p.handles.includes(type) && p.quotes?.[type]);
}

export function canTryAnother(s: AppState, c: Case): Gate {
  if (c.kind !== 'repair' || c.state === 'completed') return { ok: false, reason: 'Only open repairs' };
  if (c.track === 'visit') return { ok: false, reason: 'A visit is already booked' };
  const others = altCandidates(s, c).filter((p) => p.id !== c.alternative?.providerId);
  if (!others.length) return { ok: false, reason: 'No other saved provider handles this' };
  return { ok: true };
}

export function canApproveAlternative(s: AppState, c: Case): Gate {
  if (!c.alternative || c.alternative.status !== 'pending') return { ok: false, reason: 'No backup proposed right now' };
  if (c.track === 'visit') return { ok: false, reason: 'A visit is already booked' };
  if (c.state === 'completed') return { ok: false, reason: 'Case is closed' };
  return { ok: true };
}

export const altNeedsApproval = (s: AppState, c: Case) => !!c.alternative && c.alternative.quote > s.settings.maxSpend;

// ---------- follow-ups ----------

function identifyAlternative(s: AppState, c: Case) {
  if (c.alternative || !s.settings.autoAlternates) return;
  const p = altCandidates(s, c).find((x) => x.backup) ?? altCandidates(s, c)[0];
  if (!p) return;
  const q = p.quotes![assetOf(s, c).type]!;
  c.alternative = { providerId: p.id, quote: q.amount, quoteNote: q.note, status: 'pending' };
  event(s, c, 'info', 'WhatsApp · simulated', `Asked authorised backup ${p.name} for a quote: ${rupees(q.amount)} (${q.note}).`);
  providerLog(s, p.id, 'quoted', `Quoted ${rupees(q.amount)}`, c.id);
  reconcileAlternative(s, c);
}

function reconcileAlternative(s: AppState, c: Case) {
  const alt = c.alternative;
  const needs = !!alt && alt.status === 'pending' && c.track !== 'visit' && c.state !== 'completed' && alt.quote > s.settings.maxSpend;
  const has = s.approvals.some((a) => a.caseId === c.id && a.action === 'alt_spend');
  if (needs && alt) {
    const p = pName(s, alt.providerId);
    approval(s, {
      caseId: c.id, action: 'alt_spend', title: `Book ${p} for the ${assetOf(s, c).type === 'geyser' ? 'geyser' : 'repair'}?`,
      detail: `${pName(s, c.originalProviderId)} has missed ${c.missed} visit${c.missed === 1 ? '' : 's'}. ${p} quotes ${rupees(alt.quote)}, above your ${rupees(s.settings.maxSpend)} limit.`,
      amount: alt.quote,
    });
  } else if (!needs && has) {
    dropApprovals(s, c.id, 'alt_spend');
  }
}

function primaryStep(s: AppState, c: Case): string {
  const centre = pName(s, c.providerId);
  if (c.step === 0) {
    tick(s, 40);
    c.followUps += 1;
    event(s, c, 'attempt', 'Call · simulated', `Follow-up #${c.followUps}: called the ${centre} helpline, quoting ref ${c.reference}.`);
    const start = roundUpHour(addMinutes(s.clock, 180));
    const end = addMinutes(start, 120);
    event(s, c, 'promise', 'Call · simulated', `Coordinator promised a technician ${windowText(start, end)}.`, true, 'A provider promise, not a confirmed appointment');
    providerLog(s, c.providerId, 'responded', `Promised ${windowText(start, end)}`, c.id);
    c.state = 'appointment_proposed';
    c.waitingOn = 'provider';
    c.nextAction = `Check at ${fmtTime(end)} whether the technician actually arrived`;
    c.nextActionAt = end;
    c.step = 1;
    activity(s, 'Next follow-up queued', `${centre} promised a new window`, 'Routine follow-up on an open repair.', `Call with ${centre} (simulated)`, `Promise: ${windowText(start, end)}. Not treated as confirmed.`, { type: 'case', id: c.id }, c.nextAction);
    return `${centre} promised ${fmtTime(start)}–${fmtTime(end)}. Saathi will check it was kept.`;
  }
  if (c.step === 1) {
    jumpTo(s, addMinutes(c.nextActionAt ?? s.clock, 5));
    c.missed += 1;
    c.followUps += 1;
    event(s, c, 'missed', 'Security desk log · simulated', `Missed #${c.missed}: the promised window passed. No arrival, no call. No technician entry at the gate.`);
    providerLog(s, c.providerId, 'missed', 'Missed promised window', c.id);
    event(s, c, 'attempt', 'Call · simulated', `Follow-up #${c.followUps}: called the coordinator. Nobody picked up.`);
    c.state = 'technician_missed';
    identifyAlternative(s, c);
    const esc = canEscalate(s, c);
    c.nextAction = esc.ok
      ? `Escalate to a ${centre} supervisor. Your rule allows it after ${s.settings.escalateAfter} misses.`
      : c.alternative ? 'Book the backup, or keep chasing the centre' : 'Keep chasing the centre';
    c.nextActionAt = addMinutes(s.clock, 60);
    c.step = 2;
    return `Missed again (#${c.missed}). Logged against ${centre}.`;
  }
  tick(s, 60);
  c.followUps += 1;
  const lastReply = [...c.events].reverse().find((e) => e.kind === 'promise' || e.kind === 'evidence');
  const hours = lastReply ? Math.round((new Date(s.clock).getTime() - new Date(lastReply.at).getTime()) / 3_600_000) : 0;
  event(s, c, 'attempt', 'WhatsApp · simulated', `Follow-up #${c.followUps}: sent the case history to ${centre}. No reply — ${hours} hr since they last responded.`);
  providerLog(s, c.providerId, 'no_response', `No reply to follow-up #${c.followUps}`, c.id);
  c.state = 'awaiting_provider';
  c.waitingOn = 'provider';
  c.nextAction = `${centre} has gone quiet. Escalate or book the backup.`;
  c.nextActionAt = addMinutes(s.clock, 90);
  return `No reply from ${centre} (follow-up #${c.followUps}).`;
}

function supervisorStep(s: AppState, c: Case): string {
  const centre = pName(s, c.providerId);
  if (c.step === 0) {
    jumpTo(s, c.nextActionAt ?? s.clock);
    event(s, c, 'evidence', 'Call · simulated', `Service manager Lakshmi (${centre}) called back and apologised for ${c.missed} missed visits.`);
    const slot = nextSlot(s.clock, s.settings.days, s.settings.windows);
    event(s, c, 'promise', 'Call · simulated', `Offered ${windowText(slot.start, slot.end)} with senior technician Mahesh, who fixed this geyser before.`, true, 'Offered slot, waiting for your OK');
    providerLog(s, c.providerId, 'responded', 'Supervisor offered a slot', c.id);
    approval(s, { caseId: c.id, action: 'slot', title: `Confirm ${centre} visit, ${fmtDay(slot.start)}?`, detail: `${fmtTime(slot.start)}–${fmtTime(slot.end)} with Mahesh. Someone needs to be home. ₹400 visit + parts.`, slot });
    c.state = 'awaiting_approval';
    c.waitingOn = 'resident';
    c.nextAction = 'Confirm or decline the offered slot';
    c.nextActionAt = undefined;
    c.step = 1;
    activity(s, 'Your approval needed', `${centre} offered a slot after escalation`, 'Bookings need someone at home, so Saathi asks.', 'Supervisor call (simulated)', windowText(slot.start, slot.end), { type: 'case', id: c.id });
    return 'Supervisor offered a slot. Your OK is needed.';
  }
  if (c.step === 1 || c.step === 2) {
    tick(s, 30);
    event(s, c, 'attempt', 'Email · simulated', 'Asked the service manager for a different slot.');
    const slot = nextSlot(addMinutes(s.clock, 24 * 60), s.settings.days, s.settings.windows);
    event(s, c, 'promise', 'Email · simulated', `Manager offered ${windowText(slot.start, slot.end)} instead.`, true, 'Offered slot, waiting for your OK');
    approval(s, { caseId: c.id, action: 'slot', title: `Confirm ${centre} visit, ${fmtDay(slot.start)}?`, detail: `${fmtTime(slot.start)}–${fmtTime(slot.end)} with Mahesh. Someone needs to be home.`, slot });
    c.state = 'awaiting_approval';
    c.waitingOn = 'resident';
    c.nextAction = 'Confirm or decline the new slot';
    c.step = 3;
    return 'A new slot was offered.';
  }
  tick(s, 60);
  c.followUps += 1;
  event(s, c, 'attempt', 'Email · simulated', `Reminder #${c.followUps} to the service manager: still waiting for a slot you can make.`);
  return 'Reminder sent to the service manager.';
}

function visitStep(s: AppState, c: Case): string {
  const appt = c.appointment!;
  const pro = pName(s, appt.providerId);
  const tech = person(s, appt.providerId);
  if (c.state === 'blocked') {
    const slot = nextSlot(s.clock, s.settings.days, s.settings.windows);
    c.appointment = { ...appt, start: slot.start, end: slot.end };
    event(s, c, 'confirmed', 'WhatsApp · simulated', `Rescheduled with ${pro}: ${windowText(slot.start, slot.end)} (simulated reply).`);
    c.state = 'appointment_confirmed';
    c.waitingOn = 'provider';
    c.nextAction = `Day-of check with ${tech} before ${fmtTime(slot.start)}`;
    c.nextActionAt = addMinutes(slot.start, -45);
    c.step = 0;
    return 'Visit rescheduled.';
  }
  if (c.step === 0) {
    jumpTo(s, addMinutes(appt.start, -45));
    const eta = addMinutes(appt.start, 20);
    event(s, c, 'promise', 'Call · simulated', `Day-of check: ${tech} says he is leaving now. ETA ${fmtTime(eta)}.`, true, 'Technician claim, not yet an arrival');
    c.state = 'technician_en_route';
    c.waitingOn = 'provider';
    c.nextAction = 'Watch for arrival at the gate';
    c.nextActionAt = eta;
    c.step = 1;
    return `${tech} says he is on the way.`;
  }
  if (c.step === 1) {
    jumpTo(s, addMinutes(appt.start, 22));
    if (s.settings.accessRule === 'security_desk') {
      event(s, c, 'arrival', 'Security desk log · simulated', `Security desk let ${tech} (${pro}) in at ${fmtTime(s.clock)}, as your rules allow.`);
      c.arrived = true;
      c.state = 'repair_in_progress';
      c.waitingOn = 'provider';
      c.nextAction = "Wait for the technician's report";
      c.nextActionAt = addMinutes(s.clock, 60);
      c.step = 2;
      providerLog(s, appt.providerId, 'kept', 'Arrived for the booked visit', c.id);
      return 'Technician arrived and was let in by the security desk.';
    }
    event(s, c, 'info', 'Intercom · simulated', `${tech} (${pro}) is at the gate. Your rule says someone must be home before entry.`);
    approval(s, { caseId: c.id, action: 'access', title: `Let ${tech} in?`, detail: `${pro} technician is at the Gulmohar gate. Approve only if someone is at home.` });
    c.state = 'awaiting_approval';
    c.waitingOn = 'resident';
    c.nextAction = 'Confirm someone is home to let the technician in';
    c.nextActionAt = undefined;
    return 'Technician at the gate. Your approval is needed for entry.';
  }
  if (c.step === 2) {
    tick(s, 60);
    const isRepair = c.kind === 'repair';
    const amount = c.expectedAmount ?? 0;
    const work = isRepair ? 'thermostat replaced; heating light cycles normally' : 'jet wash done, filters cleaned, gas pressure normal';
    event(s, c, 'evidence', 'WhatsApp · simulated', `${tech} reports: ${work}. Bill of ${rupees(amount)} shared.`, true, 'Technician report, not yet verified by you');
    c.state = 'awaiting_verification';
    c.waitingOn = 'resident';
    c.nextAction = isRepair ? 'Check the hot water, then mark the repair complete' : 'Check the AC cooling, then mark the service complete';
    c.nextActionAt = undefined;
    c.step = 3;
    const p = s.providers.find((x) => x.id === appt.providerId);
    if (isRepair && p?.kind === 'brand_centre') {
      approval(s, { caseId: c.id, action: 'otp', title: `${pro} asks for the closure OTP`, detail: 'Saathi never reads or shares OTPs. Share it yourself, only after you have checked the hot water.' });
    }
    return 'Technician reports the work is done. Your check is next.';
  }
  return 'Nothing more to chase.';
}

export function runFollowUp(state: AppState, caseId: string): Result {
  const c0 = state.cases.find((c) => c.id === caseId);
  if (!c0) return { state };
  const gate = canFollowUp(state, c0);
  if (!gate.ok) return { state, toast: gate.reason };
  return edit(state, caseId, (s, c) => {
    if (c.track === 'visit') return visitStep(s, c);
    if (c.track === 'supervisor') return supervisorStep(s, c);
    return primaryStep(s, c);
  });
}

export function escalate(state: AppState, caseId: string): Result {
  const c0 = state.cases.find((c) => c.id === caseId);
  if (!c0) return { state };
  const gate = canEscalate(state, c0);
  if (!gate.ok) return { state, toast: gate.reason };
  return edit(state, caseId, (s, c) => {
    tick(s, 15);
    const centre = pName(s, c.providerId);
    const ref = `ESC-${String(7700 + c.followUps * 7).padStart(4, '0')}`;
    event(s, c, 'escalation', 'Email + helpline L2 · simulated', `Escalated to the ${centre} service manager with the full timeline: ${c.missed} missed windows on ref ${c.reference}. Escalation ref ${ref}.`);
    c.escalated = true;
    c.state = 'escalation';
    c.track = 'supervisor';
    c.step = 0;
    c.waitingOn = 'provider';
    const by = addMinutes(s.clock, 180);
    c.nextAction = `Expect a manager callback by ${fmtTime(by)}`;
    c.nextActionAt = by;
    activity(s, 'Waiting for the provider', `Geyser repair escalated to ${centre} supervisor`, `${c.missed} missed visits meets your escalation rule (${s.settings.escalateAfter}).`, `Case timeline, ref ${c.reference}`, `Escalation ${ref} raised (simulated).`, { type: 'case', id: c.id }, c.nextAction);
    return `Escalated. Callback expected by ${fmtTime(by)}.`;
  });
}

export function tryAnother(state: AppState, caseId: string): Result {
  const c0 = state.cases.find((c) => c.id === caseId);
  if (!c0) return { state };
  const gate = canTryAnother(state, c0);
  if (!gate.ok) return { state, toast: gate.reason };
  return edit(state, caseId, (s, c) => {
    const list = altCandidates(s, c);
    const idx = list.findIndex((p) => p.id === c.alternative?.providerId);
    const p = list[(idx + 1) % list.length];
    const q = p.quotes![assetOf(s, c).type]!;
    event(s, c, 'attempt', 'WhatsApp · simulated', `Asked ${p.name} for a quote, sharing the model and fault history.`);
    tick(s, 20);
    event(s, c, 'evidence', 'WhatsApp · simulated', `${p.name} quoted ${rupees(q.amount)}: ${q.note}.`, true, 'Quote, not a booking');
    providerLog(s, p.id, 'quoted', `Quoted ${rupees(q.amount)}`, c.id);
    c.alternative = { providerId: p.id, quote: q.amount, quoteNote: q.note, status: 'pending' };
    reconcileAlternative(s, c);
    const over = q.amount > s.settings.maxSpend;
    c.nextAction = over ? `Approve ${p.name} at ${rupees(q.amount)} (above your limit)` : `Book ${p.name}. ${rupees(q.amount)} is within your limit.`;
    return over ? `${p.name} quoted ${rupees(q.amount)}, which needs your approval.` : `${p.name} quoted ${rupees(q.amount)}, within your limit. Ready to book.`;
  });
}

export function approveAlternative(state: AppState, caseId: string): Result {
  const c0 = state.cases.find((c) => c.id === caseId);
  if (!c0) return { state };
  const gate = canApproveAlternative(state, c0);
  if (!gate.ok) return { state, toast: gate.reason };
  return edit(state, caseId, (s, c) => {
    const alt = c.alternative!;
    const p = s.providers.find((x) => x.id === alt.providerId)!;
    const over = alt.quote > s.settings.maxSpend;
    event(s, c, 'approval', 'App', over ? `You approved ${p.name} up to ${rupees(alt.quote)}.` : `Booked ${p.name}: ${rupees(alt.quote)} is within your ${rupees(s.settings.maxSpend)} limit.`, false);
    event(s, c, 'attempt', 'WhatsApp · simulated', `Booking request sent to ${p.name} for your allowed windows (${s.settings.windows.map((w) => WINDOW_LABEL[w].split(' ')[0].toLowerCase()).join(', ')}).`);
    tick(s, 25);
    const slot = nextSlot(s.clock, s.settings.days, s.settings.windows);
    event(s, c, 'confirmed', 'WhatsApp · simulated', `${p.name} confirmed ${windowText(slot.start, slot.end)}.`, true, 'Confirmed by the provider (simulated reply)');
    event(s, c, 'attempt', 'WhatsApp · simulated', `Told ${pName(s, c.originalProviderId)} to close ticket ${c.reference}: repair arranged elsewhere.`);
    providerLog(s, p.id, 'responded', `Booked for ${windowText(slot.start, slot.end)}`, c.id);
    alt.status = 'approved';
    dropApprovals(s, c.id, 'alt_spend');
    c.providerId = p.id;
    c.appointment = { start: slot.start, end: slot.end, providerId: p.id };
    c.expectedAmount = alt.quote;
    c.track = 'visit';
    c.step = 0;
    c.state = 'appointment_confirmed';
    c.waitingOn = 'provider';
    c.nextAction = `Day-of check with ${person(s, p.id)} before ${fmtTime(slot.start)}`;
    c.nextActionAt = addMinutes(slot.start, -45);
    activity(s, 'Waiting for the provider', `${p.name} booked for the geyser`, over ? 'You approved a quote above your limit.' : 'Quote within your pre-approved limit.', `${p.name} quote ${rupees(alt.quote)}`, `Visit ${windowText(slot.start, slot.end)} (simulated booking).`, { type: 'case', id: c.id }, c.nextAction);
    return `${p.name} booked for ${fmtDateTime(slot.start)} (simulated).`;
  });
}

// ---------- approvals ----------

export function resolveApproval(state: AppState, approvalId: string, approve: boolean): Result {
  const ap = state.approvals.find((a) => a.id === approvalId);
  if (!ap) return { state };
  if (ap.action === 'alt_spend' && approve) return approveAlternative(state, ap.caseId);
  return edit(state, ap.caseId, (s, c) => {
    s.approvals = s.approvals.filter((a) => a.id !== approvalId);
    switch (ap.action) {
      case 'alt_spend': {
        event(s, c, 'approval', 'App', `You declined ${pName(s, c.alternative!.providerId)} at ${rupees(c.alternative!.quote)}. Saathi keeps chasing ${pName(s, c.providerId)}.`, false);
        c.alternative!.status = 'declined';
        c.nextAction = `Keep chasing ${pName(s, c.providerId)}`;
        return 'Backup declined. Still chasing the centre.';
      }
      case 'slot': {
        const slot = ap.slot!;
        if (!approve) {
          event(s, c, 'approval', 'App', `You declined ${windowText(slot.start, slot.end)}.`, false);
          c.state = 'escalation';
          c.waitingOn = 'saathi';
          c.nextAction = 'Ask the manager for a different slot';
          c.nextActionAt = addMinutes(s.clock, 30);
          c.step = 2;
          return 'Slot declined. Saathi will ask for another.';
        }
        event(s, c, 'approval', 'App', `You confirmed ${windowText(slot.start, slot.end)}.`, false);
        event(s, c, 'confirmed', 'Email · simulated', `${pName(s, c.providerId)} confirmed the visit: ${windowText(slot.start, slot.end)}, job card JC-${c.reference?.slice(-4)}.`, true, 'Confirmed by the provider (simulated)');
        c.appointment = { start: slot.start, end: slot.end, providerId: c.providerId };
        c.expectedAmount = 1450;
        if (c.alternative?.status === 'pending') {
          c.alternative.status = 'declined';
          event(s, c, 'info', 'App', `Backup quote from ${pName(s, c.alternative.providerId)} put on hold.`);
        }
        dropApprovals(s, c.id, 'alt_spend');
        c.track = 'visit';
        c.step = 0;
        c.state = 'appointment_confirmed';
        c.waitingOn = 'provider';
        c.nextAction = `Day-of check with Mahesh before ${fmtTime(slot.start)}`;
        c.nextActionAt = addMinutes(slot.start, -45);
        return 'Visit confirmed (simulated).';
      }
      case 'access': {
        if (!approve) {
          event(s, c, 'approval', 'App', 'You declined entry. The visit is paused.', false);
          c.state = 'blocked';
          c.waitingOn = 'resident';
          c.nextAction = 'Run a follow-up to reschedule the visit';
          return 'Entry declined. Visit paused.';
        }
        event(s, c, 'approval', 'App', 'You confirmed someone is home.', false);
        event(s, c, 'arrival', 'Security desk log · simulated', `Technician entered at ${fmtTime(s.clock)}.`);
        providerLog(s, c.appointment!.providerId, 'kept', 'Arrived for the booked visit', c.id);
        c.arrived = true;
        c.state = 'repair_in_progress';
        c.waitingOn = 'provider';
        c.nextAction = "Wait for the technician's report";
        c.nextActionAt = addMinutes(s.clock, 60);
        c.step = 2;
        return 'Technician let in.';
      }
      case 'otp': {
        event(s, c, 'approval', 'App', approve ? 'You noted that you shared the closure OTP yourself, after checking the hot water.' : 'You are holding the closure OTP until the fix is verified.', false);
        return approve ? 'Noted. Saathi did not see the OTP.' : 'OTP held back.';
      }
      case 'service_spend': {
        const a = assetOf(s, c);
        if (!approve) {
          event(s, c, 'approval', 'App', 'You declined the quote. The service is on hold.', false);
          c.state = 'blocked';
          c.waitingOn = 'resident';
          c.nextAction = 'Change the rule or pick another provider';
          return 'Service on hold.';
        }
        event(s, c, 'approval', 'App', `You approved ${rupees(c.expectedAmount ?? 0)}.`, false);
        return confirmServiceBooking(s, c, a);
      }
      case 'amc_spend': {
        const a = assetOf(s, c);
        if (!approve) {
          event(s, c, 'approval', 'App', 'You chose not to renew.', false);
          c.state = 'completed';
          c.closedAt = s.clock;
          c.waitingOn = 'nobody';
          c.nextAction = '';
          c.outcome = { summary: 'Not renewed, by your choice', receipt: '—', amount: 0 };
          activity(s, 'Completed and saved', `${a.brand} AMC not renewed`, 'You declined the renewal.', 'Your decision in the app', 'Services after expiry will be paid visits.', { type: 'asset', id: a.id });
          return 'Renewal skipped.';
        }
        event(s, c, 'approval', 'App', `You approved renewal at ${rupees(a.amc!.cost)}.`, false);
        tick(s, 20);
        event(s, c, 'attempt', 'App · simulated', 'Asked Kent for a renewal payment link.');
        event(s, c, 'evidence', 'SMS · simulated', 'Payment link received. You pay through the link. Saathi never holds card or UPI details.', true, 'Link, not a payment');
        c.state = 'awaiting_verification';
        c.waitingOn = 'resident';
        c.nextAction = 'Pay through the link, then mark complete with the receipt';
        return 'Payment link ready. You pay; Saathi saves the receipt.';
      }
    }
    return undefined;
  });
}

// ---------- maintenance and triggers ----------

function confirmServiceBooking(s: AppState, c: Case, a: Asset): string {
  const rule = a.rule!;
  const p = pName(s, rule.providerId);
  const slot = nextSlot(s.clock, rule.days, [rule.window]);
  event(s, c, 'confirmed', 'WhatsApp · simulated', `${p} confirmed ${windowText(slot.start, slot.end)}. Simulated booking.`, true, 'Confirmed by the provider (simulated reply)');
  providerLog(s, rule.providerId, 'responded', `Booked for ${windowText(slot.start, slot.end)}`, c.id);
  c.appointment = { start: slot.start, end: slot.end, providerId: rule.providerId };
  c.track = 'visit';
  c.step = 0;
  c.state = 'appointment_confirmed';
  c.waitingOn = 'provider';
  c.nextAction = `Day-of check with ${person(s, rule.providerId)} before ${fmtTime(slot.start)}`;
  c.nextActionAt = addMinutes(slot.start, -45);
  return `${a.brand} ${a.name} service booked for ${fmtDateTime(slot.start)} (simulated).`;
}

function startService(s: AppState, a: Asset): string {
  const rule = a.rule!;
  const p = pName(s, rule.providerId);
  tick(s, 5);
  const last = [...a.history].reverse().find((h) => h.kind === 'service');
  const c: Case = {
    id: uid('case'), assetId: a.id, kind: 'service', title: `${a.brand} ${a.name}: ${rule.label.toLowerCase()}`, state: 'contacting_provider',
    reportedAt: s.clock, providerId: rule.providerId, originalProviderId: rule.providerId, track: 'visit', step: 0, followUps: 0, missed: 0,
    escalated: false, arrived: false, expectedAmount: rule.estCost, nextAction: '', waitingOn: 'provider', lastActionAt: s.clock, events: [],
  };
  s.cases.unshift(c);
  event(s, c, 'info', 'Trigger', `${rule.label} falls due ${fmtShort(nextDue(rule))} (every ${rule.intervalMonths} months). Nobody had to ask.`, false);
  event(s, c, 'memory', 'Ghar Ki Memory', last ? `Last service ${fmtShort(last.date)}${last.providerId ? ` by ${pName(s, last.providerId)}` : ''}${last.amount != null ? `, ${rupees(last.amount)}` : ''}. Preferred: ${p}, ${rule.days.join('/')} ${rule.window}s.` : `Preferred: ${p}.`, false);
  event(s, c, 'attempt', 'WhatsApp · simulated', `Asked ${p} for a ${rule.window} slot on ${rule.days.join('/')}. Expected cost ${rupees(rule.estCost)}.`);
  tick(s, 15);
  if (rule.estCost <= rule.maxCost) {
    const msg = confirmServiceBooking(s, c, a);
    activity(s, 'Handled automatically', `${a.brand} ${a.name} service booked`, `Due ${fmtShort(nextDue(rule))}; ${rupees(rule.estCost)} is within the ${rupees(rule.maxCost)} you pre-approved for this rule.`, `Rule + last service record`, msg, { type: 'case', id: c.id }, c.nextAction);
    return msg;
  }
  c.state = 'awaiting_approval';
  c.waitingOn = 'resident';
  c.nextAction = 'Approve the quote';
  approval(s, { caseId: c.id, action: 'service_spend', title: `Approve ${rupees(rule.estCost)} for ${a.brand} ${a.name} service?`, detail: `Above the ${rupees(rule.maxCost)} pre-approved for this rule.`, amount: rule.estCost });
  activity(s, 'Your approval needed', `${a.brand} ${a.name} service quote above the rule limit`, `${rupees(rule.estCost)} > ${rupees(rule.maxCost)}`, `${p} quote (simulated)`, 'Waiting for your approval.', { type: 'case', id: c.id });
  return 'Service quote is above the rule limit, so it needs your approval.';
}

function startRenewal(s: AppState, a: Asset): string {
  const amc = a.amc!;
  tick(s, 5);
  const c: Case = {
    id: uid('case'), assetId: a.id, kind: 'renewal', title: `${a.brand} AMC renewal`, state: 'awaiting_approval', reportedAt: s.clock,
    providerId: amc.providerId, originalProviderId: amc.providerId, track: 'visit', step: 0, followUps: 0, missed: 0, escalated: false,
    arrived: false, expectedAmount: amc.cost, nextAction: 'Approve the renewal amount', waitingOn: 'resident', lastActionAt: s.clock, events: [],
  };
  s.cases.unshift(c);
  event(s, c, 'info', 'Trigger', `AMC ${a.amc ? 'ends ' + fmtShort(amc.end) : ''}. Renewal prepared 30 days ahead.`, false);
  event(s, c, 'memory', 'Ghar Ki Memory', `Current contract: ${rupees(amc.cost)}/year, 3 filter services + parts. Membrane excluded.`, false);
  approval(s, { caseId: c.id, action: 'amc_spend', title: `Renew ${a.brand} AMC for ${rupees(amc.cost)}?`, detail: `Above your ${rupees(s.settings.maxSpend)} limit. Current AMC ends ${fmtShort(amc.end)}.`, amount: amc.cost });
  activity(s, 'Your approval needed', `${a.brand} AMC renewal prepared`, 'Contract ends within 30 days.', 'AMC contract', `${rupees(amc.cost)} renewal waiting for your approval.`, { type: 'case', id: c.id });
  return `${a.brand} AMC renewal prepared. Needs your approval.`;
}

export function runTrigger(state: AppState, triggerId?: string): Result {
  const list = pendingTriggers(state);
  const t = triggerId ? list.find((x) => x.id === triggerId) : list[0];
  if (!t) return { state, toast: 'Nothing is due right now. Saathi will keep watching.' };
  if (t.type === 'followup' && t.caseId) return runFollowUp(state, t.caseId);
  const s = structuredClone(state);
  const a = s.assets.find((x) => x.id === t.assetId)!;
  if (t.type === 'service') return { state: s, toast: startService(s, a) };
  if (t.type === 'amc') return { state: s, toast: startRenewal(s, a) };
  a.warrantyReminderSaved = true;
  tick(s, 2);
  const check = addMonths(a.warrantyEnd!, -1);
  activity(s, 'Handled automatically', `${a.brand} ${a.name} warranty end saved`, `Warranty ends ${fmtShort(a.warrantyEnd!)}.`, a.facts.find((f) => f.label.toLowerCase().includes('warranty'))?.sourceLabel ?? 'Invoice', `On ${fmtShort(check)}, Saathi will ask if anything feels off, so faults get reported while still covered.`, { type: 'asset', id: a.id });
  return { state: s, toast: `Warranty check saved for ${fmtShort(check)}.` };
}

export function bookServiceNow(state: AppState, assetId: string): Result {
  const t = pendingTriggers(state).find((x) => x.type === 'service' && x.assetId === assetId);
  if (t) return runTrigger(state, t.id);
  const s = structuredClone(state);
  const a = s.assets.find((x) => x.id === assetId);
  if (!a?.rule) return { state };
  if (s.cases.some((c) => c.assetId === assetId && c.kind === 'service' && c.state !== 'completed')) return { state, toast: 'A service is already being arranged.' };
  return { state: s, toast: startService(s, a) };
}

// ---------- completion ----------

export interface Completion {
  summary: string;
  receipt: string;
  amount: number;
  serviced: boolean;
}

export function completeCase(state: AppState, caseId: string, done: Completion): Result {
  return edit(state, caseId, (s, c) => {
    const a = assetOf(s, c);
    const providerId = c.appointment?.providerId ?? c.providerId;
    event(s, c, 'completed', 'App', `You confirmed: ${done.summary}. Receipt ${done.receipt || 'not provided'}, paid ${rupees(done.amount)}.`, false);
    c.state = 'completed';
    c.closedAt = s.clock;
    c.waitingOn = 'nobody';
    c.nextAction = '';
    c.nextActionAt = undefined;
    c.outcome = { summary: done.summary, receipt: done.receipt, amount: done.amount };
    dropApprovals(s, c.id);

    const fields: DocField[] = [
      { label: 'Work done', value: done.summary },
      { label: 'Amount paid', value: rupees(done.amount) },
      { label: 'Receipt no.', value: done.receipt || '—' },
    ];
    const doc: Doc = { id: uid('doc'), assetId: a.id, kind: 'service_receipt', title: `${c.kind === 'renewal' ? 'Renewal' : c.kind === 'repair' ? 'Repair' : 'Service'} receipt — ${pName(s, providerId)}`, issuer: pName(s, providerId), date: s.clock, fields, addedBy: 'resident' };
    s.docs.push(doc);
    a.history.push({ id: uid('h'), date: s.clock, kind: c.kind === 'renewal' ? 'renewal' : c.kind, title: done.summary, detail: `Case closed after ${c.followUps} follow-up${c.followUps === 1 ? '' : 's'}${c.missed ? `, ${c.missed} missed visit${c.missed === 1 ? '' : 's'}` : ''}.`, providerId, amount: done.amount, docId: doc.id });
    if (c.arrived) providerLog(s, providerId, 'kept', `Completed: ${done.summary}`, c.id);

    let next = '';
    if (c.kind === 'renewal' && a.amc) {
      a.amc = { ...a.amc, start: a.amc.end, end: addMonths(a.amc.end, 12), docId: doc.id };
      const f = a.facts.find((x) => x.label === 'AMC valid till');
      if (f) Object.assign(f, { value: fmtShort(a.amc.end) + ' ' + new Date(a.amc.end).getFullYear(), docId: doc.id, sourceLabel: 'Renewal receipt (entered by you)', confidence: 'resident' });
      next = `AMC now runs till ${fmtDate(a.amc.end)}.`;
    }
    if (a.rule && (c.kind === 'service' || done.serviced)) {
      a.rule.lastDone = s.clock;
      const f = a.facts.find((x) => x.label === 'Last service');
      if (f) Object.assign(f, { value: fmtShort(s.clock) + ' ' + new Date(s.clock).getFullYear(), docId: doc.id, sourceLabel: 'Service receipt (entered by you)', confidence: 'resident' });
      next = `Next ${a.rule.label.toLowerCase()}: ${fmtDate(nextDue(a.rule))}.`;
    }
    if (c.kind === 'repair') {
      a.partWarrantyEnd = addMonths(s.clock, 6);
      a.facts.push({ id: uid('f'), label: 'Repair part warranty till', value: `${fmtShort(a.partWarrantyEnd)} (6 months, per technician)`, docId: doc.id, sourceLabel: 'Stated by technician', confidence: 'needs_confirmation' });
      if (!next) next = a.rule ? `Next ${a.rule.label.toLowerCase()} stays ${fmtDate(nextDue(a.rule))}.` : '';
      next += ` Part warranty check saved for ${fmtDate(a.partWarrantyEnd)}.`;
    }
    activity(s, 'Completed and saved', `${c.title}: closed`, 'You confirmed the outcome with a receipt.', `Receipt ${done.receipt || '—'}, ${rupees(done.amount)}`, 'Saved to the asset history.', { type: 'asset', id: a.id }, next.trim() || undefined);
    return `Closed and saved. ${next}`.trim();
  });
}

// ---------- settings, rules, memory, providers ----------

export function updateSettings(state: AppState, patch: Partial<Settings>): Result {
  const s = structuredClone(state);
  s.settings = { ...s.settings, ...patch };
  for (const c of s.cases) reconcileAlternative(s, c);
  return { state: s };
}

export function updateRule(state: AppState, assetId: string, patch: Partial<MaintenanceRule>): Result {
  const s = structuredClone(state);
  const a = s.assets.find((x) => x.id === assetId);
  if (!a?.rule) return { state };
  a.rule = { ...a.rule, ...patch };
  return { state: s, toast: patch.intervalMonths ? `Next ${a.rule.label.toLowerCase()} recalculated: ${fmtDate(nextDue(a.rule))}` : undefined };
}

export function confirmFact(state: AppState, assetId: string, factId: string, value: string): Result {
  const s = structuredClone(state);
  const f = s.assets.find((a) => a.id === assetId)?.facts.find((x) => x.id === factId);
  if (!f) return { state };
  const changed = f.value !== value;
  Object.assign(f, { value, confidence: 'resident', sourceLabel: `${f.sourceLabel.split(' · ')[0]} · ${changed ? 'corrected' : 'confirmed'} by you` });
  return { state: s, toast: changed ? 'Corrected and saved.' : 'Confirmed.' };
}

export interface MemoryInput {
  assetId: string;
  kind: Doc['kind'];
  title: string;
  issuer: string;
  fields: (DocField & { confirmed: boolean })[];
  historyTitle?: string;
  amount?: number;
  providerId?: string;
}

export function addMemory(state: AppState, m: MemoryInput): Result {
  const s = structuredClone(state);
  const a = s.assets.find((x) => x.id === m.assetId);
  if (!a) return { state };
  const doc: Doc = { id: uid('doc'), assetId: a.id, kind: m.kind, title: m.title, issuer: m.issuer, date: s.clock, addedBy: 'resident', fields: m.fields.map(({ label, value }) => ({ label, value })) };
  s.docs.push(doc);
  const src = m.kind === 'message' ? 'Extracted from message' : m.kind === 'note' ? 'Your note' : 'Extracted from document';
  for (const f of m.fields) {
    a.facts.push({ id: uid('f'), label: f.label, value: f.value, docId: doc.id, sourceLabel: src, confidence: f.confirmed ? 'resident' : 'needs_confirmation' });
  }
  if (m.historyTitle) a.history.push({ id: uid('h'), date: s.clock, kind: m.kind === 'note' ? 'note' : 'service', title: m.historyTitle, providerId: m.providerId, amount: m.amount, docId: doc.id });
  if (m.providerId && !a.providerIds.includes(m.providerId)) a.providerIds.push(m.providerId);
  const unconfirmed = m.fields.filter((f) => !f.confirmed).length;
  activity(s, 'Handled automatically', `${m.title} saved to memory`, 'You shared it with Saathi.', m.title, `${m.fields.length} field${m.fields.length === 1 ? '' : 's'} saved to ${a.brand} ${a.name}${unconfirmed ? `; ${unconfirmed} marked "needs confirmation"` : ''}.`, { type: 'asset', id: a.id });
  return { state: s, toast: `Saved to ${a.brand} ${a.name}.` };
}

export function setProviderFlags(state: AppState, providerId: string, patch: { preferred?: boolean; backup?: boolean }): Result {
  const s = structuredClone(state);
  const p = s.providers.find((x) => x.id === providerId);
  if (!p) return { state };
  Object.assign(p, patch);
  return { state: s };
}

