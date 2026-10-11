import StatusBadge from "./StatusBadge";

export default function Sidebar({ sessions, activeId, username, onSelect, onNew, onLogout }) {
  return (
    <aside className="w-64 shrink-0 h-screen bg-[var(--color-ink-raised)] border-r border-[var(--color-wire-soft)] flex flex-col">
      <div className="px-5 py-5 border-b border-[var(--color-wire-soft)] flex items-start justify-between">
        <div>
          <h1 className="font-display font-semibold text-lg tracking-tight">Sentinel</h1>
          <p className="text-xs text-[var(--color-ash)] mt-0.5">{username}</p>
        </div>
        <button
          onClick={onLogout}
          title="Log out"
          className="text-xs font-mono text-[var(--color-ash)] hover:text-[var(--color-fail)]
                     cursor-pointer transition-colors duration-200 mt-1"
        >
          logout
        </button>
      </div>

      <button
        onClick={onNew}
        className="mx-4 mt-4 mb-2 px-3 py-2 text-sm font-medium text-left rounded cursor-pointer
                   border border-[var(--color-wire)] text-[var(--color-paper)]
                   hover:border-[var(--color-signal)] hover:text-[var(--color-signal)]
                   active:scale-[0.98] transition-all duration-200"
      >
        + New session
      </button>

      <nav className="flex-1 overflow-y-auto px-2 mt-2">
        {sessions.length === 0 && (
          <p className="px-3 py-4 text-sm text-[var(--color-ash)]">
            No sessions yet. Start one above.
          </p>
        )}
        {sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`w-full text-left px-3 py-2.5 rounded mb-0.5 cursor-pointer
              transition-all duration-200 active:scale-[0.99]
              ${s.id === activeId
                ? "bg-[var(--color-ink)] border border-[var(--color-wire)]"
                : "hover:bg-[var(--color-ink)]/60 border border-transparent hover:border-[var(--color-wire-soft)]"}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs text-[var(--color-ash)]">#{s.id}</span>
              <StatusBadge status={s.status} />
            </div>
            <p className="text-sm mt-1 truncate">{s.target_input}</p>
          </button>
        ))}
      </nav>
    </aside>
  );
}
