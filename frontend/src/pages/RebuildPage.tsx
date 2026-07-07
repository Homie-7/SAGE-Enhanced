/** Trigger the deterministic rebuild after approval; show the validation result. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, triggerRebuild } from "../api/client";
import { ValidationReportView } from "../components/ValidationReportView";
import type { Project } from "../types/state";

export function RebuildPage() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const nav = useNavigate();

  useEffect(() => { getProject(id).then(setProject).catch(e => setError(String(e))); }, [id]);

  const rebuild = async () => {
    setBusy(true); setError("");
    try {
      const p = await triggerRebuild(id);
      setProject(p);
      if (p.meta.phase === "complete") nav(`/projects/${id}/download`);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };

  return (
    <main>
      <h1>Rebuild — {project?.meta.name}</h1>
      <p>Phase: {project?.meta.phase}. The LLM plans the rebuild; deterministic
        code builds the XML from real source clips (Style B). Nothing is
        invented.</p>
      <button onClick={rebuild} disabled={busy || project?.meta.phase !== "approved"}>
        {busy ? "Rebuilding…" : "Rebuild edited XML"}
      </button>
      {project?.validation && <ValidationReportView report={project.validation} />}
      {error && <p role="alert" style={{ whiteSpace: "pre-wrap" }}>{error}</p>}
    </main>
  );
}
