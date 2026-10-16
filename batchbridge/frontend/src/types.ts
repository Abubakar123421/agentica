export type User = {
  id: string;
  email: string;
  display_name: string;
  role: "importer_investigator" | "retailer_safety_manager" | "manufacturer_reviewer";
  organization_id: string;
};

export type CaseSummary = {
  id: string;
  public_id: string;
  source: string;
  product_name: string;
  batch_number: string | null;
  status: string;
  safety_verdict: string;
  retailer_id: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentRun = {
  id: string;
  agent_type: "triage" | "traceability" | "escalation";
  status: string;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
};

export type Proposal = {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  status: string;
  version: number;
  created_at: string;
};

export type Inspection = {
  id: string;
  case_id?: string;
  retailer_id?: string;
  status: string;
  finding: string | null;
  notes: string | null;
  created_at: string;
  completed_at: string | null;
};

export type TimelineEvent = {
  id: string;
  event_type: string;
  actor_user_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type CaseDetail = {
  case: CaseSummary;
  description: string;
  proposals: Proposal[];
  inspections: Inspection[];
  timeline: TimelineEvent[];
  agent_runs: AgentRun[];
};

export type Escalation = {
  id: string;
  case_id: string;
  packet: Record<string, unknown>;
  status: string;
  response: string | null;
  created_at: string;
};
