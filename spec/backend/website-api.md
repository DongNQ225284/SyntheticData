# Backend API Spec

## Purpose

Define backend runtime behavior, storage model, domain shapes, and API contracts for the website MVP.

## Fixed Backend Constraints

Should assume these are already fixed:

- backend is local-first
- backend owns runtime filesystem state
- backend reuses existing Python generation logic
- one generate job at a time
- polling is enough for MVP
- job execution is asynchronous relative to the request
- template schema is `v2` only
- output format is `yolo` only in MVP

## Runtime Architecture

Backend responsibilities:

- asset upload and validation
- working workspace lifecycle
- working template lifecycle
- background management
- template validation
- preview generation
- generate job execution
- export generation
- download serving

## Storage Model

Expected storage layout:

```text
app_resources/
  default_backgrounds/
    white.jpg

tmp/
  synth_app/
    assets/
      <class_name>/
        <subtype_name>/
          *.png|jpg|jpeg
    template.json
    backgrounds/
      *.png|jpg|jpeg
    previews/
    jobs/
      <job_id>/
        meta.json
        output/
        export/
          dataset.zip
```

Storage rules:

- uploaded asset inventory lives in `tmp/synth_app/assets/`
- default white background lives in `app_resources/default_backgrounds/white.jpg`
- when a new working template is created, backend copies the default white background into `tmp/synth_app/backgrounds/`
- uploaded backgrounds, previews, job output, zip export, and template JSON live only inside `tmp/synth_app/`
- working data is temporary by product design

## Domain Models

### Asset Inventory

```json
{
  "classes": [
    {
      "name": "figure",
      "root_file_count": 2,
      "subtypes": [
        {
          "name": "compact_diagram",
          "file_count": 10
        }
      ]
    }
  ]
}
```

### Validation Issue

```json
{
  "severity": "error",
  "path": "blocks[0].bbox",
  "message": "bbox must stay inside the page"
}
```

### Job

```json
{
  "id": "job_20260508_001",
  "status": "running",
  "template_name": "new_layout",
  "count": 500,
  "seed": 123,
  "created_at": "2026-05-08T10:00:00Z",
  "updated_at": "2026-05-08T10:00:05Z",
  "output_dir": "tmp/synth_app/jobs/job_20260508_001/output",
  "zip_path": null,
  "error": null
}
```

Job statuses:

- `idle`
- `running`
- `succeeded`
- `failed`
- `cancelled`

ID rules:

- `background_scene_id`: `bg_001`, `bg_002`, ...
- `block_id`: `block_001`, `block_002`, ...
- `job_id`: `job_YYYYMMDD_001`, `job_YYYYMMDD_002`, ...

### Background Object

```json
{
  "id": "bg_001",
  "name": "white",
  "image_path": "backgrounds/white.jpg"
}
```

### Background Scene Object

```json
{
  "id": "bg_001",
  "scene_weight": 1,
  "canvas_size_range": {
    "width": [3200, 3500],
    "height": [2000, 2400]
  },
  "background": {
    "id": "bg_001",
    "name": "white",
    "image_path": "backgrounds/white.jpg"
  },
  "blocks": []
}
```

Background scene fields:

- `id`
- `scene_weight`
- `canvas_size_range`
- `background`
- `blocks`

Do not add by default:

- `name`
- `order`
- `enabled`

### Block Object

```json
{
  "id": "block_001",
  "bbox": [0.1, 0.1, 0.3, 0.2],
  "class": "figure",
  "allowed_subtypes": ["compact_diagram", "wide_diagram"],
  "capacity": 1,
  "skip_prob": 0,
  "position_anchor": "center",
  "augmentation": {
    "rotation_max": 5,
    "blur_max": 0.4,
    "noise_max": 0.02
  }
}
```

Block fields:

- `id`
- `bbox`
- `class`
- `allowed_subtypes`
- `capacity`
- `skip_prob`
- `position_anchor`
- `augmentation`

`position_anchor` valid values:

- `top_left`
- `top_center`
- `top_right`
- `center_left`
- `center`
- `center_right`
- `bottom_left`
- `bottom_center`
- `bottom_right`
- `null`

`augmentation` fields:

- `rotation_max`
- `blur_max`
- `noise_max`

Generate-time interpretation:

- `rotation_max` maps to `[-value, +value]`
- `blur_max` maps to `[0, value]`
- `noise_max` maps to `[0, value]`

## Complete Template `v2` Example

```json
{
  "version": 2,
  "name": "new_layout_v2",
  "description": "Template with multiple background scenes.",
  "background_scenes": [
    {
      "id": "bg_001",
      "scene_weight": 1,
      "canvas_size_range": {
        "width": [3200, 3500],
        "height": [2000, 2400]
      },
      "background": {
        "id": "bg_001",
        "name": "white",
        "image_path": "backgrounds/white.jpg"
      },
      "blocks": [
        {
          "id": "block_001",
          "bbox": [0.08, 0.12, 0.24, 0.28],
          "class": "figure",
          "allowed_subtypes": ["compact_diagram", "wide_diagram"],
          "capacity": 1,
          "skip_prob": 0,
          "position_anchor": "center",
          "augmentation": {
            "rotation_max": 0,
            "blur_max": 0,
            "noise_max": 0
          }
        }
      ]
    }
  ]
}
```

Interpretation rules:

- `background_scenes` is the top-level scene list
- each scene has its own background and block list
- `scene_weight` controls scene sampling probability during generation
- block has no `type` field in MVP

## Template Validation Rules

Validator accepts template `v2` only.

Template `v1` must be treated as invalid input.

### Template-Level Rules

- `background_scenes` must be a non-empty list

### Background Scene Rules

- required fields:
  - `id`
  - `scene_weight`
  - `canvas_size_range`
  - `background`
  - `blocks`
- `scene_weight > 0`
- `blocks` must be a list
- `blocks` may be empty while editing

### Canvas Size Rules

- `canvas_size_range.width` must be two integers
- `canvas_size_range.height` must be two integers
- for each range:
  - `min <= max`
  - all values `>= 1`

### Background Rules

- `background.id` must be a non-empty string
- `background.name` must be a non-empty string
- `background.image_path` must be a non-empty string
- `background.image_path` must point to an existing file on disk

### Block Rules

- required fields:
  - `id`
  - `bbox`
  - `class`
  - `allowed_subtypes`
  - `capacity`
  - `skip_prob`
  - `position_anchor`
  - `augmentation`
- `bbox` must be `[x, y, w, h]`
- `x` and `y` must be in `[0, 1]`
- `w` and `h` must be `> 0`
- `x + w <= 1`
- `y + h <= 1`
- `allowed_subtypes` must be a list of strings
- every allowed subtype must belong to the block class
- `allowed_subtypes` may be empty
- `capacity` must be integer in `1..10`
- `skip_prob` must satisfy `0 <= value < 1`
- `position_anchor` must be `null` or one valid anchor string
- `augmentation` must be an object
- `rotation_max >= 0`
- `blur_max >= 0`
- `noise_max >= 0`

### Severity Rules

Validation issues use:

- `error`
- `warning`

Errors must block the relevant operation.
Warnings may allow the operation to continue.

Must-be-error examples:

- invalid JSON
- wrong top-level schema
- missing or invalid `background_scenes`
- missing required scene field
- invalid `scene_weight`
- invalid `canvas_size_range`
- invalid background fields
- missing background file on disk
- invalid `blocks`
- missing required block field
- invalid `bbox`
- block class not found in inventory
- subtype not belonging to the block class
- invalid `capacity`
- invalid `skip_prob`
- invalid `position_anchor`
- invalid `augmentation`
- negative or non-numeric augmentation values

May-be-warning examples:

- scene has zero blocks
- whole template has zero blocks
- `allowed_subtypes` is empty
- `skip_prob` is very high
- bbox is very small
- scene weights are very imbalanced
- augmentation is numerically valid but unusually large
- duplicated background names with different ids

### Flow Stop Rules

- save template: stop on `error`, continue on `warning`
- preview template: stop on `error`, continue on `warning`
- generate job: stop on `error`, continue on `warning`

## API

### `GET /api/health`

Purpose:

- health check

Response:

```json
{
  "status": "ok"
}
```

### `POST /api/assets/upload`

Purpose:

- upload asset archive
- validate structure
- derive inventory

Input:

- multipart form
- field: `file`

Accepted archive types:

- `.zip`
- `.rar`

Accepted asset image types:

- `.png`
- `.jpg`
- `.jpeg`

Asset structure rules:

- top-level real asset tree contains class directories only
- class directory may contain:
  - root-level images
  - subtype directories
- subtype directory contains images only
- deeper levels than `class/subtype/image` are invalid
- images at archive root are invalid

Wrapper directory rule:

- one outer wrapper directory is allowed
- if the archive contains exactly one top-level wrapper folder, backend may strip it

Ignored system artifacts:

- `__MACOSX/`
- `.DS_Store`
- `Thumbs.db`

Other hidden files and hidden directories should be treated as validation errors.

Naming rules for `class_name` and `subtype_name`:

- lowercase `a-z`
- digits `0-9`
- underscore `_`
- hyphen `-`
- no spaces
- no Vietnamese diacritics
- must not start with `.`

Must-reject examples:

- image file at archive root
- unsupported file type inside asset tree
- deeper nested directories than allowed
- empty asset tree
- no valid class directories

Suggested error messages:

- `Unsupported archive format. Only .zip and .rar are accepted.`
- `Archive root must contain class directories only.`
- `Invalid class name: 'Wide Strip'. Use lowercase letters, numbers, '-' or '_'.`
- `Invalid subtype directory depth under class 'figure'.`
- `Unsupported asset file: figure/notes.txt`
- `No valid asset images found in archive.`

Success response:

```json
{
  "inventory": {
    "classes": [
      {
        "name": "figure",
        "root_file_count": 0,
        "subtypes": [
          {
            "name": "compact_diagram",
            "file_count": 12
          }
        ]
      }
    ]
  }
}
```

Side effects:

- reset entire current working workspace
- if a job is running, attempt to cancel it first
- rebuild clean workspace from new inventory
- recreate fresh working template with default white background scene

Notes:

- response returns inventory summary only
- there is no separate `GET /api/assets/inventory` in MVP

### `POST /api/working-template/reset`

Purpose:

- hard reset current working workspace

Response:

```json
{
  "ok": true
}
```

Rules:

- remove working artifacts under `tmp/synth_app/`
- includes:
  - `assets/`
  - `backgrounds/`
  - `previews/`
  - `jobs/`
  - `template.json`
- if a job is running, reset still wins
- backend may try to mark the job cancelled, but reset must not depend on cancel success
- recreate clean workspace and recopy default white background
- after successful reset, frontend returns to `Upload`

### `GET /api/working-template`

Purpose:

- return full working snapshot for editor rendering

Response:

```json
{
  "template": {},
  "validation": {
    "issues": [],
    "has_error": false,
    "has_warning": false
  },
  "inventory": {
    "classes": []
  },
  "job": {
    "status": "idle",
    "active_job_id": null
  }
}
```

Notes:

- frontend treats the first `background_scene` as default active scene
- backend does not return `active_background_scene_id` separately in MVP

### `PUT /api/working-template`

Purpose:

- save current working template

Request:

```json
{
  "template": {}
}
```

Rules:

- validate template `v2` before write
- reject save if any validation `error` exists
- allow save if only warnings exist
- return full working snapshot on success
- frontend preserves current active scene after successful save

### `POST /api/working-template/backgrounds/upload`

Purpose:

- upload one background image and attach it as a new scene

Input:

- multipart form
- field: `file`

Accepted file types:

- `.png`
- `.jpg`
- `.jpeg`

Response:

```json
{
  "background_scene_id": "bg_002"
}
```

Rules:

- exactly one image per request
- save file into `tmp/synth_app/backgrounds/`
- if filename collides, auto-rename with numeric suffix
- create new background object and new background scene
- return only new `background_scene_id`

### `DELETE /api/working-template/backgrounds/{background_scene_id}`

Purpose:

- delete one background scene

Response:

```json
{
  "active_background_scene_id": "bg_001"
}
```

Rules:

- last remaining scene cannot be deleted
- new active scene becomes the first remaining scene

### `POST /api/working-template/validate`

Purpose:

- validate template payload

Request:

```json
{
  "template": {}
}
```

Response:

```json
{
  "issues": []
}
```

Rule:

- endpoint accepts template `v2` only

### `POST /api/working-template/preview`

Purpose:

- render preview for one background scene

Request:

```json
{
  "background_scene_id": "bg_001"
}
```

Response:

```json
{
  "preview_url": "/api/working-template/preview/current.png"
}
```

Rules:

- frontend must save before preview
- preview is manual, not automatic on every edit
- backend reads saved `tmp/synth_app/template.json`
- backend does not accept raw template in preview request
- render preview into `tmp/synth_app/previews/`
- preview includes scene background plus block overlays
- overlay must at least show bbox and class label
- if scene id does not exist, return clear short error

Suggested preview failure message:

- `Preview could not be generated for the selected scene.`

### `POST /api/jobs`

Purpose:

- start a generate job

Request:

```json
{
  "count": 500
}
```

Rules:

- backend chooses default internal generation config
- backend generates `seed` automatically
- frontend should save before calling this endpoint
- backend validates saved working template again before start
- if validation `error` exists, reject job creation
- `count` must be integer `>= 1`
- only one job may be running at a time
- backend should return short user-facing error messages

Success response:

```json
{
  "id": "job_20260508_001",
  "status": "running"
}
```

Validation failure response example:

```json
{
  "error": "Working template is not ready to generate. Please fix validation errors in the Editor."
}
```

Running-job rejection example:

- `A generate job is already running. Please wait until it finishes or reset the workspace.`

### `GET /api/jobs/{job_id}`

Purpose:

- return job detail for polling

Response:

```json
{
  "id": "job_20260508_001",
  "status": "running",
  "count": 500,
  "generated_count": 120,
  "created_at": "2026-05-08T10:00:00Z",
  "updated_at": "2026-05-08T10:00:05Z",
  "zip_ready": false,
  "download_url": null,
  "error": null
}
```

Progress rules:

- `generated_count` must reflect real completed images
- do not use estimated progress
- if job fails or is cancelled, keep last generated count instead of resetting to zero

### `POST /api/jobs/{job_id}/cancel`

Purpose:

- cancel active job

Rules:

- if running, move job toward `cancelled`
- hard reset of workspace still wins over cancel completion

### `POST /api/jobs/{job_id}/export`

Purpose:

- create or reuse downloadable zip export

Request:

```json
{
  "format": "yolo"
}
```

Response:

```json
{
  "download_url": "/api/jobs/job_20260508_001/download"
}
```

Rules:

- request must include `format`
- MVP accepts only `format = "yolo"`
- only return `download_url`
- if zip already exists for same job and format, reuse it
- zip lives under the job workspace until working workspace is reset

### `GET /api/jobs/{job_id}/download`

Purpose:

- download dataset zip

Rules:

- only allow download if job is `succeeded`
- only allow download if export zip exists

## Job Lifecycle

### Status Set

- `idle`
- `running`
- `succeeded`
- `failed`
- `cancelled`

### Flow

1. frontend calls `POST /api/jobs`
2. backend creates `job_id`
3. backend writes `meta.json`
4. backend starts background generation
5. backend updates status to `succeeded` or `failed`
6. cancel or reset may move status to `cancelled`
7. frontend polls `GET /api/jobs/{job_id}`
8. frontend calls export on success
9. frontend downloads zip

## Engine Reuse Guidance

Preferred backend reuse targets:

- inventory scanning logic
- template load and save logic
- template validation logic
- preview render logic
- `AppConfig.from_file` plus `generate_dataset`

Preferred integration style:

- direct Python call
- not shelling out to CLI

## Fixed Decisions

1. Backend implementation target is FastAPI.
2. Job runner is in-process.
3. Job state is stored in file JSON.
4. Polling is enough for MVP.
5. Output format is YOLO zip only.
6. Invalid asset archive structure is rejected immediately.
7. Asset upload accepts `.zip` and `.rar` only.
8. Only one generate job may run at a time.
9. Template import from user machine is not supported.

## Risks

### Real Progress

If current engine does not expose per-image callback, real progress may require engine changes.

### Concurrency

Multiple simultaneous jobs are intentionally out of scope because they add:

- RAM pressure
- disk pressure
- output-path complexity

### Duplicate Upload Names

For uploaded backgrounds:

- do not overwrite existing file
- do not reject only because filename already exists
- auto-rename with numeric suffix

## Open Question

Still unresolved:

- should zip export happen only when the user clicks download, or automatically right after successful generation
