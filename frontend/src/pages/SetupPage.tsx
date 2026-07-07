/** Quick setup — the compact kickoff question set; "infer" is the default everywhere. */
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { runPlanning, submitSetup } from "../api/client";

const field = (value: string) =>
  value ? { value, origin: "user" } : { value: null, origin: "default" };

export function SetupPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    runtime_target: "", tone: "", cut_style: "natural",
    opening: "", ending: "", must_keep: "", avoid: "", known_contributors: "",
  });
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });
  const list = (s: string) => s.split(",").map(x => x.trim()).filter(Boolean);

  const start = async () => {
    setBusy(true); setError("");
    try {
      await submitSetup(id, {
        runtime_target: field(form.runtime_target),
        tone: field(form.tone),
        cut_style: { value: form.cut_style, origin: "user" },
        opening: field(form.opening),
        ending: field(form.ending),
        must_keep: list(form.must_keep),
        avoid: list(form.avoid),
        known_contributors: list(form.known_contributors),
      });
      runPlanning(id).catch(() => { /* surfaced on the processing page */ });
      nav(`/projects/${id}/processing`);
    } catch (e) { setError(String(e)); setBusy(false); }
  };

  return (
    <main>
      <h1>Quick setup</h1>
      <p>Leave anything blank to let SAGE infer it (inference defaults, canonical file 02).</p>
      <p>Runtime target: <input value={form.runtime_target} onChange={set("runtime_target")} placeholder="infer (e.g. 90s)" /></p>
      <p>Tone: <input value={form.tone} onChange={set("tone")} placeholder="infer (e.g. warm)" /></p>
      <p>Cut style: <select value={form.cut_style} onChange={set("cut_style")}>
        {["conservative", "natural", "moderate", "punchy", "aggressive"].map(v =>
          <option key={v} value={v}>{v}{v === "natural" ? " (default)" : ""}</option>)}
      </select></p>
      <p>Opening: <input value={form.opening} onChange={set("opening")} placeholder="infer (e.g. value-first)" /></p>
      <p>Ending: <input value={form.ending} onChange={set("ending")} placeholder="infer (e.g. strongest resolved line)" /></p>
      <p>Must keep (comma-separated): <input value={form.must_keep} onChange={set("must_keep")} /></p>
      <p>Avoid (comma-separated): <input value={form.avoid} onChange={set("avoid")} /></p>
      <p>Known contributors (comma-separated): <input value={form.known_contributors} onChange={set("known_contributors")} /></p>
      {error && <p role="alert">{error}</p>}
      <button onClick={start} disabled={busy}>Run planning</button>
    </main>
  );
}
