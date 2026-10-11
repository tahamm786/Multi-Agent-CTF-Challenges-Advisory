const AGENT_COLOR = {
  Coordinator: "var(--color-signal)",
  Recon: "var(--color-ash)",
  "Web Exploit": "var(--color-ok)",
  Crypto: "var(--color-fail)",
  Forensics: "var(--color-pending)",
  Binary: "var(--color-paper)",
};

function EventLine({ event }) {
  const color = AGENT_COLOR[event.agent_name] || "var(--color-ash)";

  if (event.event_type === "handoff") {
    return (
      <div className="event-line flex items-center gap-3 my-4">
        <div className="h-px flex-1 bg-[var(--color-wire-soft)]" />
        <span
          className="font-mono text-xs uppercase tracking-wide"
          style={{ color }}
        >
          {event.content}
        </span>
        <div className="h-px flex-1 bg-[var(--color-wire-soft)]" />
      </div>
    );
  }

  const prefix = { tool_call: ">", tool_result: "<", agent_started: "*", agent_finished: "=" }[
    event.event_type
  ] || "-";

  return (
    <div className="event-line flex gap-3 py-1 font-mono text-sm leading-relaxed">
      <span style={{ color }} className="shrink-0 w-5 text-right">{prefix}</span>
      <span className="text-[var(--color-ash)] shrink-0">[{event.agent_name}]</span>
      <span className="text-[var(--color-paper)]/90 break-all">{event.content}</span>
    </div>
  );
}

export default function EventFeed({ events }) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-[var(--color-ash)] font-mono">
        waiting for the first event...
      </p>
    );
  }
  return (
    <div className="space-y-0">
      {events.map((e, i) => (
        <EventLine key={i} event={e} />
      ))}
    </div>
  );
}
