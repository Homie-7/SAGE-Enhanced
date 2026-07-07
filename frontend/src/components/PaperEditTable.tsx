/**
 * Canonical Paper Edit Table (file 03): BID, src, CID, role, func, quote,
 * dur, boundary, conf, why_keep, status — with per-beat lock / reject /
 * reopen controls. Uncertainty labels shown verbatim, never hidden.
 */
import type { Beat } from "../types/state";

const RISKY = new Set(["IDENTITY_UNCERTAIN", "SENTENCE_SEAM_RISK", "CONTINUITY_RISK", "BALANCE_RISK"]);

export function PaperEditTable({ beats, onStatus, readOnly }: {
  beats: Beat[];
  onStatus?: (bid: string, status: "locked" | "rejected" | "candidate") => void;
  readOnly?: boolean;
}) {
  return (
    <table border={1} cellPadding={4} style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr>
          <th>BID</th><th>CID</th><th>Function</th><th>Quote</th><th>~s</th>
          <th>Boundary</th><th>Conf</th><th>Why keep</th><th>Flags</th><th>Status</th>
          {!readOnly && <th>Actions</th>}
        </tr>
      </thead>
      <tbody>
        {beats.map(b => (
          <tr key={b.bid} style={b.status === "rejected" ? { opacity: 0.45, textDecoration: "line-through" } : undefined}>
            <td>{b.bid}</td>
            <td>{b.cid ?? "—"}</td>
            <td>{b.func}</td>
            <td style={{ maxWidth: 340 }}>{b.exact_quote ?? b.quote_stub ?? "—"}</td>
            <td>{b.est_duration ?? "—"}</td>
            <td>{b.boundary_status ?? "—"}</td>
            <td>{b.confidence ?? "—"}</td>
            <td style={{ maxWidth: 220 }}>{b.include_reason ?? "—"}</td>
            <td>
              {b.uncertainty_labels.map(l => (
                <div key={l} style={RISKY.has(l) ? { fontWeight: "bold" } : undefined}>⚠ {l}</div>
              ))}
            </td>
            <td><strong>{b.status}</strong></td>
            {!readOnly && (
              <td>
                {b.status !== "locked" && b.status !== "rejected" && (
                  <>
                    <button onClick={() => onStatus?.(b.bid, "locked")}>Lock</button>{" "}
                    <button onClick={() => onStatus?.(b.bid, "rejected")}>Reject</button>
                  </>
                )}
                {(b.status === "locked" || b.status === "rejected") && (
                  <button onClick={() => onStatus?.(b.bid, "candidate")}>Reopen</button>
                )}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
