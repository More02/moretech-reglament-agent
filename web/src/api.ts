import type { AgentReply, Meta, Profile } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("adminToken");
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Admin-Token": token } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(typeof body.detail === "string" ? body.detail : `Ошибка ${res.status}`);
  }
  return (await res.json()) as T;
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  meta: () => request<Meta>("/api/meta"),
  start: (profile: Profile) => post<{ id: string }>("/api/conversations", { profile }),
  ask: (conv: string, text: string) => post<AgentReply>(`/api/conversations/${conv}/messages`, { text }),
  choose: (conv: string, optionId: string) =>
    post<AgentReply>(`/api/conversations/${conv}/options`, { option_id: optionId }),
  turns: (conv: string, after: number) =>
    request<{ id: number; reply: AgentReply }[]>(`/api/conversations/${conv}/turns?after=${after}`),
  rate: (turnId: number, rating: number) => post<unknown>(`/api/turns/${turnId}/rating`, { rating }),
  analytics: () => request<Analytics>("/api/admin/analytics"),
  notes: () => request<Note[]>("/api/admin/notes"),
  setNote: (id: number, status: string) =>
    request<unknown>(`/api/admin/notes/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  evalReport: () => request<EvalReport | Record<string, never>>("/api/admin/eval"),
  gardener: () => post<{ clusters: Cluster[]; notes_need_review: number }>("/api/admin/gardener", {}),
};

export interface Cluster {
  title: string;
  question_ids: string[];
  suggestion: string;
}

export interface Note {
  id: number;
  question: string;
  answer: string;
  status: string;
  reason: string;
  expert: string;
  created_at: string;
  clauses: string[];
}

export interface EvalReport {
  summary: Record<string, number | string | null | Record<string, number | null>>;
}

export interface Analytics {
  totals: {
    questions: number;
    answered: number;
    clarified: number;
    not_found: number;
    out_of_scope: number;
    answer_rate: number;
    avg_latency_ms: number;
    avg_cost_rub: number;
    total_cost_rub: number;
    rating_positive_share: number | null;
  };
  outcomes: Record<string, number>;
  by_department: { id: string; name: string; answers: number }[];
  coverage: { document: string; section: string; citations: number }[];
  unanswered: { text: string; outcome: string; at: string }[];
  tickets: {
    open: number;
    answered: number;
    avg_hours_to_answer: number | null;
    items: { code: string; question: string; status: string; employee: string; created_at: string }[];
  };
  notes: { published: number; needs_review: { id: number; question: string; reason: string }[] };
  actualization_candidates: {
    document: string;
    section: string;
    signals: Record<string, number>;
    weight: number;
  }[];
}
