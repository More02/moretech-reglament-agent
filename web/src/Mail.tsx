import { useCallback, useEffect, useState } from "react";
import { api, type MailBox, type MailThread } from "./api";

const CLASS_LABEL: Record<string, string> = {
  final_answer: "финальный ответ",
  question_to_employee: "вопрос сотруднику",
  forwarded_to_owner: "передано владельцу процесса",
  acknowledgement: "подтверждение получения",
  other: "не финальный ответ",
  error: "не удалось разобрать",
};

function Thread({ t, box, onSent }: { t: MailThread; box: MailBox; onSent: () => void }) {
  const [sender, setSender] = useState(box.quality_email);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  const send = async () => {
    if (!body.trim()) return;
    setBusy(true);
    setNote("");
    try {
      const r = await api.mailReply(t.code, sender, body);
      setBody("");
      setNote(
        r.published_notes.length
          ? "Ответ принят: разъяснение опубликовано, сотрудник получил уведомление в чате"
          : "Письмо доставлено агенту",
      );
      onSent();
    } catch (e) {
      setNote((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="thread">
      <div className="thread-head">
        <span className="ticket-code">{t.code}</span>
        <b>{t.question}</b>
        <span className={t.status === "answered" ? "tag ok" : "tag half"}>
          {t.status === "answered" ? "отвечено" : "ждёт ответа"}
        </span>
      </div>
      {t.messages.map((m, i) => (
        <article key={i} className={`letter ${m.direction}`}>
          <header>
            <span>
              <b>{m.direction === "out" ? "Агент" : m.sender}</b> → {m.recipients.join(", ")}
            </span>
            <span className="muted small">{new Date(m.at).toLocaleString("ru-RU")}</span>
          </header>
          <div className="letter-subject">{m.subject}</div>
          <pre>{m.body}</pre>
          {m.classification && (
            <span className="tag">{CLASS_LABEL[m.classification] ?? m.classification}</span>
          )}
        </article>
      ))}
      {box.demo && (
        <div className="reply-box">
          <div className="reply-row">
            <label>От кого</label>
            <input value={sender} onChange={(e) => setSender(e.target.value)} />
          </div>
          <textarea
            rows={4}
            placeholder="Ответ эксперта службы качества. Можно добавить метку #ответ или #черновик"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <div className="reply-row end">
            {note && <span className="muted small">{note}</span>}
            <button className="primary" disabled={busy || !body.trim()} onClick={() => void send()}>
              {busy ? "Агент разбирает письмо…" : "Ответить всем"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function Mail() {
  const [box, setBox] = useState<MailBox | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    api.mail().then(setBox, (e: Error) => setError(e.message));
  }, []);
  useEffect(() => {
    load();
    const t = window.setInterval(load, 5000);
    return () => window.clearInterval(t);
  }, [load]);

  if (error) return <div className="banner error">{error}</div>;
  if (!box) return <div className="loading">Загружаю почту…</div>;
  return (
    <div className="mail">
      <p className="muted">
        Ящик агента <b>{box.agent_address}</b> · служба качества <b>{box.quality_email}</b>
        {box.demo
          ? " · демо-режим стенда: ответ эксперта вводится здесь и проходит тот же путь, что письмо из почты (IMAP)"
          : " · подключён настоящий почтовый ящик"}
      </p>
      {box.threads.length === 0 && (
        <div className="empty-card">
          Обращений пока нет. Задайте в чате вопрос, на который нет ответа в регламентах, и нажмите «Отправить
          вопрос в службу качества».
        </div>
      )}
      {box.threads.map((t) => (
        <Thread key={t.code} t={t} box={box} onSent={load} />
      ))}
    </div>
  );
}
