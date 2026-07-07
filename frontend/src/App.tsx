/**
 * SAGE Internal V1 — core loop shell.
 * Route order mirrors the canonical workflow:
 * upload → setup → processing → review → rebuild → download
 */
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ProjectsPage } from "./pages/ProjectsPage";
import { UploadPage } from "./pages/UploadPage";
import { SetupPage } from "./pages/SetupPage";
import { ProcessingPage } from "./pages/ProcessingPage";
import { ReviewPage } from "./pages/ReviewPage";
import { RebuildPage } from "./pages/RebuildPage";
import { DownloadPage } from "./pages/DownloadPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/projects" replace />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id/upload" element={<UploadPage />} />
        <Route path="/projects/:id/setup" element={<SetupPage />} />
        <Route path="/projects/:id/processing" element={<ProcessingPage />} />
        <Route path="/projects/:id/review" element={<ReviewPage />} />
        <Route path="/projects/:id/rebuild" element={<RebuildPage />} />
        <Route path="/projects/:id/download" element={<DownloadPage />} />
      </Routes>
    </BrowserRouter>
  );
}
