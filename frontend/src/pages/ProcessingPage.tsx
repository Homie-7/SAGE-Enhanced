/** Poll while the canonical planning pipeline runs; route on when done. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, phaseRoute } from "../api/client";
import type { Project } from "../types/state";

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
    <main>
      <h1>Planning in progress</h1>
      <p>Phase: {project?.meta.phase ?? "…"}</p>
      <p>Running the canonical pipeline: audit → roster → classification →
        grouping → mode/structure → paper edit.</p>
    </main>
  );
}
