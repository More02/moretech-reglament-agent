import { useState } from "react";
import type { Meta, Profile } from "./types";

interface Props {
  meta: Meta;
  onLogin: (p: Profile) => void;
}

const PROMISES = [
  {
    icon: "❝",
    title: "Только по тексту",
    text: "Каждое утверждение - с дословной цитатой пункта. Цитату и числа сверяет код",
  },
  {
    icon: "?",
    title: "Уточняет, а не угадывает",
    text: "Если правила в дирекциях разные - спросит, чей проект",
  },
  {
    icon: "∅",
    title: "Честно говорит «нет»",
    text: "Нет ответа в регламентах - не додумывает, а передаёт вопрос в службу качества",
  },
];

export function Login({ meta, onLogin }: Props) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const depName = (id: string | null) =>
    meta.departments.find((d) => d.id === id)?.name ?? "без подразделения";

  return (
    <section className="hero">
      <div className="hero-copy">
        <span className="eyebrow">ИИ-агент · {meta.company}</span>
        <h1>
          Ответы по регламентам. <em>Без выдумок.</em>
        </h1>
        <p className="hero-lead">
          Спросите своими словами - агент найдёт пункт регламента, покажет цитату и честно скажет, если ответа
          в документах нет.
        </p>
        <div className="promises">
          {PROMISES.map((p) => (
            <div key={p.title} className="promise">
              <span className="promise-icon">{p.icon}</span>
              <b>{p.title}</b>
              <span>{p.text}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="hero-panel">
        <div className="panel-title">Войти как сотрудник</div>
        <p className="panel-hint">Имитация корпоративного входа: подразделение берётся из профиля</p>
        <div className="profiles">
          {meta.demo_profiles.map((p) => (
            <button key={p.name} className="profile-card" onClick={() => onLogin(p)}>
              <span className="avatar">{p.name.slice(0, 1)}</span>
              <span className="profile-body">
                <span className="profile-name">{p.name}</span>
                <span className="profile-pos">{p.position}</span>
              </span>
              <span className={p.department ? "tag" : "tag ghost-tag"}>{depName(p.department)}</span>
              <span className="arrow">→</span>
            </button>
          ))}
        </div>
        <details className="custom-profile">
          <summary>Свой профиль</summary>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim() && email.includes("@")) {
                onLogin({ name: name.trim(), email: email.trim(), department: department || null });
              }
            }}
          >
            <input placeholder="Имя и фамилия" value={name} onChange={(e) => setName(e.target.value)} />
            <input placeholder="Рабочая почта" value={email} onChange={(e) => setEmail(e.target.value)} />
            <select value={department} onChange={(e) => setDepartment(e.target.value)}>
              <option value="">Подразделение не указано</option>
              {meta.departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.full_name}
                </option>
              ))}
            </select>
            <button className="primary" type="submit">
              Войти
            </button>
          </form>
        </details>
      </div>
    </section>
  );
}
