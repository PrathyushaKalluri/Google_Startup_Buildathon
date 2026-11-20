import type { Activity, AppState, Asset, Case, Doc, Provider } from '../types';
import { addDays, addMonths, atTime, fmtShort } from '../logic/dates';

export const STATE_VERSION = 3;

/**
 * Builds the Sharma Home demo household relative to "now", so the story always reads as current:
 * the geyser was reported two days ago and the AC service is due in four days.
 */
export function buildSeed(): AppState {
  const base = atTime(new Date().toISOString(), 10, 20);
  const d = (days: number, h = 10, m = 0) => atTime(addDays(base, days), h, m);
  const mo = (months: number, days = 0) => addDays(addMonths(base, months), days);

  const acLastService = mo(-6, 4);
  const roLastService = d(-100, 11);

  const docs: Doc[] = [
    {
      id: 'doc-ac-invoice', assetId: 'ac', kind: 'invoice', title: 'Tax invoice — Voltas split AC', issuer: 'Reliance Digital, Kukatpally',
      date: mo(-19), addedBy: 'saathi',
      fields: [
        { label: 'Invoice no.', value: 'RD/HYD/24/118402' },
        { label: 'Product', value: 'Voltas 1.5T 5★ Inverter Split AC (185V)' },
        { label: 'Purchase date', value: fmtShort(mo(-19)) + ' ' + new Date(mo(-19)).getFullYear() },
        { label: 'Amount paid', value: '₹41,490' },
      ],
    },
    {
      id: 'doc-ac-warranty', assetId: 'ac', kind: 'warranty_card', title: 'Voltas warranty card', issuer: 'Voltas Ltd.',
      date: mo(-19), addedBy: 'saathi',
      fields: [
        { label: 'Comprehensive warranty', value: '1 year' },
        { label: 'Compressor warranty', value: '5 years' },
        { label: 'Serial no.', value: 'VLT185V-22K0931' },
      ],
    },
    {
      id: 'doc-ac-service', assetId: 'ac', kind: 'service_receipt', title: 'AC service receipt', issuer: 'CoolCare AC Services (Imran)',
      date: acLastService, addedBy: 'saathi',
      fields: [
        { label: 'Work done', value: 'Jet wash, filter clean, gas pressure check' },
        { label: 'Amount', value: '₹799' },
        { label: 'Technician', value: 'Imran Khan' },
      ],
    },
    {
      id: 'doc-geyser-invoice', assetId: 'geyser', kind: 'invoice', title: 'Invoice — Havells geyser', issuer: 'Vijay Sales, Madhapur',
      date: mo(-35), addedBy: 'saathi',
      fields: [
        { label: 'Invoice no.', value: 'VS-MDP-23-77310' },
        { label: 'Product', value: 'Havells Monza EC 15L storage geyser' },
        { label: 'Amount paid', value: '₹9,190' },
      ],
    },
    {
      id: 'doc-geyser-warranty', assetId: 'geyser', kind: 'warranty_card', title: 'Havells warranty card', issuer: 'Havells India',
      date: mo(-35), addedBy: 'saathi',
      fields: [
        { label: 'Product warranty', value: '2 years' },
        { label: 'Inner tank warranty', value: '5 years' },
      ],
    },
    {
      id: 'doc-geyser-element', assetId: 'geyser', kind: 'service_receipt', title: 'Repair receipt — heating element', issuer: 'Havells Care (Mahesh)',
      date: mo(-14), addedBy: 'saathi',
      fields: [
        { label: 'Work done', value: 'Heating element replaced' },
        { label: 'Amount', value: '₹1,100' },
        { label: 'Part warranty', value: '12 months' },
        { label: 'Technician', value: 'Mahesh' },
      ],
    },
    {
      id: 'doc-geyser-descale', assetId: 'geyser', kind: 'service_receipt', title: 'Service receipt — descaling', issuer: 'Havells Care',
      date: mo(-9), addedBy: 'saathi',
      fields: [
        { label: 'Work done', value: 'Tank descaling, anode check' },
        { label: 'Amount', value: '₹450' },
      ],
    },
    {
      id: 'doc-ro-amc', assetId: 'ro', kind: 'amc_contract', title: 'Kent annual maintenance contract', issuer: 'Kent RO Systems',
      date: mo(-12, 25), addedBy: 'saathi',
      fields: [
        { label: 'Contract no.', value: 'KENT-AMC-HYD-20931' },
        { label: 'Cover', value: '3 filter services + parts (excl. membrane)' },
        { label: 'Fee', value: '₹2,400 / year' },
        { label: 'Valid till', value: fmtShort(d(25)) + ' ' + new Date(d(25)).getFullYear() },
      ],
    },
    {
      id: 'doc-ro-service', assetId: 'ro', kind: 'service_receipt', title: 'Kent service receipt #KS-55120', issuer: 'Kent RO service',
      date: roLastService, addedBy: 'saathi',
      fields: [
        { label: 'Work done', value: 'Sediment + carbon filter replaced (AMC)' },
        { label: 'Amount', value: '₹0 (covered by AMC)' },
        { label: 'Next service', value: 'In about 4 months' },
      ],
    },
    {
      id: 'doc-wm-invoice', assetId: 'washer', kind: 'invoice', title: 'Invoice — LG washing machine', issuer: 'Croma, Inorbit Mall',
      date: mo(-21), addedBy: 'saathi',
      fields: [
        { label: 'Product', value: 'LG 7kg Front Load (FHM1207)' },
        { label: 'Amount paid', value: '₹32,990' },
        { label: 'Warranty', value: '2 years comprehensive, 10 years motor' },
      ],
    },
    {
      id: 'doc-fridge-invoice', assetId: 'fridge', kind: 'invoice', title: 'Invoice photo — Samsung fridge (blurry)', issuer: 'Sri Lakshmi Electronics',
      date: mo(-40), addedBy: 'saathi',
      fields: [
        { label: 'Product', value: 'Samsung 253L Double Door' },
        { label: 'Amount paid', value: '₹24,?50 (unclear)' },
      ],
    },
    {
      id: 'doc-plumbing-msg', assetId: 'plumbing', kind: 'message', title: 'WhatsApp from Yadagiri', issuer: 'Yadagiri (plumber)',
      date: mo(-2), addedBy: 'saathi',
      fields: [
        { label: 'Message', value: '"Basin pipe joint changed madam, leak stopped. ₹650 GPay cheyandi."' },
        { label: 'Amount', value: '₹650' },
      ],
    },
    {
      id: 'doc-lighting-bill', assetId: 'lighting', kind: 'message', title: 'WhatsApp bill from Ravi', issuer: 'Ravi Electricals',
      date: d(-5, 17), addedBy: 'saathi',
      fields: [
        { label: 'Work done', value: 'Kitchen LED panel + driver replaced' },
        { label: 'Amount', value: '₹420' },
      ],
    },
  ];

  const assets: Asset[] = [
    {
      id: 'ac', name: 'Split AC', brand: 'Voltas', type: 'ac', category: 'appliance', model: '1.5T 5★ Inverter (185V)', room: 'Master bedroom',
      purchaseDate: mo(-19), warrantyEnd: mo(41), warrantyNote: 'Comprehensive cover ended; compressor covered for 5 years',
      rule: { label: 'Preventive service', intervalMonths: 6, providerId: 'p-coolcare', days: ['Sat', 'Sun'], window: 'morning', maxCost: 1200, estCost: 799, lastDone: acLastService },
      providerIds: ['p-coolcare', 'p-voltas'],
      facts: [
        { id: 'f-ac-1', label: 'Purchase date', value: '', docId: 'doc-ac-invoice', sourceLabel: 'Extracted from invoice', confidence: 'verified' },
        { id: 'f-ac-2', label: 'Compressor warranty till', value: '', docId: 'doc-ac-warranty', sourceLabel: 'Warranty card', confidence: 'verified' },
        { id: 'f-ac-3', label: 'Last service', value: '', docId: 'doc-ac-service', sourceLabel: 'Service receipt', confidence: 'verified' },
        { id: 'f-ac-4', label: 'Preferred technician', value: 'Imran Khan, CoolCare', docId: 'doc-ac-service', sourceLabel: 'Previous service record', confidence: 'verified' },
      ],
      history: [
        { id: 'h-ac-1', date: mo(-19), kind: 'purchase', title: 'Bought from Reliance Digital', detail: 'Invoice RD/HYD/24/118402', amount: 41490, docId: 'doc-ac-invoice' },
        { id: 'h-ac-2', date: mo(-19, 2), kind: 'install', title: 'Installed by Voltas', detail: 'Free installation, copper pipe 3m', providerId: 'p-voltas' },
        { id: 'h-ac-3', date: mo(-12, 6), kind: 'service', title: 'Free service under warranty', detail: 'Filter clean, gas check', providerId: 'p-voltas', amount: 0 },
        { id: 'h-ac-4', date: acLastService, kind: 'service', title: 'Preventive service by Imran', detail: 'Jet wash, filter clean, gas pressure normal', providerId: 'p-coolcare', amount: 799, docId: 'doc-ac-service' },
      ],
    },
    {
      id: 'geyser', name: 'Storage geyser', brand: 'Havells', type: 'geyser', category: 'appliance', model: 'Monza EC 15L', room: 'Common bathroom',
      purchaseDate: mo(-35), warrantyEnd: mo(25), warrantyNote: 'Product warranty ended; inner tank covered for 5 years',
      partWarrantyEnd: mo(-2),
      rule: { label: 'Annual descaling', intervalMonths: 12, providerId: 'p-havells', days: ['Sat', 'Sun'], window: 'morning', maxCost: 600, estCost: 450, lastDone: mo(-9) },
      providerIds: ['p-havells', 'p-srisai', 'p-ravi'],
      facts: [
        { id: 'f-gy-1', label: 'Purchase date', value: '', docId: 'doc-geyser-invoice', sourceLabel: 'Extracted from invoice', confidence: 'verified' },
        { id: 'f-gy-2', label: 'Inner tank warranty till', value: '', docId: 'doc-geyser-warranty', sourceLabel: 'Warranty card', confidence: 'verified' },
        { id: 'f-gy-3', label: 'Element part warranty', value: 'Ended 2 months ago', docId: 'doc-geyser-element', sourceLabel: 'Repair receipt', confidence: 'verified' },
        { id: 'f-gy-4', label: 'Last technician', value: 'Mahesh, Havells Care', docId: 'doc-geyser-element', sourceLabel: 'Previous service record', confidence: 'verified' },
      ],
      history: [
        { id: 'h-gy-1', date: mo(-35), kind: 'purchase', title: 'Bought from Vijay Sales', amount: 9190, docId: 'doc-geyser-invoice' },
        { id: 'h-gy-2', date: mo(-35, 3), kind: 'install', title: 'Installed by Havells', providerId: 'p-havells' },
        { id: 'h-gy-3', date: mo(-14), kind: 'repair', title: 'Heating element replaced', detail: 'Technician Mahesh. Part warranty 12 months.', providerId: 'p-havells', amount: 1100, docId: 'doc-geyser-element' },
        { id: 'h-gy-4', date: mo(-9), kind: 'service', title: 'Tank descaled', detail: 'Anode rod checked, still fine', providerId: 'p-havells', amount: 450, docId: 'doc-geyser-descale' },
      ],
    },
    {
      id: 'ro', name: 'RO water purifier', brand: 'Kent', type: 'ro', category: 'appliance', model: 'Grand Plus', room: 'Kitchen',
      purchaseDate: mo(-26), warrantyEnd: mo(-14), warrantyNote: 'Product warranty ended; covered by Kent AMC',
      amc: { providerId: 'p-kent', start: mo(-12, 25), end: d(25), cost: 2400, docId: 'doc-ro-amc' },
      rule: { label: 'Filter service (AMC)', intervalMonths: 4, providerId: 'p-kent', days: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], window: 'morning', maxCost: 0, estCost: 0, lastDone: roLastService },
      providerIds: ['p-kent'],
      facts: [
        { id: 'f-ro-1', label: 'AMC valid till', value: '', docId: 'doc-ro-amc', sourceLabel: 'AMC contract', confidence: 'verified' },
        { id: 'f-ro-2', label: 'Last service', value: '', docId: 'doc-ro-service', sourceLabel: 'Service receipt photo', confidence: 'verified' },
        { id: 'f-ro-3', label: 'Membrane covered by AMC?', value: 'No (excluded)', docId: 'doc-ro-amc', sourceLabel: 'Extracted from AMC contract', confidence: 'extracted' },
      ],
      history: [
        { id: 'h-ro-1', date: mo(-26), kind: 'purchase', title: 'Bought from Kent dealer', amount: 18500 },
        { id: 'h-ro-2', date: mo(-12, 25), kind: 'renewal', title: 'AMC started', detail: '₹2,400 / year', providerId: 'p-kent', amount: 2400, docId: 'doc-ro-amc' },
        { id: 'h-ro-3', date: d(-222), kind: 'service', title: 'Filter service (AMC)', providerId: 'p-kent', amount: 0 },
        { id: 'h-ro-4', date: roLastService, kind: 'service', title: 'Sediment + carbon filters replaced', detail: 'Receipt #KS-55120', providerId: 'p-kent', amount: 0, docId: 'doc-ro-service' },
      ],
    },
    {
      id: 'washer', name: 'Washing machine', brand: 'LG', type: 'washer', category: 'appliance', model: '7kg Front Load (FHM1207)', room: 'Utility balcony',
      purchaseDate: mo(-21), warrantyEnd: mo(3), warrantyNote: '2-year comprehensive warranty; motor covered 10 years',
      providerIds: ['p-lg', 'p-srisai'],
      facts: [
        { id: 'f-wm-1', label: 'Purchase date', value: '', docId: 'doc-wm-invoice', sourceLabel: 'Extracted from invoice', confidence: 'verified' },
        { id: 'f-wm-2', label: 'Comprehensive warranty till', value: '', docId: 'doc-wm-invoice', sourceLabel: 'Extracted from invoice', confidence: 'extracted' },
      ],
      history: [
        { id: 'h-wm-1', date: mo(-21), kind: 'purchase', title: 'Bought from Croma', amount: 32990, docId: 'doc-wm-invoice' },
        { id: 'h-wm-2', date: mo(-8), kind: 'repair', title: 'Drain pump cleared (warranty)', detail: 'Coin stuck in filter', providerId: 'p-lg', amount: 0 },
      ],
    },
    {
      id: 'fridge', name: 'Refrigerator', brand: 'Samsung', type: 'fridge', category: 'appliance', model: '253L Double Door', room: 'Kitchen',
      purchaseDate: mo(-40), warrantyEnd: mo(80), warrantyNote: 'Product warranty ended; compressor covered 10 years',
      providerIds: ['p-samsung'],
      facts: [
        { id: 'f-fr-1', label: 'Purchase date', value: '', docId: 'doc-fridge-invoice', sourceLabel: 'Extracted from invoice photo', confidence: 'extracted' },
        { id: 'f-fr-2', label: 'Purchase price', value: '₹24,?50 — digit unreadable', docId: 'doc-fridge-invoice', sourceLabel: 'Extracted from invoice photo', confidence: 'needs_confirmation' },
      ],
      history: [{ id: 'h-fr-1', date: mo(-40), kind: 'purchase', title: 'Bought from Sri Lakshmi Electronics', docId: 'doc-fridge-invoice' }],
    },
    {
      id: 'plumbing', name: 'Bathroom plumbing', brand: 'Master bath', type: 'plumbing', category: 'fixture', model: 'Basin, taps, flush', room: 'Master bathroom',
      warrantyNote: 'No warranty — fixtures',
      providerIds: ['p-yadagiri', 'p-society'],
      facts: [{ id: 'f-pl-1', label: 'Last plumber', value: 'Yadagiri', docId: 'doc-plumbing-msg', sourceLabel: 'Extracted from message', confidence: 'extracted' }],
      history: [{ id: 'h-pl-1', date: mo(-2), kind: 'repair', title: 'Leak under wash basin fixed', detail: 'Pipe joint replaced', providerId: 'p-yadagiri', amount: 650, docId: 'doc-plumbing-msg' }],
    },
    {
      id: 'lighting', name: 'Kitchen lighting', brand: 'Wipro LED panel', type: 'lighting', category: 'fixture', model: '15W ceiling panel', room: 'Kitchen',
      warrantyNote: 'Panel has 1-year shop warranty (unconfirmed)',
      providerIds: ['p-ravi'],
      facts: [
        { id: 'f-li-1', label: 'Electrician', value: 'Ravi, Ravi Electricals', docId: 'doc-lighting-bill', sourceLabel: 'Extracted from message', confidence: 'extracted' },
        { id: 'f-li-2', label: 'Panel warranty', value: '1 year from shop?', docId: 'doc-lighting-bill', sourceLabel: 'Mentioned in message', confidence: 'needs_confirmation' },
      ],
      history: [{ id: 'h-li-1', date: d(-5, 17), kind: 'repair', title: 'LED panel + driver replaced', providerId: 'p-ravi', amount: 420, docId: 'doc-lighting-bill' }],
    },
  ];

  // Facts with an empty value are filled from the dates above, so they never drift from the record.
  const fill: Record<string, string> = {
    'f-ac-1': fmtShort(mo(-19)) + ' ' + new Date(mo(-19)).getFullYear(),
    'f-ac-2': fmtShort(mo(41)) + ' ' + new Date(mo(41)).getFullYear(),
    'f-ac-3': fmtShort(acLastService) + ' ' + new Date(acLastService).getFullYear(),
    'f-gy-1': fmtShort(mo(-35)) + ' ' + new Date(mo(-35)).getFullYear(),
    'f-gy-2': fmtShort(mo(25)) + ' ' + new Date(mo(25)).getFullYear(),
    'f-ro-1': fmtShort(d(25)) + ' ' + new Date(d(25)).getFullYear(),
    'f-ro-2': fmtShort(roLastService) + ' ' + new Date(roLastService).getFullYear(),
    'f-wm-1': fmtShort(mo(-21)) + ' ' + new Date(mo(-21)).getFullYear(),
    'f-wm-2': fmtShort(mo(3)) + ' ' + new Date(mo(3)).getFullYear(),
    'f-fr-1': fmtShort(mo(-40)) + ' ' + new Date(mo(-40)).getFullYear(),
  };
  for (const a of assets) for (const f of a.facts) if (!f.value) f.value = fill[f.id] ?? '—';

  const providers: Provider[] = [
    {
      id: 'p-havells', name: 'Havells Care', contactPerson: 'Service centre, Madhapur', category: 'Brand service centre', kind: 'brand_centre',
      phone: '+91 90000 10001', channel: 'Helpline + WhatsApp', preferred: true, backup: false, typicalCost: '₹400 visit + parts',
      assetIds: ['geyser'], handles: ['geyser'],
      log: [
        { id: 'pl-1', date: mo(-14), text: 'Replaced heating element (Mahesh). Arrived on time.', outcome: 'kept' },
        { id: 'pl-2', date: mo(-9), text: 'Descaling visit, on time.', outcome: 'kept' },
        { id: 'pl-3', date: d(-2, 10, 45), text: 'Missed "10 minutes" promise', outcome: 'missed', caseId: 'case-geyser' },
        { id: 'pl-4', date: d(-2, 15, 30), text: 'Missed "by 3 PM" promise', outcome: 'missed', caseId: 'case-geyser' },
        { id: 'pl-5', date: d(-1, 13, 10), text: 'Missed 11–1 window', outcome: 'missed', caseId: 'case-geyser' },
      ],
    },
    {
      id: 'p-coolcare', name: 'CoolCare AC Services', contactPerson: 'Imran Khan', category: 'AC technician', kind: 'individual',
      phone: '+91 90000 10002', channel: 'WhatsApp', preferred: true, backup: false, typicalCost: '₹699–₹899 per service',
      assetIds: ['ac'], handles: ['ac'],
      log: [{ id: 'pl-6', date: acLastService, text: 'AC service, ₹799. Arrived in the agreed window.', outcome: 'kept' }],
    },
    {
      id: 'p-voltas', name: 'Voltas Service', contactPerson: 'Authorised centre, Kukatpally', category: 'Brand service centre', kind: 'brand_centre',
      phone: '+91 90000 10003', channel: 'Helpline', preferred: false, backup: true, typicalCost: '₹499 visit (out of warranty)',
      assetIds: ['ac'], handles: ['ac'],
      log: [
        { id: 'pl-7', date: mo(-19, 2), text: 'Installation', outcome: 'kept' },
        { id: 'pl-8', date: mo(-12, 6), text: 'Free warranty service — came a day late', outcome: 'missed' },
      ],
    },
    {
      id: 'p-kent', name: 'Kent RO Service', contactPerson: 'AMC desk', category: 'Brand service centre', kind: 'brand_centre',
      phone: '+91 90000 10004', channel: 'App + helpline', preferred: true, backup: false, typicalCost: 'Covered by AMC',
      assetIds: ['ro'], handles: ['ro'],
      log: [{ id: 'pl-9', date: roLastService, text: 'Filter service under AMC', outcome: 'kept' }],
    },
    {
      id: 'p-srisai', name: 'Sri Sai Appliance Care', contactPerson: 'Narsimha', category: 'Appliance technician', kind: 'individual',
      phone: '+91 90000 10005', channel: 'WhatsApp', preferred: false, backup: true, typicalCost: '₹350 visit + parts',
      assetIds: ['geyser', 'washer'], handles: ['geyser', 'washer', 'fridge'],
      quotes: { geyser: { amount: 1850, note: '₹350 visit + thermostat ₹1,500 (estimate before inspection)' } },
      log: [
        { id: 'pl-10', date: mo(-30), text: 'Fixed washing machine inlet valve at previous flat', outcome: 'kept' },
        { id: 'pl-11', date: d(-1, 13, 20), text: 'Quoted ₹1,850 for geyser thermostat', outcome: 'quoted', caseId: 'case-geyser' },
      ],
    },
    {
      id: 'p-ravi', name: 'Ravi Electricals', contactPerson: 'Ravi', category: 'Electrician', kind: 'individual',
      phone: '+91 90000 10006', channel: 'WhatsApp + call', preferred: true, backup: true, typicalCost: '₹300–₹500 small jobs',
      assetIds: ['lighting'], handles: ['lighting', 'geyser'],
      quotes: { geyser: { amount: 1350, note: '₹300 visit + thermostat ₹1,050 (Havells-compatible part)' } },
      log: [{ id: 'pl-12', date: d(-5, 17), text: 'Kitchen LED panel replaced, ₹420. Came same evening.', outcome: 'kept' }],
    },
    {
      id: 'p-yadagiri', name: 'Yadagiri', contactPerson: 'Plumber', category: 'Plumber', kind: 'individual',
      phone: '+91 90000 10007', channel: 'Call', preferred: true, backup: false, typicalCost: '₹300–₹700',
      assetIds: ['plumbing'], handles: ['plumbing'],
      log: [{ id: 'pl-13', date: mo(-2), text: 'Basin leak fixed, ₹650', outcome: 'kept' }],
    },
    {
      id: 'p-society', name: 'Gulmohar Residency office', contactPerson: 'Venkat (supervisor) + security desk', category: 'Apartment maintenance', kind: 'society',
      phone: '+91 90000 10008', channel: 'Society WhatsApp group + intercom', preferred: false, backup: true,
      assetIds: ['plumbing'], handles: ['plumbing', 'lighting'],
      log: [{ id: 'pl-14', date: mo(-3), text: 'Common water line repair notice shared', outcome: 'responded' }],
    },
    {
      id: 'p-lg', name: 'LG Service', contactPerson: 'Authorised centre', category: 'Brand service centre', kind: 'brand_centre',
      phone: '+91 90000 10009', channel: 'Helpline + app', preferred: true, backup: false, typicalCost: 'Free in warranty',
      assetIds: ['washer'], handles: ['washer'],
      log: [{ id: 'pl-15', date: mo(-8), text: 'Drain pump cleared under warranty', outcome: 'kept' }],
    },
    {
      id: 'p-samsung', name: 'Samsung Care', contactPerson: 'Authorised centre', category: 'Brand service centre', kind: 'brand_centre',
      phone: '+91 90000 10010', channel: 'Helpline', preferred: true, backup: false,
      assetIds: ['fridge'], handles: ['fridge'], log: [],
    },
  ];

  const geyserCase: Case = {
    id: 'case-geyser', assetId: 'geyser', kind: 'repair', title: 'Geyser not heating', state: 'technician_missed',
    reportedAt: d(-2, 7, 42), providerId: 'p-havells', originalProviderId: 'p-havells', reference: 'HVL-HYD-482917',
    track: 'primary', step: 0, followUps: 4, missed: 3, escalated: false, arrived: false,
    alternative: { providerId: 'p-srisai', quote: 1850, quoteNote: '₹350 visit + thermostat ₹1,500 (estimate before inspection)', status: 'pending' },
    nextAction: 'Follow up with Havells Care again at 11:00 AM', nextActionAt: d(0, 11), waitingOn: 'provider',
    lastActionAt: d(0, 8),
    events: [
      { id: 'e1', at: d(-2, 7, 42), kind: 'resident', channel: 'App', text: 'Ananya reported: "Geyser not heating since morning. Light comes on, water stays cold."', simulated: false },
      { id: 'e2', at: d(-2, 7, 42), kind: 'memory', channel: 'Ghar Ki Memory', text: 'Retrieved Havells Monza EC 15L record: bought 35 months ago, element replaced 14 months ago by Mahesh (Havells Care).', simulated: false },
      { id: 'e3', at: d(-2, 7, 43), kind: 'memory', channel: 'Ghar Ki Memory', text: 'Warranty check: product warranty ended, element part warranty ended 2 months ago. Inner tank still covered, but not relevant to a heating fault. Expect a paid visit.', simulated: false },
      { id: 'e4', at: d(-2, 7, 45), kind: 'attempt', channel: 'WhatsApp · simulated', text: 'Raised a service request with Havells Care, sharing model, serial and fault description.', simulated: true },
      { id: 'e5', at: d(-2, 8, 10), kind: 'evidence', channel: 'WhatsApp · simulated', text: 'Havells Care issued case reference HVL-HYD-482917. Visit charge ₹400 + parts.', simulated: true },
      { id: 'e6', at: d(-2, 10, 5), kind: 'promise', channel: 'Call · simulated', text: 'Technician Suresh said: "Reaching in 10 minutes."', detail: 'A promise, not a confirmed appointment', simulated: true },
      { id: 'e7', at: d(-2, 10, 45), kind: 'missed', channel: 'Security desk log · simulated', text: 'Missed #1: no arrival 40 minutes after the promise. No technician entry at the gate.', simulated: true },
      { id: 'e8', at: d(-2, 10, 50), kind: 'attempt', channel: 'Call · simulated', text: 'Follow-up #1: called Suresh. He said he was stuck at another job and would come by 3 PM.', simulated: true },
      { id: 'e9', at: d(-2, 15, 30), kind: 'missed', channel: 'Security desk log · simulated', text: 'Missed #2: the "by 3 PM" promise passed with no arrival.', simulated: true },
      { id: 'e10', at: d(-2, 15, 35), kind: 'attempt', channel: 'Call · simulated', text: 'Follow-up #2: Suresh did not pick up. Sent a WhatsApp with the case reference.', simulated: true },
      { id: 'e11', at: d(-1, 9, 0), kind: 'promise', channel: 'Helpline · simulated', text: 'Follow-up #3: centre said Suresh is on leave; job reassigned. New window today 11 AM–1 PM.', detail: 'A promise, not a confirmed appointment', simulated: true },
      { id: 'e12', at: d(-1, 13, 10), kind: 'missed', channel: 'Security desk log · simulated', text: 'Missed #3: the 11 AM–1 PM window passed. No call, no arrival.', simulated: true },
      { id: 'e13', at: d(-1, 13, 15), kind: 'attempt', channel: 'Helpline · simulated', text: 'Follow-up #4: centre asked us to "wait 48 hours". No slot offered.', simulated: true },
      { id: 'e14', at: d(-1, 13, 20), kind: 'info', channel: 'WhatsApp · simulated', text: 'Identified a backup: Sri Sai Appliance Care (your authorised backup). Quote ₹1,850 is above your ₹1,500 limit, so it needs your approval.', simulated: true },
      { id: 'e15', at: d(0, 8, 0), kind: 'attempt', channel: 'WhatsApp · simulated', text: 'Morning check with Havells Care: no new slot yet. Next follow-up queued for 11:00 AM.', simulated: true },
    ],
  };

  const activities: Activity[] = [
    {
      id: 'a1', at: d(0, 8), label: 'Next follow-up queued', title: 'Morning check on Havells Care', link: { type: 'case', id: 'case-geyser' },
      why: 'The geyser case is open and Havells has missed 3 promised windows.', evidence: 'Case HVL-HYD-482917 timeline',
      outcome: 'No new slot offered yet.', next: 'Follow up again at 11:00 AM',
    },
    {
      id: 'a2', at: d(-1, 13, 20), label: 'Your approval needed', title: 'Backup technician quote is above your limit', link: { type: 'case', id: 'case-geyser' },
      why: 'Havells has missed 3 windows, and your rules let Saathi ask authorised backups for quotes.', evidence: 'Sri Sai Appliance Care quote, ₹1,850 (simulated message)',
      outcome: '₹1,850 is more than your ₹1,500 pre-approved limit.', next: 'Approve or decline from the geyser case',
    },
    {
      id: 'a3', at: d(-1, 18), label: 'Handled automatically', title: "Electrician's contact linked to the kitchen light repair", link: { type: 'asset', id: 'lighting' },
      why: 'Ravi sent a bill on WhatsApp for the kitchen LED panel.', evidence: "Ravi's WhatsApp bill, ₹420",
      outcome: 'Ravi Electricals saved as the electrician for kitchen lighting, with the repair in its history.',
    },
    {
      id: 'a4', at: d(-3, 19), label: 'Handled automatically', title: 'RO purifier service date saved', link: { type: 'asset', id: 'ro' },
      why: 'A photo of the Kent service receipt was shared.', evidence: 'Kent receipt #KS-55120',
      outcome: `Last filter service saved as ${fmtShort(roLastService)}. Next one falls due in about 4 months.`,
    },
    {
      id: 'a5', at: d(-9, 21), label: 'Handled automatically', title: 'Warranty details extracted from the washing machine invoice', link: { type: 'asset', id: 'washer' },
      why: 'The Croma invoice PDF was forwarded.', evidence: 'Croma invoice, LG FHM1207',
      outcome: `Comprehensive warranty runs till ${fmtShort(mo(3))}. Marked "extracted" until the warranty card is seen.`,
    },
    {
      id: 'a6', at: d(-12, 20), label: 'Completed and saved', title: 'AC maintenance schedule created', link: { type: 'asset', id: 'ac' },
      why: 'Two AC services in memory are about 6 months apart.', evidence: 'Voltas warranty service + CoolCare receipt',
      outcome: 'Every 6 months with Imran (CoolCare), weekend mornings, up to ₹1,200 pre-approved.',
    },
    {
      id: 'a7', at: d(-2, 7, 45), label: 'Waiting for the provider', title: 'Geyser repair request raised with Havells Care', link: { type: 'case', id: 'case-geyser' },
      why: 'Ananya reported the geyser not heating.', evidence: 'Asset record + warranty status',
      outcome: 'Case HVL-HYD-482917 opened (simulated).',
    },
  ];

  return {
    version: STATE_VERSION,
    clock: base,
    lastCheckedAt: atTime(base, 10, 16),
    household: { name: 'Sharma Home', city: 'Hyderabad', residents: ['Ananya Sharma', 'Rohit Sharma'], society: 'Gulmohar Residency, Kondapur' },
    assets,
    docs,
    providers,
    cases: [geyserCase],
    approvals: [
      {
        id: 'ap-geyser-alt', caseId: 'case-geyser', action: 'alt_spend', title: 'Book Sri Sai for the geyser?',
        detail: 'Havells has missed 3 visits. Sri Sai Appliance Care quotes ₹1,850, above your ₹1,500 limit.', amount: 1850, createdAt: d(-1, 13, 20),
      },
    ],
    activities,
    settings: {
      maxSpend: 1500,
      approver: 'Ananya or Rohit',
      autoAlternates: true,
      escalationAllowed: true,
      escalateAfter: 3,
      routineFollowUps: true,
      accessRule: 'resident_present',
      days: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      windows: ['morning', 'evening'],
    },
  };
}
