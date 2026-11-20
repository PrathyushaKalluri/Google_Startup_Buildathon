import type { AppState, Asset, Case, CaseState, MaintenanceRule } from '../types';
import { addMonths, daysBetween } from './dates';

export const STATE_LABEL: Record<CaseState, string> = {
  issue_received: 'Issue received',
  checking_memory: 'Checking memory',
  contacting_provider: 'Contacting provider',
  awaiting_provider: 'Awaiting provider response',
  appointment_proposed: 'Appointment proposed',
  awaiting_approval: 'Awaiting your approval',
  appointment_confirmed: 'Appointment confirmed',
  technician_en_route: 'Technician en route',
  technician_missed: 'Technician missed appointment',
  escalation: 'Escalation in progress',
  repair_in_progress: 'Repair in progress',
  awaiting_verification: 'Awaiting your verification',
  completed: 'Completed',
  blocked: 'Blocked',
};

export type Tone = 'coral' | 'teal' | 'haldi' | 'leaf' | 'sand';

export const STATE_TONE: Record<CaseState, Tone> = {
  issue_received: 'sand',
  checking_memory: 'sand',
  contacting_provider: 'haldi',
  awaiting_provider: 'haldi',
  appointment_proposed: 'haldi',
  awaiting_approval: 'coral',
  appointment_confirmed: 'teal',
  technician_en_route: 'teal',
  technician_missed: 'coral',
  escalation: 'coral',
  repair_in_progress: 'teal',
  awaiting_verification: 'coral',
  completed: 'leaf',
  blocked: 'coral',
};

export const nextDue = (rule: MaintenanceRule) => addMonths(rule.lastDone, rule.intervalMonths);

export const isOpen = (c: Case) => c.state !== 'completed';

export const openCasesFor = (s: AppState, assetId: string) => s.cases.filter((c) => c.assetId === assetId && isOpen(c));

export const pendingApprovals = (s: AppState, caseId?: string) =>
  s.approvals.filter((a) => (caseId ? a.caseId === caseId : true));

/** Approvals that stop the case from moving until the resident answers. */
export const blockingApproval = (s: AppState, caseId: string) =>
  s.approvals.find((a) => a.caseId === caseId && ['slot', 'access', 'service_spend', 'amc_spend'].includes(a.action));

export interface Trigger {
  id: string;
  type: 'service' | 'amc' | 'warranty' | 'followup';
  assetId: string;
  caseId?: string;
  date: string;
  title: string;
  detail: string;
}

/** Work that saved rules and dates say should start now. Order: soonest first. */
export function pendingTriggers(s: AppState): Trigger[] {
  const out: Trigger[] = [];
  for (const a of s.assets) {
    if (a.rule) {
      const due = nextDue(a.rule);
      const days = daysBetween(s.clock, due);
      const hasCase = s.cases.some((c) => c.assetId === a.id && c.kind === 'service' && isOpen(c));
      if (days <= 7 && !hasCase) {
        out.push({ id: `t-svc-${a.id}`, type: 'service', assetId: a.id, date: due, title: `${a.brand} ${a.name}: ${a.rule.label.toLowerCase()} due`, detail: `Rule: every ${a.rule.intervalMonths} months. Saathi will book within your rules.` });
      }
    }
    if (a.amc) {
      const days = daysBetween(s.clock, a.amc.end);
      const hasCase = s.cases.some((c) => c.assetId === a.id && c.kind === 'renewal' && isOpen(c));
      if (days <= 30 && !hasCase) {
        out.push({ id: `t-amc-${a.id}`, type: 'amc', assetId: a.id, date: a.amc.end, title: `${a.brand} AMC renewal coming up`, detail: 'Saathi prepares the renewal and asks before paying.' });
      }
    }
    if (a.warrantyEnd && !a.warrantyReminderSaved && a.category === 'appliance') {
      const days = daysBetween(s.clock, a.warrantyEnd);
      if (days > 0 && days <= 100) {
        out.push({ id: `t-wty-${a.id}`, type: 'warranty', assetId: a.id, date: a.warrantyEnd, title: `${a.brand} ${a.name} warranty ending`, detail: 'Saathi saves a pre-expiry check so any fault gets reported while still covered.' });
      }
    }
  }
  if (s.settings.routineFollowUps) {
    for (const c of s.cases) {
      if (isOpen(c) && c.nextActionAt && c.waitingOn === 'provider' && new Date(c.nextActionAt) <= new Date(s.clock) && !blockingApproval(s, c.id)) {
        out.push({ id: `t-fu-${c.id}`, type: 'followup', assetId: c.assetId, caseId: c.id, date: c.nextActionAt, title: `Follow-up due: ${c.title}`, detail: c.nextAction });
      }
    }
  }
  return out.sort((x, y) => x.date.localeCompare(y.date));
}

export function upcomingMaintenance(s: AppState, withinDays: number) {
  return s.assets
    .filter((a): a is Asset & { rule: MaintenanceRule } => !!a.rule)
    .map((a) => ({ asset: a, due: nextDue(a.rule), days: daysBetween(s.clock, nextDue(a.rule)) }))
    .filter((x) => x.days <= withinDays)
    .sort((x, y) => x.days - y.days);
}

export function attentionContracts(s: AppState) {
  const items: { asset: Asset; kind: 'Warranty' | 'AMC'; end: string; days: number }[] = [];
  for (const a of s.assets) {
    if (a.warrantyEnd && a.category === 'appliance') {
      const days = daysBetween(s.clock, a.warrantyEnd);
      if (days >= 0 && days <= 100) items.push({ asset: a, kind: 'Warranty', end: a.warrantyEnd, days });
    }
    if (a.amc) {
      const days = daysBetween(s.clock, a.amc.end);
      if (days <= 45) items.push({ asset: a, kind: 'AMC', end: a.amc.end, days });
    }
  }
  return items.sort((x, y) => x.days - y.days);
}

export function stats(s: AppState) {
  const weekAgo = new Date(new Date(s.clock).getTime() - 7 * 86_400_000);
  const handled = s.activities.filter((a) => a.label === 'Handled automatically' && new Date(a.at) >= weekAgo).length;
  const chasing = s.cases.filter((c) => c.kind === 'repair' && isOpen(c)).length;
  const serviceCases = s.cases.filter((c) => c.kind === 'service' && isOpen(c));
  const dueRules = upcomingMaintenance(s, 14).filter((x) => !serviceCases.some((c) => c.assetId === x.asset.id));
  return {
    handled,
    chasing,
    upcoming: serviceCases.length + dueRules.length,
    assets: s.assets.length,
    active: s.cases.filter(isOpen).length,
    maintenance30: upcomingMaintenance(s, 30).length,
    contracts: attentionContracts(s).length,
    approvals: s.approvals.length,
  };
}

export const JOURNEY = ['Problem reported', 'Provider contacted', 'Visit missed', 'Escalation', 'Repair pending'] as const;

/** How far the repair has got along the five-step journey shown on the home screen (index of the current step). */
export function journeyIndex(c: Case): number {
  if (['repair_in_progress', 'awaiting_verification', 'completed', 'technician_en_route'].includes(c.state)) return 4;
  if (c.escalated || c.alternative?.status === 'approved' || c.track === 'visit') return c.state === 'appointment_confirmed' ? 4 : 3;
  if (c.missed > 0) return 2;
  if (['issue_received', 'checking_memory'].includes(c.state)) return 0;
  return 1;
}

export function honestStatus(s: AppState, c: Case): string {
  if (c.state === 'completed') return 'Repair verified and saved';
  const block = blockingApproval(s, c.id);
  if (block) return 'Waiting for your approval';
  if (c.state === 'awaiting_verification') return 'Waiting for you to confirm the fix';
  if (c.state === 'appointment_confirmed') return 'Visit confirmed (simulated)';
  if (c.state === 'technician_en_route') return 'Technician says he is on the way';
  if (c.state === 'escalation') return `Waiting on ${s.providers.find((p) => p.id === c.providerId)?.name ?? 'provider'} supervisor`;
  if (c.alternative?.status === 'pending' && s.approvals.some((a) => a.caseId === c.id && a.action === 'alt_spend')) return 'Chasing service centre · backup needs your OK';
  if (c.waitingOn === 'provider') return 'Chasing the provider';
  return 'Working on it';
}
