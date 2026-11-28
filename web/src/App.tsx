import { useEffect, useState } from "react";
import { api } from "./api";
import { Cabinet } from "./Cabinet";
import { Chat } from "./Chat";
import { Login } from "./Login";
import type { Meta, Profile } from "./types";

type View = "chat" | "cabinet";

export function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [view, setView] = useState<View>(
    window.location.pathname.startsWith("/cabinet") ? "cabinet" : "chat",
  );
  const [error, setError] = useState("");

  useEffect(() => {
    api.meta().then(setMeta, (e: Error) => setError(e.message));
  }, []);

  const go = (next: View) => {
    setView(next);
    window.history.replaceState(null, "", next === "cabinet" ? "/cabinet" : "/");
  };

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={() => { setProfile(null); go("chat"); }} aria-label="На главную" title="На главную">
          <img className="logo" src="/logo.svg" alt="MORE TECH" />
          <span className="brand-sub">Агент по регламентам{meta ? ` · ${meta.company}` : ""}</span>
        </button>
        <nav className="switcher" aria-label="Раздел">
          <button className={view === "chat" ? "on" : ""} onClick={() => go("chat")}>
            Сотрудник
          </button>
          <button className={view === "cabinet" ? "on" : ""} onClick={() => go("cabinet")}>
            Служба качества
          </button>
        </nav>
        <div className="topbar-right">
          {profile && view === "chat" && (
            <button className="who" onClick={() => setProfile(null)} title="Сменить профиль">
              <span className="avatar sm">{profile.name.slice(0, 1)}</span>
              <span>{profile.name}</span>
              <span className="who-change">сменить</span>
            </button>
          )}
        </div>
      </header>
      {error && <div className="banner error">{error}</div>}
      <main className={view === "chat" && !profile ? "main hero-main" : "main"}>
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
