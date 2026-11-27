import { useCallback, useEffect, useState } from "react";
import { api, type Analytics, type Cluster, type EvalReport, type Note } from "./api";
import type { Meta } from "./types";

const STATUS: Record<string, string> = {
  published: "опубликовано",
  needs_review: "перепроверить",
  disputed: "эксперты разошлись",
  retired: "снято",
};

const OUTCOME: Record<string, string> = {
  answer: "Ответ с цитатой",
  clarify: "Уточнение",
  not_found: "Нет в регламентах",
  conflict: "Противоречие",
  escalation_sent: "Служба качества",
  out_of_scope: "Вне регламентов",
  off_task: "Посторонняя задача",
  greeting: "Приветствие",
  document: "Поиск документа",
  error: "Ошибка",
};

function Tile({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="tile">
      <div className="tile-value">{value}</div>
      <div className="tile-label">{label}</div>
      {hint && <div className="tile-hint">{hint}</div>}
    </div>
  );
}

const pct = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v * 100)}%`);

export function Cabinet({ meta }: { meta: Meta | null }) {
  const [data, setData] = useState<Analytics | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [evalReport, setEval] = useState<EvalReport | null>(null);
  const [clusters, setClusters] = useState<Cluster[] | null>(null);
  const [error, setError] = useState("");
  const [token, setToken] = useState(localStorage.getItem("adminToken") ?? "");

  const load = useCallback(() => {
    setError("");
    Promise.all([api.analytics(), api.notes(), api.evalReport()]).then(
      ([a, n, e]) => {
        setData(a);
        setNotes(n);
        setEval("summary" in e ? (e as EvalReport) : null);
      },
      (e: Error) => setError(e.message),
    );
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (error)
    return (
      <section className="cabinet">
        <div className="banner error">{error}</div>
        <form
          className="token"
          onSubmit={(e) => {
            e.preventDefault();
            localStorage.setItem("adminToken", token);
            load();
          }}
        >
          <input placeholder="Токен кабинета" value={token} onChange={(e) => setToken(e.target.value)} />
          <button className="primary">Войти</button>
        </form>
      </section>
    );
  if (!data) return <div className="loading">Загружаю аналитику…</div>;

  const t = data.totals;
  const maxOutcome = Math.max(1, ...Object.values(data.outcomes));
  const s = evalReport?.summary;

  return (
    <section className="cabinet">
      <div className="cabinet-head">
        <h1>Кабинет службы качества</h1>
        <button className="ghost" onClick={load}>
          Обновить
        </button>
      </div>
      <div className="tiles">
        <Tile label="вопросов за 30 дней" value={t.questions} />
        <Tile label="ответов с цитатой" value={pct(t.answer_rate)} hint={`${t.answered} шт.`} />
        <Tile label="уточнений" value={t.clarified} />
        <Tile label="нет в регламентах" value={t.not_found} hint="кандидаты в разъяснения" />
        <Tile label="среднее время ответа" value={`${(t.avg_latency_ms / 1000).toFixed(1)} с`} />
        <Tile
          label="средняя стоимость"
          value={`${t.avg_cost_rub.toFixed(2)} ₽`}
          hint={`всего ${t.total_cost_rub} ₽`}
        />
        <Tile label="полезных по оценкам" value={pct(t.rating_positive_share)} />
        <Tile label="разъяснений в базе" value={data.notes.published} />
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Чем закончились вопросы</h2>
          {Object.entries(data.outcomes).map(([k, v]) => (
            <div key={k} className="bar-row">
              <span>{OUTCOME[k] ?? k}</span>
              <div className="bar">
                <div style={{ width: `${(v / maxOutcome) * 100}%` }} />
              </div>
              <b>{v}</b>
            </div>
          ))}
        </div>
        <div className="card">
          <h2>Кандидаты на актуализацию регламентов</h2>
          <p className="muted">
            Разделы, где сотрудникам чаще не хватает регламента: уточнения, нет ответа, разъяснения поверх
            текста.
          </p>
          {data.actualization_candidates.length === 0 && <p className="muted">Пока сигналов нет.</p>}
          <table>
            <tbody>
              {data.actualization_candidates.slice(0, 8).map((c) => (
                <tr key={c.document + c.section}>
                  <td>
                    <b>{c.section}</b>
                    <div className="muted">{c.document}</div>
                  </td>
                  <td className="num">{c.weight}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Обращения в службу качества</h2>
          <p className="muted">
            Открыто: {data.tickets.open} · отвечено: {data.tickets.answered}
            {data.tickets.avg_hours_to_answer != null &&
              ` · среднее время ответа ${data.tickets.avg_hours_to_answer} ч`}
          </p>
          <table>
            <tbody>
              {data.tickets.items.slice(0, 8).map((tk) => (
                <tr key={tk.code}>
                  <td className="nowrap">{tk.code}</td>
                  <td>{tk.question}</td>
                  <td className="nowrap">{tk.status === "answered" ? "отвечено" : "ждёт ответа"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h2>Вопросы без ответа в регламентах</h2>
          <button
            className="ghost small"
            onClick={() =>
              api.gardener().then(
                (r) => setClusters(r.clusters),
                (e: Error) => setError(e.message),
              )
            }
          >
            Сгруппировать по темам
          </button>
          {clusters ? (
            <ul className="clusters">
              {clusters.map((c) => (
                <li key={c.title}>
                  <b>{c.title}</b> · {c.question_ids.length} вопр.
                  {c.suggestion && <div className="muted">{c.suggestion}</div>}
                </li>
              ))}
            </ul>
          ) : (
            <ul className="plain">
              {data.unanswered.slice(-8).map((q, i) => (
                <li key={i}>{q.text}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card">
        <h2>База разъяснений службы качества</h2>
        <table>
          <tbody>
            {notes.map((n) => (
              <tr key={n.id}>
                <td>
                  <b>{n.question}</b>
                  <div>{n.answer}</div>
                  <div className="muted">
                    {n.expert} · {new Date(n.created_at).toLocaleDateString("ru-RU")}
                    {n.reason && ` · ${n.reason}`}
                  </div>
                </td>
                <td className="nowrap">
                  <span className={`chip st-${n.status}`}>{STATUS[n.status] ?? n.status}</span>
                </td>
                <td className="nowrap">
                  {n.status !== "published" && (
                    <button className="ghost small" onClick={() => api.setNote(n.id, "published").then(load)}>
                      Утвердить
                    </button>
                  )}
                  {n.status !== "retired" && (
                    <button className="ghost small" onClick={() => api.setNote(n.id, "retired").then(load)}>
                      Снять
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {notes.length === 0 && (
              <tr>
                <td className="muted">
                  Разъяснений пока нет - они появятся после ответов экспертов на письма.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Покрытие регламентов</h2>
          <table>
            <tbody>
              {data.coverage
                .filter((c) => c.citations > 0)
                .slice(0, 10)
                .map((c) => (
                  <tr key={c.document + c.section}>
                    <td>
                      {c.section}
                      <div className="muted">{c.document}</div>
                    </td>
                    <td className="num">{c.citations}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h2>Качество на тестовом наборе</h2>
          {s ? (
            <table>
              <tbody>
                <tr>
                  <td>Верное поведение</td>
                  <td className="num">{pct(s.behavior_accuracy as number)}</td>
                </tr>
                <tr>
                  <td>Верная цитата</td>
                  <td className="num">{pct(s.citation_accuracy as number)}</td>
                </tr>
                <tr>
                  <td>Ложные ответы</td>
                  <td className="num">{pct(s.false_answer_rate as number)}</td>
                </tr>
                <tr>
                  <td>Эскалация, где нужно</td>
                  <td className="num">{pct(s.escalation_recall as number)}</td>
                </tr>
                <tr>
                  <td>Уточнение, где нужно</td>
                  <td className="num">{pct(s.clarify_recall as number)}</td>
                </tr>
                <tr>
                  <td>Медиана времени</td>
                  <td className="num">{((s.latency_ms_p50 as number) / 1000).toFixed(1)} с</td>
                </tr>
                <tr>
                  <td>Стоимость вопроса</td>
                  <td className="num">{(s.avg_cost_rub as number).toFixed(2)} ₽</td>
                </tr>
                <tr>
                  <td>Модель</td>
                  <td className="num">{String(s.model)}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="muted">Отчёт появится после прогона «reglament eval».</p>
          )}
          {meta && <p className="muted">Документов в базе: {meta.documents.length}</p>}
        </div>
      </div>
    </section>
  );
}
