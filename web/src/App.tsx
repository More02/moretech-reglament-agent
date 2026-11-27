import { useEffect, useState } from "react";
import { api } from "./api";
import { Cabinet } from "./Cabinet";
import { Chat } from "./Chat";
import { Login } from "./Login";
import type { Meta, Profile } from "./types";

export function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [view, setView] = useState<"chat" | "cabinet">(
    window.location.pathname.startsWith("/cabinet") ? "cabinet" : "chat",
  );
  const [error, setError] = useState("");

  useEffect(() => {
    api.meta().then(setMeta, (e: Error) => setError(e.message));
  }, []);

  const go = (next: "chat" | "cabinet") => {
    setView(next);
    window.history.replaceState(null, "", next === "cabinet" ? "/cabinet" : "/");
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="monogram">MT</span>
          <div>
            <div className="brand-name">MORE TECH</div>
            <div className="brand-sub">Агент по регламентам{meta ? ` · ${meta.company}` : ""}</div>
          </div>
        </div>
        <nav className="tabs">
          <button className={view === "chat" ? "tab active" : "tab"} onClick={() => go("chat")}>
            Чат сотрудника
          </button>
          <button className={view === "cabinet" ? "tab active" : "tab"} onClick={() => go("cabinet")}>
            Кабинет службы качества
          </button>
        </nav>
        {profile && view === "chat" && (
          <button className="ghost" onClick={() => setProfile(null)}>
            {profile.name} · сменить
          </button>
        )}
      </header>
      {error && <div className="banner error">{error}</div>}
      <main>
        {view === "cabinet" ? (
          <Cabinet meta={meta} />
        ) : !meta ? (
          <div className="loading">Загружаю…</div>
        ) : profile ? (
          <Chat key={profile.name + profile.department} meta={meta} profile={profile} />
        ) : (
          <Login meta={meta} onLogin={setProfile} />
        )}
      </main>
    </div>
  );
}
