import { useState, type ReactNode } from 'react';
import { Bell, CalendarDays, ChevronDown, Home, ListChecks, RotateCcw, Settings2, Sparkles, Users, Warehouse, Check, Plus } from 'lucide-react';
import { useStore, type Screen } from '../store';
import { fmtDateTime } from '../logic/dates';
import { stats } from '../logic/derive';
import { Sparkle } from './Doodles';

export const NAV: { id: Screen; label: string; short: string; icon: ReactNode }[] = [
  { id: 'home', label: 'Aaj Ka Scene', short: 'Aaj', icon: <Home className="h-5 w-5" /> },
  { id: 'memory', label: 'Ghar Ki Memory', short: 'Memory', icon: <Warehouse className="h-5 w-5" /> },
  { id: 'work', label: 'Kaam Chal Raha Hai', short: 'Kaam', icon: <ListChecks className="h-5 w-5" /> },
  { id: 'calendar', label: 'Service Calendar', short: 'Calendar', icon: <CalendarDays className="h-5 w-5" /> },
  { id: 'providers', label: 'People & Providers', short: 'People', icon: <Users className="h-5 w-5" /> },
];

function HouseholdSwitcher() {
  const { state, toast } = useStore();
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 rounded-full border border-ink/15 bg-white/80 py-1.5 pl-1.5 pr-3 text-left hover:border-ink/40" aria-expanded={open}>
        <span className="grid h-8 w-8 place-items-center rounded-full bg-mirchi font-display text-sm font-bold text-white">S</span>
        <span className="leading-tight">
          <span className="block whitespace-nowrap text-sm font-bold">{state.household.name}</span>
          <span className="hidden whitespace-nowrap text-[11px] text-ink-soft sm:block">{state.household.city} · 2BHK</span>
        </span>
        <ChevronDown className="h-4 w-4 text-ink-soft" />
      </button>
      {open && (
        <>
          <button className="fixed inset-0 z-30 cursor-default" aria-label="Close menu" onClick={() => setOpen(false)} />
          <div className="animate-slide-up absolute left-0 z-40 mt-2 w-64 rounded-2xl border-2 border-ink bg-cream p-2 shadow-pop">
            <div className="flex items-center gap-2 rounded-xl bg-white p-2">
              <span className="grid h-8 w-8 place-items-center rounded-full bg-mirchi font-display text-sm font-bold text-white">S</span>
              <div className="flex-1 text-sm">
                <div className="font-bold">{state.household.name}</div>
                <div className="text-xs text-ink-soft">{state.household.society}</div>
              </div>
              <Check className="h-4 w-4 text-peacock" />
            </div>
            <button
              onClick={() => {
                setOpen(false);
                toast('Only one home in this demo. Adding a second home is coming later.');
              }}
              className="mt-1 flex w-full items-center gap-2 rounded-xl p-2 text-sm text-ink-soft hover:bg-sand"
            >
              <Plus className="h-4 w-4" /> Add another home
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const { route, go, state, setPanel, reset } = useStore();
  const st = stats(state);
  const [confirmReset, setConfirmReset] = useState(false);

  return (
    <div className="min-h-screen lg:pl-64">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-sand-deep/70 bg-tile bg-sand/60 lg:flex">
        <div className="px-6 pb-6 pt-7">
          <div className="flex items-center gap-2">
            <Sparkle className="h-7 w-7" />
            <span className="font-display text-[26px] font-black tracking-tight">GharSaathi</span>
          </div>
          <p className="mt-1 font-display text-sm italic text-ink-soft">Ghar ka kaam. Agent ke naam.</p>
        </div>
        <nav className="flex-1 space-y-1 px-3" aria-label="Main">
          {NAV.map((n) => {
            const active = route.screen === n.id;
            return (
              <button
                key={n.id}
                onClick={() => go({ screen: n.id })}
                className={`flex w-full items-center gap-3 rounded-2xl px-3.5 py-3 text-left text-[15px] font-bold transition ${active ? 'border-2 border-ink bg-haldi shadow-pop' : 'border-2 border-transparent hover:bg-cream/80'}`}
                aria-current={active ? 'page' : undefined}
              >
                {n.icon}
                <span className="flex-1">{n.label}</span>
                {n.id === 'work' && st.active > 0 && <span className={`rounded-full px-2 text-xs ${active ? 'bg-ink text-cream' : 'bg-mirchi text-white'}`}>{st.active}</span>}
              </button>
            );
          })}
        </nav>
        <div className="m-4 rounded-2xl border border-dashed border-ink/30 bg-cream/70 p-3 text-xs text-ink-soft">
          <div className="mb-1 flex items-center gap-1.5 font-bold text-ink">
            <span className="h-2 w-2 rounded-full bg-haldi-deep" /> Demo mode
          </div>
          Calls, WhatsApp messages and bookings here are simulated. No real person is contacted.
        </div>
      </aside>

      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-sand-deep/60 bg-cream/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2.5 sm:px-6">
          <div className="flex items-center gap-1.5 lg:hidden">
            <Sparkle className="h-6 w-6" />
          </div>
          <HouseholdSwitcher />
          <div className="ml-auto flex items-center gap-1.5">
            <div className="hidden items-center gap-2 rounded-full border border-dashed border-ink/40 px-3 py-1.5 text-xs md:flex" title="The demo runs on its own clock so a two-day story can play out in minutes">
              <span className="font-bold uppercase tracking-wider text-haldi-deep">Demo</span>
              <span className="text-ink-soft">{fmtDateTime(state.clock)}</span>
            </div>
            <button onClick={() => setConfirmReset(true)} className="rounded-full p-2.5 hover:bg-sand" aria-label="Reset demo data" title="Reset demo">
              <RotateCcw className="h-5 w-5" />
            </button>
            <button onClick={() => setPanel('activity')} className="rounded-full p-2.5 hover:bg-sand" aria-label="Agent activity" title="Agent activity">
              <Sparkles className="h-5 w-5" />
            </button>
            <button onClick={() => setPanel('settings')} className="rounded-full p-2.5 hover:bg-sand" aria-label="Household rules" title="Household rules">
              <Settings2 className="h-5 w-5" />
            </button>
            <button onClick={() => setPanel('approvals')} className="relative rounded-full border-2 border-ink bg-white p-2 hover:bg-haldi" aria-label={`Approvals and notifications, ${st.approvals} pending`}>
              <Bell className="h-5 w-5" />
              {st.approvals > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-mirchi px-1 text-[11px] font-bold text-white">{st.approvals}</span>}
            </button>
          </div>
        </div>
        <div className="flex items-center justify-center gap-2 border-t border-dashed border-ink/20 bg-haldi-soft/60 px-4 py-1 text-[11px] md:hidden">
          <span className="font-bold uppercase tracking-wider">Demo</span>
          <span className="text-ink-soft">{fmtDateTime(state.clock)} · simulated actions</span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-28 pt-6 sm:px-6 lg:pb-16">{children}</main>

      {/* Mobile bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-30 border-t-2 border-ink bg-cream lg:hidden" aria-label="Main">
        <div className="mx-auto grid max-w-lg grid-cols-5">
          {NAV.map((n) => {
            const active = route.screen === n.id;
            return (
              <button key={n.id} onClick={() => go({ screen: n.id })} className="relative flex flex-col items-center gap-0.5 py-2 text-[11px] font-bold" aria-current={active ? 'page' : undefined}>
                <span className={`grid h-8 w-12 place-items-center rounded-full transition ${active ? 'bg-haldi' : ''}`}>{n.icon}</span>
                {n.short}
                {n.id === 'work' && st.active > 0 && <span className="absolute right-3 top-1 h-2.5 w-2.5 rounded-full border-2 border-cream bg-mirchi" />}
              </button>
            );
          })}
        </div>
      </nav>

      {confirmReset && (
        <div className="fixed inset-0 z-[70] grid place-items-center p-4" role="dialog" aria-modal="true">
          <button className="absolute inset-0 bg-ink/40" aria-label="Cancel" onClick={() => setConfirmReset(false)} />
          <div className="animate-pop relative w-full max-w-sm rounded-3xl border-2 border-ink bg-cream p-5 shadow-pop">
            <h3 className="text-xl font-bold">Reset the demo?</h3>
            <p className="mt-1 text-sm text-ink-soft">Everything goes back to the start: the geyser is two days stuck, the AC service is due in four days.</p>
            <div className="mt-4 flex justify-end gap-2">
              <button className="btn-ghost" onClick={() => setConfirmReset(false)}>Cancel</button>
              <button className="btn-primary" onClick={() => { setConfirmReset(false); reset(); }}>Reset demo</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function Toasts() {
  const { toasts } = useStore();
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-24 z-[80] flex flex-col items-center gap-2 px-4 lg:bottom-6" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className="animate-slide-up pointer-events-auto flex max-w-md items-start gap-2 rounded-2xl border-2 border-ink bg-ink px-4 py-3 text-sm font-medium text-cream shadow-pop">
          <Sparkle className="mt-0.5 h-4 w-4 flex-none" />
          {t.text}
        </div>
      ))}
    </div>
  );
}
