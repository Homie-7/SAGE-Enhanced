/**
 * A button that requires an inline confirm before it fires — for actions
 * that discard real state (reopening setup mid-plan, deleting a project).
 * Deliberately not a native `confirm()` dialog: it matches the app's own
 * styling instead of a jarring browser popup.
 */
import { useState } from "react";

export function ConfirmAction({
  label,
  confirmLabel = "Confirm",
  message,
  onConfirm,
  className = "btn btn-secondary",
  disabled,
}: {
  label: string;
  confirmLabel?: string;
  message: string;
  onConfirm: () => void | Promise<void>;
  className?: string;
  disabled?: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!confirming) {
    return (
      <button className={className} disabled={disabled}
              onClick={() => setConfirming(true)}>
        {label}
      </button>
    );
  }

  return (
    <span className="confirm-inline">
      <span className="small dim">{message}</span>
      <button
        className="btn btn-quiet-danger"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try { await onConfirm(); } finally { setBusy(false); setConfirming(false); }
        }}
      >
        {confirmLabel}
      </button>
      <button className="btn btn-ghost" disabled={busy} onClick={() => setConfirming(false)}>
        Cancel
      </button>
    </span>
  );
}
