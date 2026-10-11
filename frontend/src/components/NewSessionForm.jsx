import { useState } from "react";

export default function NewSessionForm({ onSubmit, onCancel }) {
  const [targetInput, setTargetInput] = useState("");
  const [contextNotes, setContextNotes] = useState("");
  const [overallGoal, setOverallGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!targetInput.trim() || submitting) return;
    setSubmitting(true);
    try {
      await onSubmit({
        target_input: targetInput,
        context_notes: contextNotes,
        overall_goal: overallGoal,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-xl bg-[var(--color-ink-raised)] border border-[var(--color-wire)] rounded p-6"
    >
      <h2 className="font-display text-lg font-medium mb-5">New session</h2>

      <label className="block text-xs font-mono text-[var(--color-ash)] mb-1.5">
        Target
      </label>
      <textarea
        value={targetInput}
        onChange={(e) => setTargetInput(e.target.value)}
        placeholder="URL, ciphertext, file reference, hash..."
        rows={3}
        required
        className="w-full bg-[var(--color-ink)] border border-[var(--color-wire)] rounded px-3 py-2
                   font-mono text-sm text-[var(--color-paper)] placeholder:text-[var(--color-ash)]
                   focus:border-[var(--color-signal)] outline-none transition-colors duration-200 mb-4 resize-none"
      />

      <label className="block text-xs font-mono text-[var(--color-ash)] mb-1.5">
        Context notes <span className="text-[var(--color-pending)]">(optional)</span>
      </label>
      <textarea
        value={contextNotes}
        onChange={(e) => setContextNotes(e.target.value)}
        placeholder="Known credentials, hints, prior progress..."
        rows={2}
        className="w-full bg-[var(--color-ink)] border border-[var(--color-wire)] rounded px-3 py-2
                   font-mono text-sm text-[var(--color-paper)] placeholder:text-[var(--color-ash)]
                   focus:border-[var(--color-signal)] outline-none transition-colors duration-200 mb-4 resize-none"
      />

      <label className="block text-xs font-mono text-[var(--color-ash)] mb-1.5">
        Overall goal <span className="text-[var(--color-pending)]">(optional)</span>
      </label>
      <input
        value={overallGoal}
        onChange={(e) => setOverallGoal(e.target.value)}
        placeholder="Leave blank to let the team decide"
        className="w-full bg-[var(--color-ink)] border border-[var(--color-wire)] rounded px-3 py-2
                   font-mono text-sm text-[var(--color-paper)] placeholder:text-[var(--color-ash)]
                   focus:border-[var(--color-signal)] outline-none transition-colors duration-200 mb-6"
      />

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 text-sm font-medium rounded bg-[var(--color-signal)] text-[var(--color-ink)]
                     cursor-pointer hover:opacity-90 active:scale-[0.98]
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          {submitting ? "Starting..." : "Start session"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-[var(--color-ash)] hover:text-[var(--color-paper)] cursor-pointer transition-colors duration-200"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
