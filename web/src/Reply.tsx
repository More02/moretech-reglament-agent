import { useState } from "react";
import type { AgentReply, Claim, Variant } from "./types";

interface Props {
  reply: AgentReply;
  active: boolean;
  onChoose: (id: string, label: string) => void;
  onRate: (rating: number) => void;
}

type Tone = "ok" | "half" | "no" | "ask" | "mail" | "muted" | "warn";

function verdict(reply: AgentReply): { tone: Tone; icon: string; title: string } | null {
  switch (reply.kind) {
    case "answer": {
      const partial = reply.variants.some((v) => v.status === "partial");
      const fromQuality = reply.variants.some((v) => v.claims.some((c) => c.from_quality));
      if (partial)
        return { tone: "half", icon: "◐", title: "Неполный ответ - в регламентах есть только часть" };
      if (fromQuality) return { tone: "ok", icon: "★", title: "Ответ по разъяснению службы качества" };
      return { tone: "ok", icon: "✓", title: "Ответ найден в регламенте" };
    }
    case "not_found":
      return { tone: "no", icon: "∅", title: "В регламентах ответа нет" };
    case "clarify":
      return { tone: "ask", icon: "?", title: "Нужно уточнение - правила в подразделениях разные" };
    case "conflict":
      return { tone: "warn", icon: "!", title: "Противоречие в регламенте" };
    case "escalation_sent":
      return {
        tone: "mail",
        icon: "✉",
        title: reply.ticket?.status === "answered" ? "Ответ службы качества" : "Служба качества",
      };
    case "out_of_scope":
      return { tone: "muted", icon: "↗", title: "Вопрос не про регламенты" };
    case "off_task":
      return { tone: "muted", icon: "×", title: "Это не моя задача" };
    case "document":
      return { tone: "ok", icon: "▤", title: "Документы" };
    default:
      return null;
  }
}

function docLink(sourceId: string): string | null {
  if (sourceId.startsWith("note:")) return null;
  const [doc, num] = sourceId.split(":");
  return doc && num ? `/api/documents/${doc}#${num}` : null;
}

function ClaimRow({ claim, openByDefault }: { claim: Claim; openByDefault: boolean }) {
  const [open, setOpen] = useState(openByDefault);
  const link = docLink(claim.source_id);
  return (
    <li className={claim.from_quality ? "claim quality" : "claim"}>
      <div className="claim-text">{claim.text}</div>
      <div className="claim-src">
        <button className="cite" onClick={() => setOpen(!open)} aria-expanded={open}>
          {claim.from_quality ? "★ " : "§ "}
          {claim.source_title}
          <span className="caret">{open ? "▴" : "▾"}</span>
        </button>
        {link && (
          <a className="open-src" href={link} target="_blank" rel="noreferrer">
            открыть пункт ↗
          </a>
        )}
      </div>
      {open && <blockquote>{claim.quote}</blockquote>}
    </li>
  );
}

function VariantCard({ v, single, first }: { v: Variant; single: boolean; first: boolean }) {
  return (
    <div className={`variant st-${v.status}`}>
      {!single && (
        <div className="variant-head">
          <span className="tag">{v.department_name}</span>
          {v.status === "partial" && <span className="tag half">неполный</span>}
          {v.status === "not_found" && <span className="tag no">нет в регламенте</span>}
        </div>
      )}
      {v.lead && <p className="lead-answer">{v.lead}</p>}
      {v.claims.length > 0 && (
        <ul className="claims">
          {v.claims.map((c, i) => (
            <ClaimRow key={i} claim={c} openByDefault={first && i === 0} />
          ))}
        </ul>
      )}
      {v.steps.length > 0 && (
        <ol className="steps">
          {v.steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
      )}
      {v.gap && (
        <div className="gap">
          <b>Чего нет в регламентах</b>
          <span>{v.gap}</span>
        </div>
      )}
    </div>
  );
}

export function Reply({ reply, active, onChoose, onRate }: Props) {
  const [rated, setRated] = useState(0);
  const v = verdict(reply);
  const u = reply.usage;
  const single = reply.variants.length === 1 && !reply.text.includes("Комплексный");
  return (
    <div className={`answer-card ${v ? `tone-${v.tone}` : ""}`}>
      {v && (
        <div className="verdict">
          <span className="verdict-icon">{v.icon}</span>
          {v.title}
        </div>
      )}
      {reply.text && <p className="reply-text">{reply.text}</p>}
      {reply.variants.map((variant, i) => (
        <VariantCard key={variant.department_id} v={variant} single={single} first={i === 0} />
      ))}
      {reply.documents.length > 0 && (
        <ul className="docs">
          {reply.documents.map((d) => (
            <li key={d.id}>
              <a href={d.url} target="_blank" rel="noreferrer">
                {d.title}
              </a>
              <span className="muted"> · {d.department_name}</span>
            </li>
          ))}
        </ul>
      )}
      {reply.missing_documents.length > 0 && (
        <div className="missing">
          <b>Регламент ссылается на документы, которых нет в базе</b>
          <ul>
            {reply.missing_documents.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
          <span className="muted small">Их содержание агент не додумывает.</span>
        </div>
      )}
      {reply.ticket && (
        <div className="ticket">
          <span className="ticket-code">{reply.ticket.code}</span>
          {reply.ticket.status === "answered"
            ? "Эксперт ответил - разъяснение сохранено в базе знаний"
            : `Письмо отправлено на ${reply.ticket.quality_email}, вы в копии`}
        </div>
      )}
      {reply.options.length > 0 && (
        <div className="options">
          {reply.options.map((o) => (
            <button
              key={o.id}
              className={o.id === "escalate" ? "option accent" : "option"}
              disabled={!active}
              onClick={() => onChoose(o.id, o.label)}
            >
              {o.id === "escalate" ? "✉ " : ""}
              {o.label}
            </button>
          ))}
        </div>
      )}
      <div className="meta-row">
        <span className="pill">⚡ {(u.latency_ms / 1000).toFixed(1).replace(".", ",")} с</span>
        <span className="pill">{u.cost_rub.toFixed(2).replace(".", ",")} ₽</span>
        <span className="pill">
          {u.llm_calls === 0 ? "без вызова модели" : `вызовов модели: ${u.llm_calls}`}
        </span>
        {reply.checked_claims > 0 && (
          <span className="pill shield" title="Цитаты, пункты и числа проверены кодом, а не нейросетью">
            ✓ цитат сверено кодом: {reply.checked_claims - reply.rejected_claims}
            {reply.rejected_claims > 0 && ` · отброшено: ${reply.rejected_claims}`}
          </span>
        )}
        {reply.turn_id && reply.kind === "answer" && (
          <span className="rate">
            <button
              className={rated === 1 ? "on" : ""}
              onClick={() => (setRated(1), onRate(1))}
              title="Полезно"
            >
              👍
            </button>
            <button
              className={rated === -1 ? "on" : ""}
              onClick={() => (setRated(-1), onRate(-1))}
              title="Неверно"
            >
              👎
            </button>
          </span>
        )}
      </div>
    </div>
  );
}
