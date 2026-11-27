import { useState } from "react";
import type { Meta, Profile } from "./types";

interface Props {
  meta: Meta;
  onLogin: (p: Profile) => void;
}

export function Login({ meta, onLogin }: Props) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const depName = (id: string | null) =>
    meta.departments.find((d) => d.id === id)?.name ?? "подразделение не указано";

  return (
    <section className="login">
      <h1>Ответы по регламентам - строго по тексту документов</h1>
      <p className="lead">
        Агент отвечает с цитатой из пункта регламента, уточняет подразделение, если правила разные, а если
        ответа в регламентах нет - отправляет вопрос в службу качества и запоминает ответ эксперта.
      </p>
      <p className="hint">
        Вход имитирует корпоративную авторизацию: подразделение берётся из профиля, почта - для копии письма в
        службу качества.
      </p>
      <div className="profiles">
        {meta.demo_profiles.map((p) => (
          <button key={p.name} className="profile-card" onClick={() => onLogin(p)}>
            <span className="avatar">{p.name.slice(0, 1)}</span>
            <span className="profile-name">{p.name}</span>
            <span className="profile-pos">{p.position}</span>
            <span className={p.department ? "chip" : "chip muted"}>{depName(p.department)}</span>
          </button>
        ))}
      </div>
      <form
        className="custom-profile"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim() && email.includes("@")) {
            onLogin({ name: name.trim(), email: email.trim(), department: department || null });
          }
        }}
      >
        <h2>Или свой профиль</h2>
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
    </section>
  );
}
