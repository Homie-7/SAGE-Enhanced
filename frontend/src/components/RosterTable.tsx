/** Contributor Roster (file 02): IDENTITY_UNCERTAIN must be visually prominent. */
import type { Contributor } from "../types/state";

export function RosterTable({ roster }: { roster: Contributor[] }) {
  if (!roster.length) return null;
  return (
    <table border={1} cellPadding={4} style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr><th>CID</th><th>Label</th><th>Role</th><th>Source</th><th>Confidence</th><th>Status</th><th>Notes</th></tr>
      </thead>
      <tbody>
        {roster.map(c => {
          const uncertain = c.confidence === "IDENTITY_UNCERTAIN";
          return (
            <tr key={c.cid} style={uncertain ? { background: "#fff3cd" } : undefined}>
              <td>{c.cid}</td>
              <td>{c.label}</td>
              <td>{c.role ?? "—"}</td>
              <td>{c.source ?? "—"}</td>
              <td>{uncertain ? <strong>⚠ IDENTITY_UNCERTAIN</strong> : (c.confidence ?? "—")}</td>
              <td>{c.status}</td>
              <td>{[c.value_note, c.ambiguity_note].filter(Boolean).join(" · ") || "—"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
