export type ReplyKind =
  | "answer"
  | "clarify"
  | "not_found"
  | "conflict"
  | "escalation_sent"
  | "out_of_scope"
  | "off_task"
  | "greeting"
  | "document"
  | "error";

export interface Profile {
  name: string;
  email: string;
  position?: string;
  department: string | null;
}

export interface Option {
  id: string;
  label: string;
}

export interface Claim {
  text: string;
  source_id: string;
  source_title: string;
  quote: string;
  from_quality: boolean;
}

export interface Variant {
  department_id: string;
  department_name: string;
  status: "answered" | "partial" | "not_found";
  lead: string;
  claims: Claim[];
  steps: string[];
  gap: string | null;
}

export interface DocumentLink {
  id: string;
  title: string;
  department_name: string;
  url: string;
}

export interface Usage {
  input_tokens: number;
  output_tokens: number;
  cost_rub: number;
  latency_ms: number;
  llm_calls: number;
}

export interface AgentReply {
  kind: ReplyKind;
  text: string;
  variants: Variant[];
  options: Option[];
  documents: DocumentLink[];
  missing_documents: string[];
  ticket: { code: string; status: string; quality_email: string } | null;
  usage: Usage;
  turn_id: number | null;
}

export interface Meta {
  company: string;
  assistant: string;
  departments: { id: string; name: string; full_name: string }[];
  documents: { id: string; title: string; department: string }[];
  demo_profiles: Profile[];
  quality_email: string;
}

export type ChatItem = { role: "employee"; text: string } | { role: "agent"; reply: AgentReply };
