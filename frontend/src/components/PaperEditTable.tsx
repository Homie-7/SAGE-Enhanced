/**
 * The cutting log — canonical Paper Edit Table (file 03).
 * Locked beats carry a red left rule (the commitment mark); rejected beats
 * dim and strike. Uncertainty labels are shown verbatim, never hidden.
 */
import type { Beat } from "../types/state";

export function PaperEditTable({ beats, onStatus, readOnly }: {
  beats: Beat[];
  onStatus?: (bid: string, status: "locked" | "rejected" | "candidate") => void;
  readOnly?: boolean;
}) {
  return (
    <div className="table-wrap">
      <table className="sys">
        <thead>
          <tr>
            <th>Beat</th><th>Speaker</th><th>Function</th><th>Quote</th>
            <th>Est.</th><th>Confidence</th><th>Why keep</th><th>Flags</th>
            <th>Status</th>
            {!readOnly && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {beats.map(b => (
            <tr key={b.bid}
                className={b.status === "locked" ? "beat-locked"
                         : b.status === "rejected" ? "beat-rejected" : ""}>
              <td className="mono">{b.bid}</td>
              <td className="mono dim">{b.cid ?? "—"}</td>
              <td className="dim">{b.func}</td>
              <td className="quote">{b.exact_quote ?? b.quote_stub ?? "—"}</td>
              <td className="mono dim">{b.est_duration != null ? `${b.est_duration}s` : "—"}</td>
              <td className="dim small">{b.confidence ?? "—"}</td>
              <td className="why">{b.include_reason ?? "—"}</td>
              <td>
                {b.uncertainty_labels
                  .filter(l => l !== "HIGH_CONFIDENCE")
                  .map(l => <span key={l} className="flag">▲ {l}</span>)}
                {b.uncertainty_labels.every(l => l === "HIGH_CONFIDENCE") &&
                  <span className="faint">—</span>}
              </td>
              <td className="mono small"
                  style={b.status === "locked" ? { color: "var(--red-hover)" } : undefined}>
                {b.status}
              </td>
              {!readOnly && (
                <td>
                  <div className="beat-actions">
                    {b.status !== "locked" && b.status !== "rejected" ? (
                      <>
                        <button className="btn btn-secondary"
                                onClick={() => onStatus?.(b.bid, "locked")}>Lock</button>
                        <button className="btn btn-quiet-danger"
                                onClick={() => onStatus?.(b.bid, "rejected")}>Reject</button>
                      </>
                    ) : (
                      <button className="btn btn-ghost"
                              onClick={() => onStatus?.(b.bid, "candidate")}>Reopen</button>
                    )}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
