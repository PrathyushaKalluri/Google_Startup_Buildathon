import type { TimeWindow, Weekday } from '../types';

export const DAY = 86_400_000;

export const WEEKDAYS: Weekday[] = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export const WINDOW_HOURS: Record<TimeWindow, [number, number]> = {
  morning: [9, 12],
  afternoon: [13, 16],
  evening: [17, 20],
};

export const WINDOW_LABEL: Record<TimeWindow, string> = {
  morning: 'Morning (9–12)',
  afternoon: 'Afternoon (1–4)',
  evening: 'Evening (5–8)',
};

export function addMinutes(iso: string, n: number): string {
  return new Date(new Date(iso).getTime() + n * 60_000).toISOString();
}

export function addDays(iso: string, n: number): string {
  return new Date(new Date(iso).getTime() + n * DAY).toISOString();
}

export function addMonths(iso: string, n: number): string {
  const d = new Date(iso);
  const day = d.getDate();
  d.setDate(1);
  d.setMonth(d.getMonth() + n);
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  d.setDate(Math.min(day, last));
  return d.toISOString();
}

/** A date on the same day as `iso`, at the given local time. */
export function atTime(iso: string, h: number, m = 0): string {
  const d = new Date(iso);
  d.setHours(h, m, 0, 0);
  return d.toISOString();
}

function startOfDay(iso: string): number {
  const d = new Date(iso);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function daysBetween(from: string, to: string): number {
  return Math.round((startOfDay(to) - startOfDay(from)) / DAY);
}

export function sameDay(a: string, b: string): boolean {
  return startOfDay(a) === startOfDay(b);
}

export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

export const fmtShort = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

export const fmtDay = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });

export const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true }).toUpperCase();

export const fmtDateTime = (iso: string) => `${fmtDay(iso)}, ${fmtTime(iso)}`;

export const rupees = (n: number) => `₹${n.toLocaleString('en-IN')}`;

export function relTime(iso: string, clock: string): string {
  const diff = new Date(clock).getTime() - new Date(iso).getTime();
  const mins = Math.round(diff / 60_000);
  if (Math.abs(mins) < 2) return 'just now';
  if (mins > 0) {
    if (mins < 60) return `${mins} min ago`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours} hr ago`;
    const days = daysBetween(iso, clock);
    return days === 1 ? 'yesterday' : `${days} days ago`;
  }
  const ahead = -mins;
  if (ahead < 60) return `in ${ahead} min`;
  if (ahead < 24 * 60) return `in ${Math.round(ahead / 60)} hr`;
  const days = daysBetween(clock, iso);
  return days === 1 ? 'tomorrow' : `in ${days} days`;
}

export function dueText(days: number): string {
  if (days === 0) return 'due today';
  if (days === 1) return 'due tomorrow';
  if (days > 1) return `due in ${days} days`;
  return days === -1 ? '1 day overdue' : `${-days} days overdue`;
}

export function duration(from: string, to: string): string {
  const hours = Math.max(0, Math.round((new Date(to).getTime() - new Date(from).getTime()) / 3_600_000));
  if (hours < 24) return `${hours} hr`;
  const days = Math.floor(hours / 24);
  const rest = hours % 24;
  return rest ? `${days}d ${rest}h` : `${days} days`;
}

/** First slot on or after `from` (and at least 2 hours later) that falls on an allowed day and window. */
export function nextSlot(from: string, days: Weekday[], windows: TimeWindow[]): { start: string; end: string } {
  const order: TimeWindow[] = ['morning', 'afternoon', 'evening'];
  const allowed = order.filter((w) => windows.includes(w));
  const useWindows = allowed.length ? allowed : order;
  const useDays = days.length ? days : WEEKDAYS;
  const earliest = new Date(from).getTime() + 2 * 3_600_000;
  for (let i = 0; i < 21; i++) {
    const day = addDays(from, i);
    if (!useDays.includes(WEEKDAYS[new Date(day).getDay()])) continue;
    for (const w of useWindows) {
      const [h1, h2] = WINDOW_HOURS[w];
      const start = atTime(day, h1);
      if (new Date(start).getTime() >= earliest) return { start, end: atTime(day, h2) };
    }
  }
  return { start: atTime(addDays(from, 1), 10), end: atTime(addDays(from, 1), 12) };
}
