import { useEffect, type ReactNode } from 'react';
import { AlertTriangle, BadgeCheck, Bell, Brain, CalendarCheck, CheckCircle2, Clock, DoorOpen, FileSearch, Flag, HandCoins, MessageCircle, PhoneCall, Send, ShieldQuestion, Sparkles, UserRound, X } from 'lucide-react';
import type { ActivityLabel, CaseState, Confidence, EventKind } from '../types';
import { STATE_LABEL, STATE_TONE, type Tone } from '../logic/derive';

export const TONE_CLASS: Record<Tone, string> = {
  coral: 'bg-mirchi-soft text-mirchi-deep',
  teal: 'bg-peacock-soft text-peacock-deep',
  haldi: 'bg-haldi-soft text-ink',
  leaf: 'bg-leaf-soft text-leaf-deep',
  sand: 'bg-sand text-ink',
};

export function StateBadge({ state }: { state: CaseState }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${TONE_CLASS[STATE_TONE[state]]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {STATE_LABEL[state]}
    </span>
  );
}

const CONF: Record<Confidence, { text: string; cls: string; icon: ReactNode }> = {
  verified: { text: 'Verified from document', cls: 'bg-peacock-soft text-peacock-deep', icon: <BadgeCheck className="h-3.5 w-3.5" /> },
  extracted: { text: 'Extracted, not yet verified', cls: 'bg-haldi-soft text-ink', icon: <FileSearch className="h-3.5 w-3.5" /> },
  needs_confirmation: { text: 'Needs confirmation', cls: 'bg-mirchi-soft text-mirchi-deep', icon: <ShieldQuestion className="h-3.5 w-3.5" /> },
  resident: { text: 'Confirmed by you', cls: 'bg-leaf-soft text-leaf-deep', icon: <UserRound className="h-3.5 w-3.5" /> },
};

export function ConfidenceBadge({ c }: { c: Confidence }) {
  const x = CONF[c];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold ${x.cls}`}>
      {x.icon}
      {x.text}
    </span>
  );
}

const LABEL: Record<ActivityLabel, { cls: string; icon: ReactNode }> = {
  'Handled automatically': { cls: 'bg-peacock text-white', icon: <Sparkles className="h-3.5 w-3.5" /> },
  'Waiting for the provider': { cls: 'bg-haldi text-ink', icon: <Clock className="h-3.5 w-3.5" /> },
  'Your approval needed': { cls: 'bg-mirchi text-white', icon: <HandCoins className="h-3.5 w-3.5" /> },
  'Next follow-up queued': { cls: 'bg-sand text-ink', icon: <Send className="h-3.5 w-3.5" /> },
  'Completed and saved': { cls: 'bg-leaf text-white', icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
};

export function LabelChip({ label }: { label: ActivityLabel }) {
  const x = LABEL[label];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${x.cls}`}>
      {x.icon}
      {label}
    </span>
  );
}

export const EVENT_META: Record<EventKind, { label: string; icon: ReactNode; dot: string }> = {
  resident: { label: 'Reported by you', icon: <UserRound className="h-4 w-4" />, dot: 'bg-ink text-cream' },
  memory: { label: 'From memory', icon: <Brain className="h-4 w-4" />, dot: 'bg-haldi text-ink' },
  attempt: { label: 'Attempt', icon: <PhoneCall className="h-4 w-4" />, dot: 'bg-sand text-ink' },
  promise: { label: 'Provider promise', icon: <MessageCircle className="h-4 w-4" />, dot: 'bg-haldi-soft text-ink border border-dashed border-ink/50' },
  missed: { label: 'Missed commitment', icon: <AlertTriangle className="h-4 w-4" />, dot: 'bg-mirchi text-white' },
  confirmed: { label: 'Appointment confirmed', icon: <CalendarCheck className="h-4 w-4" />, dot: 'bg-peacock text-white' },
  arrival: { label: 'Technician arrived', icon: <DoorOpen className="h-4 w-4" />, dot: 'bg-peacock text-white' },
  evidence: { label: 'Evidence received', icon: <FileSearch className="h-4 w-4" />, dot: 'bg-peacock-soft text-peacock-deep' },
  approval: { label: 'Your decision', icon: <HandCoins className="h-4 w-4" />, dot: 'bg-ink text-cream' },
  escalation: { label: 'Escalation', icon: <Flag className="h-4 w-4" />, dot: 'bg-mirchi-deep text-white' },
  info: { label: 'Update', icon: <Bell className="h-4 w-4" />, dot: 'bg-cream text-ink border border-ink/30' },
  completed: { label: 'Verified complete', icon: <CheckCircle2 className="h-4 w-4" />, dot: 'bg-leaf text-white' },
};

export function Drawer({ open, onClose, title, children, wide = false }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
      <button aria-label="Close" className="absolute inset-0 bg-ink/30 backdrop-blur-[1px]" onClick={onClose} />
      <div className={`animate-slide-in relative flex h-full w-full flex-col bg-cream shadow-soft ${wide ? 'sm:max-w-2xl' : 'sm:max-w-md'}`}>
        <div className="flex items-start justify-between gap-3 border-b border-sand-deep/70 px-5 py-4">
          <div className="min-w-0 flex-1">{title}</div>
          <button onClick={onClose} className="rounded-full p-2 hover:bg-sand" aria-label="Close panel">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true">
      <button aria-label="Close" className="absolute inset-0 bg-ink/40" onClick={onClose} />
      <div className="animate-slide-up relative max-h-[92vh] w-full overflow-y-auto rounded-t-3xl border-2 border-ink bg-cream shadow-pop sm:max-w-lg sm:rounded-3xl">
        <div className="flex items-start justify-between gap-3 px-5 pb-2 pt-5">
          <div className="min-w-0 flex-1">{title}</div>
          <button onClick={onClose} className="rounded-full p-2 hover:bg-sand" aria-label="Close dialog">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-5 pb-5">{children}</div>
      </div>
    </div>
  );
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { id: T; label: string; count?: number }[] }) {
  return (
    <div className="no-scrollbar -mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="tablist">
      {items.map((it) => (
        <button
          key={it.id}
          role="tab"
          aria-selected={value === it.id}
          onClick={() => onChange(it.id)}
          className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-sm font-bold transition ${value === it.id ? 'bg-ink text-cream' : 'bg-white/70 text-ink hover:bg-sand'}`}
        >
          {it.label}
          {it.count != null && <span className={`ml-1.5 rounded-full px-1.5 text-xs ${value === it.id ? 'bg-haldi text-ink' : 'bg-sand'}`}>{it.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function SectionHead({ kicker, title, action }: { kicker?: string; title: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        {kicker && <div className="label mb-1">{kicker}</div>}
        <h2 className="text-2xl font-bold leading-tight sm:text-[28px]">{title}</h2>
      </div>
      {action}
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-7 w-12 flex-none rounded-full border-2 border-ink transition ${checked ? 'bg-peacock' : 'bg-sand'}`}
    >
      <span className={`absolute top-0.5 h-5 w-5 rounded-full border-2 border-ink bg-cream transition-all ${checked ? 'left-[22px]' : 'left-0.5'}`} />
    </button>
  );
}

export function DemoTag({ children = 'Simulated' }: { children?: ReactNode }) {
  return <span className="rounded-md border border-dashed border-ink/40 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-ink-soft">{children}</span>;
}
