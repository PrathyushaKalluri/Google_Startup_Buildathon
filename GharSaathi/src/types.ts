export type AssetType = 'ac' | 'geyser' | 'ro' | 'washer' | 'fridge' | 'plumbing' | 'lighting';
export type Confidence = 'verified' | 'extracted' | 'needs_confirmation' | 'resident';
export type DocKind = 'invoice' | 'warranty_card' | 'service_receipt' | 'message' | 'amc_contract' | 'note';
export type Weekday = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';
export type TimeWindow = 'morning' | 'afternoon' | 'evening';

export interface DocField {
  label: string;
  value: string;
}

export interface Doc {
  id: string;
  assetId: string;
  kind: DocKind;
  title: string;
  issuer: string;
  date: string;
  fields: DocField[];
  addedBy: 'saathi' | 'resident';
}

export interface Fact {
  id: string;
  label: string;
  value: string;
  docId?: string;
  sourceLabel: string;
  confidence: Confidence;
}

export interface HistoryEvent {
  id: string;
  date: string;
  kind: 'purchase' | 'install' | 'service' | 'repair' | 'note' | 'renewal';
  title: string;
  detail?: string;
  providerId?: string;
  amount?: number;
  docId?: string;
}

export interface MaintenanceRule {
  label: string;
  intervalMonths: number;
  providerId: string;
  days: Weekday[];
  window: TimeWindow;
  maxCost: number;
  estCost: number;
  lastDone: string;
}

export interface Amc {
  providerId: string;
  start: string;
  end: string;
  cost: number;
  docId: string;
}

export interface Asset {
  id: string;
  name: string;
  brand: string;
  type: AssetType;
  category: 'appliance' | 'fixture';
  model: string;
  room: string;
  purchaseDate?: string;
  warrantyEnd?: string;
  warrantyNote: string;
  partWarrantyEnd?: string;
  amc?: Amc;
  rule?: MaintenanceRule;
  facts: Fact[];
  history: HistoryEvent[];
  providerIds: string[];
  warrantyReminderSaved?: boolean;
}

export interface ProviderLog {
  id: string;
  date: string;
  text: string;
  outcome: 'kept' | 'missed' | 'responded' | 'no_response' | 'quoted';
  caseId?: string;
}

export interface Provider {
  id: string;
  name: string;
  contactPerson?: string;
  category: string;
  kind: 'brand_centre' | 'individual' | 'society';
  phone: string;
  channel: string;
  preferred: boolean;
  backup: boolean;
  typicalCost?: string;
  assetIds: string[];
  /** Asset types this provider can be asked to quote for. */
  handles: AssetType[];
  quotes?: Partial<Record<AssetType, { amount: number; note: string }>>;
  log: ProviderLog[];
}

export type CaseState =
  | 'issue_received'
  | 'checking_memory'
  | 'contacting_provider'
  | 'awaiting_provider'
  | 'appointment_proposed'
  | 'awaiting_approval'
  | 'appointment_confirmed'
  | 'technician_en_route'
  | 'technician_missed'
  | 'escalation'
  | 'repair_in_progress'
  | 'awaiting_verification'
  | 'completed'
  | 'blocked';

export type EventKind =
  | 'resident'
  | 'memory'
  | 'attempt'
  | 'promise'
  | 'missed'
  | 'confirmed'
  | 'arrival'
  | 'evidence'
  | 'approval'
  | 'escalation'
  | 'info'
  | 'completed';

export interface CaseEvent {
  id: string;
  at: string;
  kind: EventKind;
  channel: string;
  text: string;
  detail?: string;
  simulated: boolean;
}

export interface Alternative {
  providerId: string;
  quote: number;
  quoteNote: string;
  status: 'pending' | 'approved' | 'declined';
}

export interface Appointment {
  start: string;
  end: string;
  providerId: string;
}

export type Track = 'primary' | 'supervisor' | 'visit';

export interface Case {
  id: string;
  assetId: string;
  kind: 'repair' | 'service' | 'renewal';
  title: string;
  state: CaseState;
  reportedAt: string;
  providerId: string;
  originalProviderId: string;
  reference?: string;
  track: Track;
  step: number;
  followUps: number;
  missed: number;
  escalated: boolean;
  arrived: boolean;
  expectedAmount?: number;
  alternative?: Alternative;
  appointment?: Appointment;
  nextAction: string;
  nextActionAt?: string;
  waitingOn: 'provider' | 'resident' | 'saathi' | 'nobody';
  lastActionAt: string;
  events: CaseEvent[];
  closedAt?: string;
  outcome?: { summary: string; receipt: string; amount: number };
}

export type ApprovalAction = 'alt_spend' | 'slot' | 'access' | 'otp' | 'service_spend' | 'amc_spend';

export interface Approval {
  id: string;
  caseId: string;
  action: ApprovalAction;
  title: string;
  detail: string;
  amount?: number;
  slot?: { start: string; end: string };
  createdAt: string;
}

export type ActivityLabel =
  | 'Handled automatically'
  | 'Waiting for the provider'
  | 'Your approval needed'
  | 'Next follow-up queued'
  | 'Completed and saved';

export interface Activity {
  id: string;
  at: string;
  label: ActivityLabel;
  title: string;
  why: string;
  evidence: string;
  outcome: string;
  next?: string;
  link?: { type: 'asset' | 'case'; id: string };
}

export interface Settings {
  maxSpend: number;
  approver: string;
  autoAlternates: boolean;
  escalationAllowed: boolean;
  escalateAfter: number;
  routineFollowUps: boolean;
  accessRule: 'resident_present' | 'security_desk';
  days: Weekday[];
  windows: TimeWindow[];
}

export interface AppState {
  version: number;
  clock: string;
  lastCheckedAt: string;
  household: { name: string; city: string; residents: string[]; society: string };
  assets: Asset[];
  docs: Doc[];
  providers: Provider[];
  cases: Case[];
  approvals: Approval[];
  activities: Activity[];
  settings: Settings;
}
