/** Step 5 — rebuild after approval. The plan is machine-made; the timeline
 * is built deterministically from real source clips. Nothing is invented. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, triggerRebuild } from "../api/client";
import { Shell } from "../components/Shell";
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
    <Shell project={project}>
      <h1>Rebuild the sequence</h1>
      <p className="page-sub">The approved paper edit becomes an edited
        timeline, cut from your original source clips only.</p>

      <div className="panel">
        {busy && <div className="sweep" role="progressbar" aria-label="Rebuilding" />}
        <div className="actions" style={{ marginTop: busy ? 8 : 0 }}>
          <span className="dim small">
            {project?.meta.phase === "approved"
              ? "Approved and ready to rebuild."
              : `Phase: ${project?.meta.phase ?? "…"}`}
          </span>
          <span className="push" />
          <button className="btn btn-primary" onClick={rebuild}
                  disabled={busy || project?.meta.phase !== "approved"}>
            {busy ? "Rebuilding…" : "Rebuild edited sequence"}
          </button>
        </div>
      </div>

      {project?.validation && <div className="section">
        <ValidationReportView report={project.validation} />
      </div>}

      {error && <div className="alert danger">
        <h3>Rebuild stopped</h3>
        <p style={{ whiteSpace: "pre-wrap" }}>{error}</p>
      </div>}
    </Shell>
  );
}
