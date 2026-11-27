import { useState } from "react";
import type { AgentReply, Claim, Variant } from "./types";

interface Props {
  reply: AgentReply;
  active: boolean;
  onChoose: (id: string, label: string) => void;
  onRate: (rating: number) => void;
}

const KIND_LABEL: Partial<Record<AgentReply["kind"], string>> = {
  clarify: "Нужно уточнение",
  not_found: "В регламентах ответа нет",
  conflict: "Противоречие в регламенте",
  escalation_sent: "Служба качества",
  out_of_scope: "Вне регламентов",
  off_task: "Не моя задача",
};

function docLink(sourceId: string): string | null {
  if (sourceId.startsWith("note:")) return null;
  const [doc, num] = sourceId.split(":");
  return doc && num ? `/api/documents/${doc}#${num}` : null;
}

function ClaimRow({ claim }: { claim: Claim }) {
  const [open, setOpen] = useState(false);
  const link = docLink(claim.source_id);
  return (
    <li className={claim.from_quality ? "claim quality" : "claim"}>
      <span>{claim.text}</span>
      <button className="source" onClick={() => setOpen(!open)} title="Показать цитату">
        {claim.from_quality ? "★ " : ""}
        {claim.source_title}
      </button>
      {open && (
        <blockquote>
          «{claim.quote}»
          {link && (
            <a href={link} target="_blank" rel="noreferrer">
              открыть пункт ↗
            </a>
          )}
        </blockquote>
      )}
    </li>
  );
}

function VariantCard({ v, single }: { v: Variant; single: boolean }) {
  return (
    <div className="variant">
      {!single && (
        <div className="variant-head">
          <span className="chip">{v.department_name}</span>
          {v.status === "partial" && <span className="chip warn">частично</span>}
        </div>
      )}
      {v.lead && <p className="lead-answer">{v.lead}</p>}
      <ul className="claims">
        {v.claims.map((c, i) => (
          <ClaimRow key={i} claim={c} />
        ))}
      </ul>
      {v.steps.length > 0 && (
        <ol className="steps">
          {v.steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
      )}
      {v.gap && <p className="gap">Не описано в регламенте: {v.gap}</p>}
    </div>
  );
}

export function Reply({ reply, active, onChoose, onRate }: Props) {
  const [rated, setRated] = useState(0);
  const label = KIND_LABEL[reply.kind];
  const u = reply.usage;
  return (
    <div className={`bubble agent kind-${reply.kind}`}>
      {label && <div className="kind-label">{label}</div>}
      {reply.text && <p className="reply-text">{reply.text}</p>}
      {reply.variants.map((v) => (
        <VariantCard
          key={v.department_id}
          v={v}
          single={reply.variants.length === 1 && !reply.text.includes("Комплексный")}
        />
      ))}
      {reply.documents.length > 0 && (
        <ul className="docs">
          {reply.documents.map((d) => (
            <li key={d.id}>
              <a href={d.url} target="_blank" rel="noreferrer">
                {d.title}
              </a>{" "}
              <span className="muted">· {d.department_name}</span>
            </li>
          ))}
        </ul>
      )}
      {reply.missing_documents.length > 0 && (
        <div className="missing">
          <b>Регламент ссылается на документы, которых нет в базе:</b>
          <ul>
            {reply.missing_documents.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
          Их содержание агент не додумывает.
        </div>
      )}
      {reply.ticket && (
        <div className="ticket">
          Обращение <b>{reply.ticket.code}</b> · письмо на {reply.ticket.quality_email}, вы в копии
        </div>
      )}
      {reply.options.length > 0 && (
        <div className="options">
          {reply.options.map((o) => (
            <button key={o.id} className="option" disabled={!active} onClick={() => onChoose(o.id, o.label)}>
              {o.label}
            </button>
          ))}
        </div>
      )}
      <div className="meta-row">
        <span>
          {(u.latency_ms / 1000).toFixed(1)} с · {u.cost_rub.toFixed(2)} ₽ ·{" "}
          {u.llm_calls === 0 ? "без вызова модели" : `вызовов модели: ${u.llm_calls}`}
        </span>
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
