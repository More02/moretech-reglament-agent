import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Reply } from "./Reply";
import type { AgentReply, ChatItem, Meta, Profile } from "./types";

interface Props {
  meta: Meta;
  profile: Profile;
}

const SCENARIOS = [
  { tone: "ok", label: "Ответ есть", q: "Можно ли подать бюджетную оценку в конкурс?" },
  { tone: "ask", label: "Синонимы и сокращения", q: "Как часто PM обновляет реестр рисков?" },
  {
    tone: "half",
    label: "Ответ неполный",
    q: "Кто назначает РП и нужно ли согласовывать его кандидатуру с заказчиком?",
  },
  { tone: "no", label: "Нет в регламентах", q: "Компенсируют ли такси в командировке в выходной день?" },
  { tone: "doc", label: "Ссылка на документ вне базы", q: "Как выбрать субподрядчика для проекта?" },
  { tone: "muted", label: "Вне регламентов", q: "Какая у меня будет премия по итогам года?" },
];

const STEPS = ["Понимаю вопрос", "Ищу пункты регламентов", "Сверяю цитаты и числа"];

function Thinking() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = window.setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1600);
    return () => window.clearInterval(t);
  }, []);
  return (
    <div className="thinking">
      {STEPS.map((s, i) => (
        <span key={s} className={i < step ? "done" : i === step ? "now" : ""}>
          <i />
          {s}
        </span>
      ))}
    </div>
  );
}

export function Chat({ meta, profile }: Props) {
  const [conv, setConv] = useState<string | null>(null);
  const [items, setItems] = useState<ChatItem[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lastTurn = useRef(0);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.start(profile).then(
      (r) => setConv(r.id),
      (e: Error) => setError(e.message),
    );
  }, [profile]);

  useEffect(() => {
    // В новых браузерах scrollIntoView возвращает Promise - его нельзя отдавать React как функцию очистки
    void bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items, busy]);

  const push = useCallback((reply: AgentReply) => {
    if (reply.turn_id) lastTurn.current = Math.max(lastTurn.current, reply.turn_id);
    setItems((prev) => [...prev, { role: "agent", reply }]);
  }, []);

  // Ответ эксперта приходит по почте - агент добавляет реплику в диалог, чат её подхватывает.
  useEffect(() => {
    if (!conv) return;
    const timer = window.setInterval(() => {
      api.turns(conv, lastTurn.current).then(
        (rows) => {
          const fresh = rows.filter((r) => r.id > lastTurn.current && r.reply.kind === "escalation_sent");
          rows.forEach((r) => (lastTurn.current = Math.max(lastTurn.current, r.id)));
          fresh.forEach((r) => push({ ...r.reply, turn_id: r.id }));
        },
        () => undefined,
      );
    }, 4000);
    return () => window.clearInterval(timer);
  }, [conv, push]);

  const run = async (label: string, action: () => Promise<AgentReply>) => {
    setItems((prev) => [...prev, { role: "employee", text: label }]);
    setBusy(true);
    setError("");
    try {
      push(await action());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const send = (q: string) => {
    if (!conv || !q.trim() || busy) return;
    setText("");
    void run(q.trim(), () => api.ask(conv, q.trim()));
  };

  const choose = (id: string, label: string) => {
    if (!conv || busy) return;
    void run(label, () => api.choose(conv, id));
  };

  const dep = meta.departments.find((d) => d.id === profile.department);

  return (
    <section className="workspace">
      <aside className="side">
        <div className="side-card me">
          <span className="avatar">{profile.name.slice(0, 1)}</span>
          <div>
            <b>{profile.name}</b>
            <div className="muted small">{profile.email}</div>
          </div>
        </div>
        <div className={dep ? "dep-pill" : "dep-pill empty"}>
          {dep ? dep.full_name : "Подразделение не указано - агент уточнит, если правила разные"}
        </div>

        <div className="side-title">Попробуйте</div>
        <div className="scenarios">
          {SCENARIOS.map((s) => (
            <button
              key={s.q}
              className={`scenario t-${s.tone}`}
              onClick={() => send(s.q)}
              disabled={busy || !conv}
            >
              <span className="scenario-label">{s.label}</span>
              <span className="scenario-q">{s.q}</span>
            </button>
          ))}
        </div>

        <div className="side-title">Как агент отвечает</div>
        <ul className="rules">
          <li>Каждое утверждение - с цитатой пункта, сверенной кодом</li>
          <li>Не нашёл в регламентах - так и говорит</li>
          <li>Письмо в службу качества - только по вашей кнопке</li>
        </ul>
      </aside>

      <div className="chat">
        <div className="messages">
          {items.length === 0 && (
            <div className="welcome">
              <span className="welcome-mark">❝</span>
              <h2>Задайте вопрос по регламентам</h2>
              <p>Можно своими словами и сокращениями: РП, PM, SS, ТКП, «подрядчик», «смета».</p>
            </div>
          )}
          {items.map((it, i) =>
            it.role === "employee" ? (
              <div key={i} className="msg-row me">
                <div className="bubble employee">{it.text}</div>
              </div>
            ) : (
              <div key={i} className="msg-row">
                <span className="bot-mark">
                  <img src="/mono-gold.svg" alt="" />
                </span>
                <Reply
                  reply={it.reply}
                  active={i === items.length - 1 && !busy}
                  onChoose={choose}
                  onRate={(r) => it.reply.turn_id && void api.rate(it.reply.turn_id, r)}
                />
              </div>
            ),
          )}
          {busy && (
            <div className="msg-row">
              <span className="bot-mark pulse">
                <img src="/mono-gold.svg" alt="" />
              </span>
              <Thinking />
            </div>
          )}
          <div ref={bottom} />
        </div>
        {error && <div className="banner error">{error}</div>}
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send(text);
          }}
        >
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Например: можно ли начать работы без договора?"
            maxLength={2000}
            disabled={!conv}
          />
          <button className="send" disabled={!conv || busy || !text.trim()} aria-label="Спросить">
            ↑
          </button>
        </form>
      </div>
    </section>
  );
}
