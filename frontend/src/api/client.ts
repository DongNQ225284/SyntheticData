import type {
  JobDetail,
  TemplateV2,
  ValidationResult,
  WorkingTemplateSnapshot
} from "../types/contracts";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail: unknown = undefined;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    throw detail;
  }
  return response.json() as Promise<T>;
}

export async function fetchWorkingTemplate() {
  const response = await fetch("/api/working-template");
  return parseResponse<WorkingTemplateSnapshot>(response);
}

export async function uploadArchive(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/assets/upload", {
    method: "POST",
    body: formData
  });
  return parseResponse<{ inventory: WorkingTemplateSnapshot["inventory"] }>(response);
}

export async function saveTemplate(template: TemplateV2) {
  const response = await fetch("/api/working-template", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ template })
  });
  return parseResponse<WorkingTemplateSnapshot>(response);
}

export async function validateTemplate(template: TemplateV2) {
  const response = await fetch("/api/working-template/validate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ template })
  });
  return parseResponse<ValidationResult>(response);
}

export async function previewScene(backgroundSceneId: string) {
  const response = await fetch("/api/working-template/preview", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ background_scene_id: backgroundSceneId })
  });
  return parseResponse<{ preview_url: string }>(response);
}

export async function uploadBackground(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/working-template/backgrounds/upload", {
    method: "POST",
    body: formData
  });
  return parseResponse<{ background_scene_id: string }>(response);
}

export async function deleteBackground(sceneId: string) {
  const response = await fetch(`/api/working-template/backgrounds/${sceneId}`, {
    method: "DELETE"
  });
  return parseResponse<{ active_background_scene_id: string }>(response);
}

export async function createJob(count: number) {
  const response = await fetch("/api/jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ count })
  });
  return parseResponse<{ id: string; status: "running" }>(response);
}

export async function fetchJob(jobId: string) {
  const response = await fetch(`/api/jobs/${jobId}`);
  return parseResponse<JobDetail>(response);
}

export async function cancelJob(jobId: string) {
  const response = await fetch(`/api/jobs/${jobId}/cancel`, {
    method: "POST"
  });
  return parseResponse<{ ok: boolean }>(response);
}

export interface SplitConfig {
  train: number;
  valid: number;
  test: number;
}

export async function exportJob(jobId: string, format: "yolo" | "coco", split: SplitConfig) {
  const response = await fetch(`/api/jobs/${jobId}/export`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ format, split })
  });
  return parseResponse<{ download_url: string }>(response);
}
