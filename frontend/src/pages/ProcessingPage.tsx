/** Step 3 — planning runs in the background; this page keeps calm and polls. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, phaseRoute } from "../api/client";
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
  const nav = useNavigate();

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const p = await getProject(id);
        setProject(p);
        if (!["setup_complete", "analysing"].includes(p.meta.phase)) {
          clearInterval(timer);
          nav(phaseRoute(p));
        }
      } catch { /* keep polling */ }
    }, 1500);
    return () => clearInterval(timer);
  }, [id, nav]);

  return (
    <Shell project={project}>
      <h1>Planning the cut</h1>
      <p className="page-sub">SAGE is reading the timeline and transcript.
        This can take a few minutes; the page moves on by itself.</p>
      <div className="panel">
        <div className="sweep" role="progressbar" aria-label="Planning in progress" />
        <ul className="task-list">
          {PIPELINE.map(step => <li key={step}>{step}</li>)}
        </ul>
      </div>
    </Shell>
  );
}
