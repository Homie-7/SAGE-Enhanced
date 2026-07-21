/** Step 3 — planning runs in the background; this page keeps calm and polls. */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, phaseRoute, reopenSetup } from "../api/client";
import { ConfirmAction } from "../components/ConfirmAction";
import { Shell } from "../components/Shell";
import type { Project } from "../types/state";

const PIPELINE = [
  "Audit the source timeline",
  "Identify contributors",
  "Classify the material",
  "Group by function",
  "Choose mode and structure",
  "Draft the paper edit",
];

export function ProcessingPage() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const nav = useNavigate();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    timerRef.current = setInterval(async () => {
      try {
        const p = await getProject(id);
        setProject(p);
        if (!["setup_complete", "analysing"].includes(p.meta.phase)) {
          if (timerRef.current) clearInterval(timerRef.current);
          nav(phaseRoute(p));
        }
      } catch { /* keep polling */ }
    }, 1500);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [id, nav]);

  const done = project?.meta.planning_progress ?? 0;
  const pct = Math.round((done / PIPELINE.length) * 100);

  return (
    <Shell project={project}>
      <h1>Planning the cut</h1>
      <p className="page-sub">SAGE is reading the timeline and transcript.
        This can take a few minutes; the page moves on by itself.</p>
      <div className="panel">
        <div className="progress-track" role="progressbar" aria-label="Planning progress"
             aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <ul className="task-list">
          {PIPELINE.map((step, i) => (
            <li key={step} className={i < done ? "done" : i === done ? "current" : ""}>
              {i < done ? "✓ " : ""}{step}
            </li>
          ))}
        </ul>
      </div>

      {error && <div className="alert danger"><p>{error}</p></div>}

      <div className="actions">
        <span className="push" />
        <ConfirmAction
          className="btn-quiet-danger"
          label="Back to setup"
          confirmLabel="Stop and go back"
          message="This stops the current analysis and discards this plan."
          onConfirm={async () => {
            if (timerRef.current) clearInterval(timerRef.current);
            try {
              await reopenSetup(id);
              nav(`/projects/${id}/setup`);
            } catch (e) { setError(String(e)); }
          }}
        />
      </div>
    </Shell>
  );
}
