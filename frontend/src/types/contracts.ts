export type AnchorValue =
  | "top_left"
  | "top_center"
  | "top_right"
  | "center_left"
  | "center"
  | "center_right"
  | "bottom_left"
  | "bottom_center"
  | "bottom_right"
  | null;

export type JobStatus = "idle" | "running" | "succeeded" | "failed" | "cancelled";

export interface AssetSubtype {
  name: string;
  file_count: number;
}

export interface AssetClass {
  name: string;
  root_file_count: number;
  subtypes: AssetSubtype[];
}

export interface AssetInventory {
  classes: AssetClass[];
}

export interface ValidationIssue {
  severity: "error" | "warning";
  path: string;
  message: string;
}

export interface ValidationResult {
  issues: ValidationIssue[];
  has_error: boolean;
  has_warning: boolean;
}

export interface Background {
  id: string;
  name: string;
  image_path: string;
}

export interface CanvasSizeRange {
  width: [number, number];
  height: [number, number];
}

export interface Augmentation {
  rotation_max: number;
  blur_max: number;
  noise_max: number;
}

export interface Block {
  id: string;
  bbox: [number, number, number, number];
  class: string;
  allowed_subtypes: string[];
  capacity: number;
  skip_prob: number;
  position_anchor: AnchorValue;
  augmentation: Augmentation;
}

export interface BackgroundScene {
  id: string;
  scene_weight: number;
  canvas_size_range: CanvasSizeRange;
  background: Background;
  blocks: Block[];
  allow_overlap: boolean;
}

export interface TemplateV2 {
  version: 2;
  name: string;
  description: string;
  background_scenes: BackgroundScene[];
}

export interface JobState {
  status: JobStatus;
  active_job_id: string | null;
}

export interface WorkingTemplateSnapshot {
  template: TemplateV2;
  validation: ValidationResult;
  inventory: AssetInventory;
  job: JobState;
}

export interface JobDetail {
  id: string;
  status: JobStatus;
  count: number;
  generated_count: number;
  created_at: string;
  updated_at: string;
  zip_ready: boolean;
  download_url: string | null;
  error: string | null;
}
