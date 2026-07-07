/** Final validation report + download of the edited XML (refused unless complete). */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { downloadUrl, getProject } from "../api/client";
import { ValidationReportView } from "../components/ValidationReportView";
import type { Project } from "../types/state";

export function DownloadPage() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");

  useEffect(() => { getProject(id).then(setProject).catch(e => setError(String(e))); }, [id]);
  if (!project) return <main><p>{error || "Loading…"}</p></main>;

  const done = project.meta.phase === "complete";
  return (
    <main>
      <h1>{done ? "Complete" : "Not complete"} — {project.meta.name}</h1>
      {project.validation && <ValidationReportView report={project.validation} />}
      {done && project.output && (
        <p>
          <a href={downloadUrl(id)} download>Download edited XML</a>
          <br /><small>sha256 {project.output.checksum_sha256}</small>
        </p>
      )}
      {done && (
        <p><em>Import check happens in Premiere — validation reports import
          safety as a warning, never a certainty (file 05).</em></p>
      )}
      {!done && <p>The edited XML becomes available only when the project
        reaches <code>complete</code>. Blockers above say exactly what is needed.</p>}
    </main>
  );
}
