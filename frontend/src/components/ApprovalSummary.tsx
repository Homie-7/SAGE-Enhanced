/** Compact approval gate summary (file 03): Mode / Runtime / Tone / Cut /
 * Contributors / Clarity / Main risks — then the explicit approval action. */
import type { Project } from "../types/state";

const val = (f: unknown) =>
  f && typeof f === "object" && "value" in (f as object)
    ? ((f as { value: string | null; origin: string }).value ?? "inferred")
      + ((f as { origin: string }).origin !== "user" ? ` (${(f as { origin: string }).origin})` : "")
    : "—";

export function ApprovalSummary({ project }: { project: Project }) {
  const beats = project.paper_edit?.beats ?? [];
  const kept = beats.filter(b => b.status !== "rejected");
  const risks = [...new Set(kept.flatMap(b => b.uncertainty_labels))]
    .filter(l => l !== "HIGH_CONFIDENCE");
  const dur = kept.reduce((s, b) => s + (b.est_duration ?? 0), 0);
  return (
    <div style={{ border: "1px solid #999", padding: "0.5em 1em", margin: "1em 0" }}>
      <h3>Approval summary</h3>
      <p>Mode: <strong>{project.structure?.mode ?? "—"}</strong>
        {" · "}Cut: {val(project.setup["cut_style"])}
        {" · "}Runtime target: {val(project.setup["runtime_target"])}
        {" · "}Estimated: ~{Math.round(dur)}s
        {" · "}Tone: {val(project.setup["tone"])}</p>
      <p>Beats: {kept.length} kept / {beats.length - kept.length} rejected
        {" · "}Contributors: {project.roster.filter(c => c.status === "keep").length} keep
        {project.roster.some(c => c.confidence === "IDENTITY_UNCERTAIN") &&
          <strong> · ⚠ identity uncertainty in roster</strong>}</p>
      {risks.length > 0 && <p>Main risks (accepted on approval): {risks.join(", ")}</p>}
      <p><em>Approval locks every non-rejected beat and resolves exact quotes
        from the transcript. Rebuild is refused before approval.</em></p>
    </div>
  );
}
