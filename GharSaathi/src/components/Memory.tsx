import { useEffect, useState } from 'react';
import { FileUp, Loader2, MessageSquareText, NotebookPen, Sparkles } from 'lucide-react';
import { useStore } from '../store';
import type { DocKind } from '../types';
import { fmtDate } from '../logic/dates';
import { addMemory, type MemoryInput } from '../logic/workflow';
import { ConfidenceBadge, Modal } from './ui';

const KIND_LABEL: Record<DocKind, string> = {
  invoice: 'Invoice',
  warranty_card: 'Warranty card',
  service_receipt: 'Service receipt',
  message: 'Message',
  amc_contract: 'AMC contract',
  note: 'Note',
};

/** Shows the stored document behind a fact, styled like the paper it came from, with the cited field highlighted. */
export function SourceModal() {
  const { source, openSource, state } = useStore();
  const doc = state.docs.find((d) => d.id === source?.docId);
  if (!doc) return null;
  const asset = state.assets.find((a) => a.id === doc.assetId);
  const isMsg = doc.kind === 'message';
  const hit = (label: string) => {
    const f = source?.field?.toLowerCase() ?? '';
    const l = label.toLowerCase();
    return !!f && (f.includes(l) || l.includes(f.split(' ')[0]));
  };
  return (
    <Modal
      open
      onClose={() => openSource(null)}
      title={
        <div>
          <div className="label">Source · {KIND_LABEL[doc.kind]}</div>
          <div className="font-display text-xl font-bold leading-tight">{doc.title}</div>
        </div>
      }
    >
      {isMsg ? (
        <div className="rounded-2xl bg-[#E7F3EC] p-4">
          <div className="mb-2 text-xs font-bold text-leaf-deep">{doc.issuer} · WhatsApp</div>
          <div className="space-y-2">
            {doc.fields.map((f) => (
              <div key={f.label} className={`max-w-[90%] rounded-2xl rounded-tl-sm bg-white p-3 text-sm shadow-sm ${hit(f.label) ? 'ring-2 ring-haldi' : ''}`}>
                <div className="text-[10px] font-bold uppercase tracking-wider text-ink-soft">{f.label}</div>
                {f.value}
              </div>
            ))}
          </div>
          <div className="mt-2 text-right text-[11px] text-ink-soft">{fmtDate(doc.date)}</div>
        </div>
      ) : (
        <div className="relative rotate-[-0.6deg] rounded-sm border border-sand-deep bg-white p-5 font-mono text-sm shadow-soft">
          <div className="absolute right-4 top-4 rotate-6 rounded border-2 border-peacock px-2 py-0.5 text-[10px] font-bold uppercase text-peacock">{doc.addedBy === 'resident' ? 'Added by you' : 'Filed'}</div>
          <div className="font-sans text-xs font-bold uppercase tracking-widest text-ink-soft">{doc.issuer}</div>
          <div className="mt-1 font-sans text-xs text-ink-soft">{fmtDate(doc.date)}</div>
          <div className="my-3 border-t border-dashed border-ink/30" />
          <dl className="space-y-2">
            {doc.fields.map((f) => (
              <div key={f.label} className={`flex justify-between gap-4 rounded px-1 ${hit(f.label) ? 'bg-haldi-soft ring-1 ring-haldi' : ''}`}>
                <dt className="text-ink-soft">{f.label}</dt>
                <dd className="text-right font-bold">{f.value}</dd>
              </div>
            ))}
          </dl>
          <div className="my-3 border-t border-dashed border-ink/30" />
          <div className="font-sans text-[11px] text-ink-soft">Demo record. Fictional business details.</div>
        </div>
      )}
      <p className="mt-3 text-sm text-ink-soft">Linked to <b className="text-ink">{asset?.brand} {asset?.name}</b>. Facts taken from this document keep this as their source.</p>
    </Modal>
  );
}

type Mode = 'invoice' | 'message' | 'note';

interface Draft {
  assetId: string;
  title: string;
  issuer: string;
  kind: DocKind;
  fields: { label: string; value: string; confidence: 'extracted' | 'needs_confirmation'; confirmed: boolean }[];
  historyTitle?: string;
  amount?: number;
  providerId?: string;
}

const SAMPLE_MESSAGE = 'Madam, Yadagiri here. Flush tank valve changed in master bathroom. ₹380 only. Next time leak aithe direct call cheyandi.';

function extract(mode: Mode, text: string, assetId: string): Draft {
  if (mode === 'invoice') {
    return {
      assetId: 'fridge', kind: 'service_receipt', title: 'Samsung service receipt (photo)', issuer: 'Samsung Care', historyTitle: 'Door gasket replaced, gas checked', amount: 1850,
      fields: [
        { label: 'Service date', value: 'Last Saturday', confidence: 'extracted', confirmed: true },
        { label: 'Work done', value: 'Door gasket replaced, gas pressure checked', confidence: 'extracted', confirmed: true },
        { label: 'Amount paid', value: '₹1,850', confidence: 'extracted', confirmed: true },
        { label: 'Gasket warranty', value: '6 months?', confidence: 'needs_confirmation', confirmed: false },
      ],
    };
  }
  if (mode === 'message') {
    const amt = text.match(/₹\s?([\d,]+)/);
    const amount = amt ? Number(amt[1].replace(/,/g, '')) : undefined;
    return {
      assetId: 'plumbing', kind: 'message', title: 'WhatsApp from Yadagiri', issuer: 'Yadagiri (plumber)', historyTitle: 'Flush tank valve changed', amount, providerId: 'p-yadagiri',
      fields: [
        { label: 'Work done', value: /flush/i.test(text) ? 'Flush tank valve changed' : text.slice(0, 60), confidence: 'extracted', confirmed: true },
        { label: 'Amount', value: amount ? `₹${amount.toLocaleString('en-IN')}` : 'Not found in message', confidence: amount ? 'extracted' : 'needs_confirmation', confirmed: !!amount },
        { label: 'Plumber', value: 'Yadagiri', confidence: 'extracted', confirmed: true },
      ],
    };
  }
  return {
    assetId, kind: 'note', title: 'Note from you', issuer: 'You', historyTitle: text.slice(0, 70),
    fields: [{ label: 'Note', value: text, confidence: 'extracted', confirmed: true }],
  };
}

export function AddMemoryModal() {
  const { panel, setPanel, state, act } = useStore();
  const [mode, setMode] = useState<Mode>('invoice');
  const [text, setText] = useState(SAMPLE_MESSAGE);
  const [note, setNote] = useState('');
  const [noteAsset, setNoteAsset] = useState('ac');
  const [phase, setPhase] = useState<'pick' | 'processing' | 'review'>('pick');
  const [draft, setDraft] = useState<Draft | null>(null);

  useEffect(() => {
    if (panel === 'memory') {
      setPhase('pick');
      setDraft(null);
    }
  }, [panel]);

  if (panel !== 'memory') return null;
  const close = () => setPanel(null);

  const run = () => {
    setPhase('processing');
    const d = extract(mode, mode === 'note' ? note : text, noteAsset);
    setTimeout(() => {
      setDraft(d);
      setPhase('review');
    }, 1300);
  };

  const save = () => {
    if (!draft) return;
    const input: MemoryInput = {
      assetId: draft.assetId, kind: draft.kind, title: draft.title, issuer: draft.issuer, historyTitle: draft.historyTitle, amount: draft.amount, providerId: draft.providerId,
      fields: draft.fields.map((f) => ({ label: f.label, value: f.value, confirmed: f.confirmed })),
    };
    act((s) => addMemory(s, input));
    close();
  };

  return (
    <Modal
      open
      onClose={close}
      title={
        <div>
          <div className="label">Ghar Ki Memory</div>
          <div className="font-display text-xl font-bold">Add something to memory</div>
        </div>
      }
    >
      {phase === 'pick' && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-2">
            {([
              ['invoice', 'Upload a bill', <FileUp key="i" className="h-5 w-5" />],
              ['message', 'Share a message', <MessageSquareText key="m" className="h-5 w-5" />],
              ['note', 'Write a note', <NotebookPen key="n" className="h-5 w-5" />],
            ] as const).map(([id, label, icon]) => (
              <button key={id} onClick={() => setMode(id)} className={`flex flex-col items-center gap-1.5 rounded-2xl border-2 p-3 text-center text-sm font-bold ${mode === id ? 'border-ink bg-haldi shadow-pop' : 'border-sand-deep bg-white'}`} aria-pressed={mode === id}>
                {icon}
                {label}
              </button>
            ))}
          </div>
          {mode === 'invoice' && (
            <div className="rounded-2xl border-2 border-dashed border-ink/30 bg-white p-4 text-center">
              <div className="font-bold">IMG_20241102_samsung_receipt.jpg</div>
              <div className="text-sm text-ink-soft">Demo file · 1.2 MB · a photo of a service receipt</div>
              <p className="mt-2 text-xs text-ink-soft">The demo uses this sample instead of opening your files.</p>
            </div>
          )}
          {mode === 'message' && (
            <label className="block">
              <span className="label">Paste a WhatsApp or SMS</span>
              <textarea className="input mt-1 h-28" value={text} onChange={(e) => setText(e.target.value)} />
            </label>
          )}
          {mode === 'note' && (
            <div className="space-y-2">
              <label className="block">
                <span className="label">About</span>
                <select className="input mt-1" value={noteAsset} onChange={(e) => setNoteAsset(e.target.value)}>
                  {state.assets.map((a) => (
                    <option key={a.id} value={a.id}>{a.brand} {a.name}</option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="label">Note</span>
                <textarea className="input mt-1 h-24" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. AC makes a rattling sound on high speed" />
              </label>
            </div>
          )}
          <button className="btn-primary w-full" onClick={run} disabled={mode === 'note' ? !note.trim() : mode === 'message' ? !text.trim() : false}>
            <Sparkles className="h-4 w-4" /> Let Saathi read it
          </button>
        </div>
      )}
      {phase === 'processing' && (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-peacock" />
          <div className="font-display text-lg font-bold">Reading it carefully…</div>
          <p className="text-sm text-ink-soft">Finding the appliance, dates, amounts and who did the work.</p>
        </div>
      )}
      {phase === 'review' && draft && (
        <div className="space-y-3">
          <p className="text-sm text-ink-soft">Check what Saathi found. Anything you leave unticked is saved as <b>needs confirmation</b>, never as fact.</p>
          <label className="block">
            <span className="label">Save to</span>
            <select className="input mt-1" value={draft.assetId} onChange={(e) => setDraft({ ...draft, assetId: e.target.value })}>
              {state.assets.map((a) => (
                <option key={a.id} value={a.id}>{a.brand} {a.name} · {a.room}</option>
              ))}
            </select>
          </label>
          {draft.fields.map((f, i) => (
            <div key={f.label} className="rounded-2xl border border-sand-deep bg-white p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="label !text-[10px]">{f.label}</span>
                <ConfidenceBadge c={f.confirmed ? 'resident' : f.confidence} />
              </div>
              <input
                className="input mt-1"
                value={f.value}
                onChange={(e) => {
                  const fields = [...draft.fields];
                  fields[i] = { ...f, value: e.target.value };
                  setDraft({ ...draft, fields });
                }}
                aria-label={f.label}
              />
              <label className="mt-2 flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={f.confirmed}
                  onChange={(e) => {
                    const fields = [...draft.fields];
                    fields[i] = { ...f, confirmed: e.target.checked };
                    setDraft({ ...draft, fields });
                  }}
                  className="h-4 w-4 accent-peacock"
                />
                This looks right
              </label>
            </div>
          ))}
          <div className="flex gap-2">
            <button className="btn-ghost flex-1" onClick={() => setPhase('pick')}>Back</button>
            <button className="btn-primary flex-1" onClick={save}>Save to memory</button>
          </div>
        </div>
      )}
    </Modal>
  );
}
