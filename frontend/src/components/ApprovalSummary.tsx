/** Compact approval-gate summary (file 03): the facts an approver signs off. */
import type { Project } from "../types/state";

const val = (f: unknown): { text: string; origin?: string } => {
  if (f && typeof f === "object" && "value" in (f as object)) {
    const field = f as { value: string | null; origin: string };
    return {
      text: field.value ?? "inferred",
      origin: field.origin !== "user" ? field.origin : undefined,
    };
  }
  return { text: "—" };
};

export function ApprovalSummary({ project }: { project: Project }) {
  const beats = project.paper_edit?.beats ?? [];
  const kept = beats.filter(b => b.status !== "rejected");
  const risks = [...new Set(kept.flatMap(b => b.uncertainty_labels))]
    .filter(l => l !== "HIGH_CONFIDENCE");
  const dur = kept.reduce((s, b) => s + (b.est_duration ?? 0), 0);
  const uncertainIds = project.roster.some(c => c.confidence === "IDENTITY_UNCERTAIN");
  const cells: { k: string; v: string; origin?: string }[] = [
    { k: "Mode", v: project.structure?.mode ?? "—" },
    { k: "Cut style", ...toCell(val(project.setup["cut_style"])) },
    { k: "Runtime target", ...toCell(val(project.setup["runtime_target"])) },
    { k: "Estimated", v: `~${Math.round(dur)}s` },
    { k: "Tone", ...toCell(val(project.setup["tone"])) },
    { k: "Beats", v: `${kept.length} kept · ${beats.length - kept.length} rejected` },
  ];
  return (
    <div className="section">
      <h2>Approval summary</h2>
      <div className="summary-grid">
        {cells.map(c => (
          <div key={c.k} className="summary-cell">
            <div className="k">{c.k}</div>
            <div className="v">{c.v}{" "}
              {c.origin && <span className="origin">({c.origin})</span>}
            </div>
          </div>
        ))}
      </div>
      {(risks.length > 0 || uncertainIds) && (
        <div className="alert warn">
          <h3>Accepted on approval</h3>
          {risks.length > 0 && <p>Open risks: {risks.join(", ")}</p>}
          {uncertainIds && <p>The roster contains unresolved speaker identities.</p>}
        </div>
      )}
      <p className="small faint" style={{ marginTop: 14 }}>
        Approving locks every kept beat and resolves its exact wording from the
        transcript. Rebuild stays unavailable until approval.
      </p>
    </div>
  );
}

function toCell(v: { text: string; origin?: string }) {
  return { v: v.text, origin: v.origin };
}
