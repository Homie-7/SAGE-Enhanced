/**
 * First-run intro: what SAGE is, shown once per browser. Purely local
 * (localStorage-gated) — no backend involvement, no account concept.
 */
import { useState } from "react";

const SEEN_KEY = "sage_welcome_seen";

export function WelcomeModal() {
  const [open, setOpen] = useState(() => !localStorage.getItem(SEEN_KEY));

  if (!open) return null;

  const dismiss = () => {
    localStorage.setItem(SEEN_KEY, "1");
    setOpen(false);
  };

  return (
    <div className="modal-overlay" onClick={dismiss}>
      <div className="modal-panel" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="modal-eyebrow">SAGE</div>
        <h2>Story Assembly &amp; Guidance Engine</h2>
        <p>
          SAGE takes a synced timeline and transcript, then structures an
          editorial paper edit for your review — audit, roster, grouping,
          structure, and a full beat-by-beat cut proposal.
        </p>
        <p className="dim">
          It does not replace the editor. Nothing rebuilds until you
          approve it, and every step is yours to lock, reject, or redo.
        </p>
        <div className="actions" style={{ marginTop: 20 }}>
          <span className="push" />
          <button className="btn btn-primary" onClick={dismiss}>Got it</button>
        </div>
      </div>
    </div>
  );
}
