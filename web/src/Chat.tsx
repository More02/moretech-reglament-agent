import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Reply } from "./Reply";
import type { AgentReply, ChatItem, Meta, Profile } from "./types";

interface Props {
  meta: Meta;
  profile: Profile;
}

const EXAMPLES = [
  "Можно ли подать бюджетную оценку в конкурс?",
  "Как часто PM обновляет реестр рисков?",
  "Можно ли начать работы без подписанного договора?",
  "Компенсируют ли такси в командировке в выходной день?",
];

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

  useEffect(() => bottom.current?.scrollIntoView({ behavior: "smooth" }), [items, busy]);

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
    }, 5000);
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
    <section className="chat">
      <div className="chat-head">
        <div>
          <b>{profile.name}</b>
          <span className="muted"> · {profile.email}</span>
        </div>
        <span className={dep ? "chip" : "chip muted"}>
          {dep ? dep.full_name : "подразделение не указано - агент уточнит"}
        </span>
      </div>
      <div className="messages">
        {items.length === 0 && (
          <div className="empty">
            <p>Спросите своими словами - можно сокращениями (РП, SS, ТКП) и неформально.</p>
            <div className="examples">
              {EXAMPLES.map((q) => (
                <button key={q} className="example" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {items.map((it, i) =>
          it.role === "employee" ? (
            <div key={i} className="bubble employee">
              {it.text}
            </div>
          ) : (
            <Reply
              key={i}
              reply={it.reply}
              active={i === items.length - 1 && !busy}
              onChoose={choose}
              onRate={(r) => it.reply.turn_id && void api.rate(it.reply.turn_id, r)}
            />
          ),
        )}
        {busy && (
          <div className="bubble agent thinking">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
            Ищу в регламентах и сверяю цитаты…
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
          placeholder="Ваш вопрос по регламентам…"
          maxLength={2000}
          disabled={!conv}
        />
        <button className="primary" disabled={!conv || busy || !text.trim()}>
          Спросить
        </button>
      </form>
    </section>
  );
}
