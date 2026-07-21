/**
 * App shell: top bar + the gated workflow rail.
 *
 * The rail is the product's core truth drawn as interface: the canonical
 * sequence with a hard human gate before Rebuild. The line fills red as
 * phases complete; the gate tick turns red only after approval.
 *
 * Every reached step is a plain navigation link — visiting a past step is
 * always safe, since each page just re-fetches live project state. This is
 * pure viewing/navigation, not an action: the one action that actually
 * changes state (reopening setup) lives as its own explicit, confirmed
 * button on the Processing and Download pages, not squeezed into these
 * small rail nodes.
 */
import { Link } from "react-router-dom";
import type { Project, ProjectPhase } from "../types/state";

const STEPS: { label: string; path: string; phases: ProjectPhase[] }[] = [
  { label: "Upload", path: "upload", phases: ["created"] },
  { label: "Setup", path: "setup", phases: ["inputs_uploaded"] },
  { label: "Plan", path: "processing", phases: ["setup_complete", "analysing"] },
  { label: "Review", path: "review", phases: ["paper_edit_ready", "in_review", "revising"] },
  { label: "Rebuild", path: "rebuild", phases: ["approved", "rebuilding", "validating"] },
  { label: "Deliver", path: "download", phases: ["complete", "failed"] },
];
const GATE_AFTER = 3; // gate sits between Review and Rebuild

function stepIndex(phase: ProjectPhase): number {
  return STEPS.findIndex(s => s.phases.includes(phase));
}

export function WorkflowRail({ project }: { project: Project }) {
  const phase = project.meta.phase;
  const current = stepIndex(phase);
  const delivered = phase === "complete";

  return (
    <nav className="rail" aria-label="Workflow">
      {STEPS.map((step, i) => {
        const reached = i <= current;
        const label = i < current || (i === current && delivered) ? "✓" : String(i + 1);
        return (
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
              {reached ? (
                <Link className="rail-node rail-node-link"
                      to={`/projects/${project.meta.id}/${step.path}`}>
                  {label}
                </Link>
              ) : (
                <div className="rail-node">{label}</div>
              )}
              <div className="rail-label">{step.label}</div>
            </div>
          </div>
        );
      })}
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
        {project && <WorkflowRail project={project} />}
        {children}
      </div>
    </>
  );
}
