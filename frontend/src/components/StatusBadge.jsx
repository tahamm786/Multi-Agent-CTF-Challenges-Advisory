const STYLES = {
  pending: { color: "var(--color-pending)", label: "pending" },
  running: { color: "var(--color-signal)", label: "running" },
  solved:  { color: "var(--color-ok)",      label: "solved" },
  failed:  { color: "var(--color-fail)",    label: "failed" },
  rejected:{ color: "var(--color-pending)", label: "rejected" },
};

export default function StatusBadge({ status }) {
  const s = STYLES[status] || STYLES.pending;
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-xs">
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: s.color }}
      />
      <span style={{ color: s.color }}>{s.label}</span>
    </span>
  );
}
