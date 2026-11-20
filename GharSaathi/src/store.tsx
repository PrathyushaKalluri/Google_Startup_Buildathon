import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import type { AppState } from './types';
import { buildSeed, STATE_VERSION } from './data/seed';
import type { Result } from './logic/workflow';

const KEY = 'gharsaathi:state';

function load(): AppState {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as AppState;
      if (parsed.version === STATE_VERSION) return parsed;
    }
  } catch {
    /* storage unavailable: fall back to a fresh seed */
  }
  return buildSeed();
}

export type Screen = 'home' | 'memory' | 'work' | 'calendar' | 'providers';

export interface Route {
  screen: Screen;
  caseId?: string;
}

interface Toast {
  id: number;
  text: string;
}

interface Store {
  state: AppState;
  act: (fn: (s: AppState) => Result) => void;
  reset: () => void;
  route: Route;
  go: (r: Route) => void;
  assetDrawer: { id: string; tab?: string } | null;
  openAsset: (id: string | null, tab?: string) => void;
  providerDrawer: string | null;
  openProvider: (id: string | null) => void;
  source: { docId: string; field?: string } | null;
  openSource: (docId: string | null, field?: string) => void;
  panel: 'activity' | 'settings' | 'approvals' | 'memory' | null;
  setPanel: (p: Store['panel']) => void;
  toasts: Toast[];
  toast: (text: string) => void;
}

const Ctx = createContext<Store | null>(null);

function parseHash(): Route {
  const [screen, caseId] = window.location.hash.replace(/^#\/?/, '').split('/');
  const valid: Screen[] = ['home', 'memory', 'work', 'calendar', 'providers'];
  return { screen: valid.includes(screen as Screen) ? (screen as Screen) : 'home', caseId: caseId || undefined };
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(load);
  const ref = useRef(state);
  ref.current = state;
  const [route, setRoute] = useState<Route>(parseHash);
  const [assetDrawer, setAssetDrawer] = useState<Store['assetDrawer']>(null);
  const [providerDrawer, setProviderDrawer] = useState<string | null>(null);
  const [source, setSource] = useState<Store['source']>(null);
  const [panel, setPanel] = useState<Store['panel']>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch {
      /* ignore */
    }
  }, [state]);

  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const toast = useCallback((text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-2), { id, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);

  const act = useCallback(
    (fn: (s: AppState) => Result) => {
      const r = fn(ref.current);
      ref.current = r.state;
      setState(r.state);
      if (r.toast) toast(r.toast);
    },
    [toast],
  );

  const go = useCallback((r: Route) => {
    window.location.hash = `/${r.screen}${r.caseId ? '/' + r.caseId : ''}`;
    setRoute(r);
    setAssetDrawer(null);
    setProviderDrawer(null);
    setPanel(null);
    window.scrollTo({ top: 0 });
  }, []);

  const reset = useCallback(() => {
    const fresh = buildSeed();
    ref.current = fresh;
    setState(fresh);
    setAssetDrawer(null);
    setProviderDrawer(null);
    setSource(null);
    setPanel(null);
    window.location.hash = '/home';
    setRoute({ screen: 'home' });
    toast('Demo reset. Sharma Home is back to day two of the geyser saga.');
  }, [toast]);

  const value: Store = {
    state, act, reset, route, go,
    assetDrawer, openAsset: (id, tab) => setAssetDrawer(id ? { id, tab } : null),
    providerDrawer, openProvider: setProviderDrawer,
    source, openSource: (docId, field) => setSource(docId ? { docId, field } : null),
    panel, setPanel, toasts, toast,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore() {
  const s = useContext(Ctx);
  if (!s) throw new Error('useStore outside provider');
  return s;
}
