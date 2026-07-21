/** Step 6 — the result. Download appears only when validation completes;
 * otherwise the blockers say exactly what's needed. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { downloadUrl, getProject, reopenSetup } from "../api/client";
import { ConfirmAction } from "../components/ConfirmAction";
import { Shell } from "../components/Shell";
import { ValidationReportView } from "../components/ValidationReportView";
import type { Project } from "../types/state";

export function DownloadPage() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const nav = useNavigate();

  useEffect(() => { getProject(id).then(setProject).catch(e => setError(String(e))); }, [id]);

  if (!project) {
    return <Shell><div className="empty"><div className="mark">···</div>
      {error || "Loading project"}</div></Shell>;
  }
  const done = project.meta.phase === "complete";
  // A failure here can mean two very different things: a planning crash
  // (pre-approval — setup can still be reopened) or a rebuild/validation
  // failure (post-approval — approval is a one-way gate, setup stays
  // locked). project.approval is the honest signal, not the phase name.
  const canReopen = project.meta.phase === "failed" && !project.approval;

  return (
    <Shell project={project}>
      <h1>{done ? "Edited sequence ready" : "Not finished yet"}</h1>
      <p className="page-sub">
        {done
          ? "Import the XML into your Premiere project to review the cut."
          : "The sequence becomes available when every check below is resolved."}
      </p>

      {done && project.output && (
        <div className="panel">
          <div className="actions" style={{ marginTop: 0 }}>
            <div>
              <div className="small dim">Edited sequence (Final Cut Pro XML)</div>
              <div className="mono faint small">sha256 {project.output.checksum_sha256}</div>
            </div>
            <span className="push" />
            <a className="btn btn-primary" href={downloadUrl(id)} download
               style={{ textDecoration: "none" }}>
              Download XML
            </a>
          </div>
        </div>
      )}

      {project.validation && <div className="section">
        <ValidationReportView report={project.validation} />
      </div>}

      {error && <div className="alert danger"><p>{error}</p></div>}

      {canReopen && (
        <div className="actions">
          <span className="push" />
          <ConfirmAction
            className="btn-quiet-danger"
            label="Back to setup"
            confirmLabel="Discard this plan and go back"
            message="This discards the failed plan so you can try again."
            onConfirm={async () => {
              try {
                await reopenSetup(id);
                nav(`/projects/${id}/setup`);
              } catch (e) { setError(String(e)); }
            }}
          />
        </div>
      )}

      {done && (
        <div className="alert">
          <h3>After import</h3>
          <p>Check the cut in Premiere: media relinks, clips play in order,
            audio stays in sync. Import safety is reported as a warning, never
            a certainty — the final check is always yours.</p>
        </div>
      )}
    </Shell>
  );
}
