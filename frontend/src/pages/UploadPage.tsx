/** XML + transcript (+ optional notes) upload. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, uploadInput } from "../api/client";
import type { Project } from "../types/state";

export function UploadPage() {
  const { id = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const nav = useNavigate();

  useEffect(() => { getProject(id).then(setProject).catch(e => setError(String(e))); }, [id]);

  const upload = (kind: "xml" | "transcript" | "notes") =>
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try { setProject(await uploadInput(id, kind, file)); setError(""); }
      catch (err) { setError(String(err)); }
    };

  const has = (kind: string) =>
    (project?.inputs as { kind: string; filename: string }[] | undefined)
      ?.find(f => f.kind === kind);

  return (
    <main>
      <h1>Upload sources — {project?.meta.name}</h1>
      <p>Synced source XML (Premiere/FCP7 export): <input type="file" accept=".xml" onChange={upload("xml")} />
        {has("xml") && <em> ✓ {has("xml")!.filename}</em>}</p>
      <p>Transcript (timecoded): <input type="file" onChange={upload("transcript")} />
        {has("transcript") && <em> ✓ {has("transcript")!.filename}</em>}</p>
      <p>Notes (optional): <input type="file" onChange={upload("notes")} />
        {has("notes") && <em> ✓ {has("notes")!.filename}</em>}</p>
      {error && <p role="alert">{error}</p>}
      <button disabled={project?.meta.phase !== "inputs_uploaded"}
              onClick={() => nav(`/projects/${id}/setup`)}>
        Continue to quick setup
      </button>
    </main>
  );
}
