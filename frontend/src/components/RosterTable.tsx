/** Contributor roster (file 02). Identity uncertainty is prominent, never hidden. */
import type { Contributor } from "../types/state";

export function RosterTable({ roster }: { roster: Contributor[] }) {
  if (!roster.length) return null;
  return (
    <div className="table-wrap">
      <table className="sys">
        <thead>
          <tr><th>ID</th><th>Label</th><th>Role</th><th>Source</th>
              <th>Confidence</th><th>Status</th><th>Notes</th></tr>
        </thead>
        <tbody>
          {roster.map(c => {
            const uncertain = c.confidence === "IDENTITY_UNCERTAIN";
            return (
              <tr key={c.cid}>
                <td className="mono">{c.cid}</td>
                <td>{c.label}</td>
                <td className="dim">{c.role ?? "—"}</td>
                <td className="dim small">{c.source ?? "—"}</td>
                <td>{uncertain
                  ? <span className="flag">▲ IDENTITY_UNCERTAIN</span>
                  : <span className="dim small">{c.confidence ?? "—"}</span>}
                </td>
                <td className="mono small">{c.status}</td>
                <td className="dim small">
                  {[c.value_note, c.ambiguity_note].filter(Boolean).join(" · ") || "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
