/** Step 6 — the result. Download appears only when validation completes;
 * otherwise the blockers say exactly what's needed. */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { downloadUrl, getProject } from "../api/client";
import { Shell } from "../components/Shell";
import { ValidationReportView } from "../components/ValidationReportView";
import type { Project } from "../types/state";

export function DownloadPage() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");

  useEffect(() => { getProject(id).then(setProject).catch(e => setError(String(e))); }, [id]);

  if (!project) {
    return <Shell><div className="empty"><div className="mark">···</div>
      {error || "Loading project"}</div></Shell>;
  }
  const done = project.meta.phase === "complete";

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
