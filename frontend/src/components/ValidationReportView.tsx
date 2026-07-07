/** Structured validation report: pass/warn/fail per check, explicit blockers. */
import type { ValidationReport } from "../types/state";

const COLOUR = { pass: "#2e7d32", warn: "#b26a00", fail: "#c62828" } as const;

export function ValidationReportView({ report }: { report: ValidationReport }) {
  return (
    <div>
      <h3>Validation — overall:{" "}
        <span style={{ color: COLOUR[report.overall] }}>{report.overall.toUpperCase()}</span></h3>
      <ul>
        {report.checks.map(c => (
          <li key={c.name}>
            <span style={{ color: COLOUR[c.outcome] }}>[{c.outcome}]</span>{" "}
            <strong>{c.name}</strong>{c.detail ? ` — ${c.detail}` : ""}
          </li>
        ))}
      </ul>
      {report.blockers.length > 0 && (
        <div style={{ border: "2px solid #c62828", padding: "0.5em 1em" }}>
          <h4>Blockers</h4>
          {report.blockers.map((b, i) => (
            <p key={i}><strong>{b.check}</strong><br />
              Why it blocks: {b.why_it_blocks}<br />
              What is needed: {b.what_is_needed}</p>
          ))}
        </div>
      )}
    </div>
  );
}
