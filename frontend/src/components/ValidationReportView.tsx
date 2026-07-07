/** Structured validation report: pass/warn/fail per check, blockers explicit. */
import type { ValidationReport } from "../types/state";

export function ValidationReportView({ report }: { report: ValidationReport }) {
  return (
    <div className="panel">
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Validation</h2>
        <span className={"pill " + (report.overall === "pass" ? "ok"
                       : report.overall === "warn" ? "warn" : "danger")}>
          {report.overall}
        </span>
      </div>
      <ul className="check-list">
        {report.checks.map(c => (
          <li key={c.name}>
            <span className={"check-outcome " + c.outcome}>{c.outcome}</span>
            <span className="check-name">{c.name.replaceAll("_", " ")}</span>
            <span className="check-detail">{c.detail ?? ""}</span>
          </li>
        ))}
      </ul>
      {report.blockers.length > 0 && (
        <div className="alert danger">
          <h3>Blocked — what's needed</h3>
          {report.blockers.map((b, i) => (
            <p key={i}><strong>{b.check.replaceAll("_", " ")}</strong> — {b.why_it_blocks}
              <br />{b.what_is_needed}</p>
          ))}
        </div>
      )}
    </div>
  );
}
