/**
 * App shell: top bar + the gated workflow rail.
 *
 * The rail is the product's core truth drawn as interface: the canonical
 * sequence with a hard human gate before Rebuild. The line fills red as
 * phases complete; the gate tick turns red only after approval.
 */
import { Link } from "react-router-dom";
import type { Project, ProjectPhase } from "../types/state";

const STEPS: { label: string; phases: ProjectPhase[] }[] = [
  { label: "Upload", phases: ["created"] },
  { label: "Setup", phases: ["inputs_uploaded"] },
  { label: "Plan", phases: ["setup_complete", "analysing"] },
  { label: "Review", phases: ["paper_edit_ready", "in_review", "revising"] },
  { label: "Rebuild", phases: ["approved", "rebuilding", "validating"] },
  { label: "Deliver", phases: ["complete", "failed"] },
];
const GATE_AFTER = 3; // gate sits between Review and Rebuild

function stepIndex(phase: ProjectPhase): number {
  return STEPS.findIndex(s => s.phases.includes(phase));
}

export function WorkflowRail({ phase }: { phase: ProjectPhase }) {
  const current = stepIndex(phase);
  const delivered = phase === "complete";
  return (
    <nav className="rail" aria-label="Workflow">
      {STEPS.map((step, i) => (
        <div key={step.label} style={{ display: "contents" }}>
          {i > 0 && i !== GATE_AFTER + 1 && (
            <div className={"rail-line" + (i <= current ? " filled" : "")} />
          )}
          {i === GATE_AFTER + 1 && (
            <>
              <div className={"rail-line" + (i <= current ? " filled" : "")} />
              <div className={"rail-gate" + (current > GATE_AFTER ? " passed" : "")}
                   title="Rebuild requires an approved paper edit" />
              <div className={"rail-line" + (i <= current ? " filled" : "")} />
            </>
          )}
          <div className={
            "rail-step" +
            (i < current || (i === current && delivered) ? " done" :
             i === current ? " current" : "")
          }>
            <div className="rail-node">
              {i < current || (i === current && delivered) ? "✓" : i + 1}
            </div>
            <div className="rail-label">{step.label}</div>
          </div>
        </div>
      ))}
    </nav>
  );
}

export function Shell({ project, adminMode, children }: {
  project?: Project | null;
  adminMode?: boolean;
  children: React.ReactNode;
}) {
  return (
    <>
      <header className="topbar">
        <Link to="/projects" className="wordmark">SAGE</Link>
        {project && <span className="crumb">{project.meta.name}</span>}
        <span className="spacer" />
        {adminMode && <span className="admin-tag">Admin</span>}
      </header>
      <div className="shell page-enter">
        {project && <WorkflowRail phase={project.meta.phase} />}
        {children}
      </div>
    </>
  );
}
