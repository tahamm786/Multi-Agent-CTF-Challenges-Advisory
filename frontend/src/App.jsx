import { useEffect, useState, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import EventFeed from "./components/EventFeed";
import StatusBadge from "./components/StatusBadge";
import NewSessionForm from "./components/NewSessionForm";
import AuthForm from "./components/AuthForm";
import { listSessions, getSession, createSession, streamSession } from "./api/client";

export default function App() {
  const [username, setUsername] = useState(() => localStorage.getItem("sentinel_username"));
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [events, setEvents] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [loadError, setLoadError] = useState(null);

  // Load the session list once we have a logged-in user.
  useEffect(() => {
    if (!username) return;
    listSessions()
      .then((res) => {
        setSessions(res.data);
        if (res.data.length > 0) setActiveId(res.data[0].id);
        else setShowForm(true);
      })
      .catch(() => setLoadError("Couldn't reach the backend. Is Django running on :8000?"));
  }, [username]);

  const handleLogout = () => {
    localStorage.removeItem("sentinel_token");
    localStorage.removeItem("sentinel_username");
    setUsername(null);
    setSessions([]);
    setActiveId(null);
    setActiveSession(null);
  };

  if (!username) {
    return <AuthForm onAuthenticated={setUsername} />;
  }

  // Whenever the active session changes: fetch its current state, and if it's
  // still running, open a live SSE connection; otherwise just show its events.
  useEffect(() => {
    if (!activeId) return;
    let cleanupStream = null;

    getSession(activeId).then((res) => {
      setActiveSession(res.data);
      setEvents(res.data.events || []);

      if (res.data.status === "running" || res.data.status === "pending") {
        cleanupStream = streamSession(
          activeId,
          (event) => setEvents((prev) => [...prev, event]),
          () => {
            // session finished while we were watching -- refresh full state
            getSession(activeId).then((r) => {
              setActiveSession(r.data);
              setSessions((prev) =>
                prev.map((s) => (s.id === activeId ? { ...s, status: r.data.status } : s))
              );
            });
          }
        );
      }
    });

    return () => cleanupStream?.();
  }, [activeId]);

  const handleCreate = useCallback(async (payload) => {
    const res = await createSession(payload);
    setSessions((prev) => [res.data, ...prev]);
    setActiveId(res.data.id);
    setShowForm(false);
  }, []);

  if (loadError) {
    return (
      <div className="h-screen flex items-center justify-center font-mono text-sm text-[var(--color-fail)]">
        {loadError}
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        username={username}
        onSelect={(id) => {
          setActiveId(id);
          setShowForm(false);
        }}
        onNew={() => setShowForm(true)}
        onLogout={handleLogout}
      />

      <main className="flex-1 overflow-y-auto px-10 py-8">
        {showForm && (
          <NewSessionForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />
        )}

        {!showForm && activeSession && (
          <>
            <div className="flex items-start justify-between mb-8">
              <div>
                <p className="text-xs font-mono text-[var(--color-ash)] mb-1">TARGET</p>
                <h2 className="font-display text-xl font-medium break-all max-w-2xl">
                  {activeSession.target_input}
                </h2>
              </div>
              <StatusBadge status={activeSession.status} />
            </div>

            <EventFeed events={events} />

            {activeSession.final_report && (
              <div className="mt-10 pt-8 border-t border-[var(--color-wire-soft)]">
                <p className="text-xs font-mono text-[var(--color-ash)] mb-3">FINAL REPORT</p>
                <pre className="whitespace-pre-wrap font-display text-sm leading-relaxed text-[var(--color-paper)]/90">
                  {activeSession.final_report}
                </pre>
              </div>
            )}
          </>
        )}

        {!showForm && !activeSession && (
          <div className="relative h-full min-h-[60vh] rounded overflow-hidden">
            <div className="dot-field absolute inset-0 pointer-events-none" />
            <div className="relative flex items-center justify-center h-full">
              <p className="text-sm text-[var(--color-ash)] font-mono">Select a session.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
