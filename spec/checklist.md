# Agent Implementation Checklist

## Purpose

This file gives implementation developer a default execution order for building the website MVP.

Use this file together with:

1. `spec/product/website-overview.md`
2. `spec/product/independent-repo-structure.md`
3. `spec/product/technology-recommendation.md`
4. `spec/frontend/website-ui.md`
5. `spec/backend/website-api.md`

This checklist is intentionally sequential.
Do not skip ahead unless an earlier phase is already complete.

## Global Rules

- treat all `fixed decisions` in other spec files as binding
- do not add extra screens
- do not add template `v1` compatibility
- do not add multi-user assumptions
- do not add cloud infrastructure assumptions
- do not add websocket or external queue in MVP
- keep generator logic in Python and call it directly from backend
- keep runtime filesystem ownership in backend

## Phase 0: Read And Freeze Scope

### Goal

Make sure implementation starts from the correct product boundaries.

### Must Do

- read `spec/README.md`
- read the files in the documented order
- extract all `fixed decisions`
- extract all explicit `non-goals`
- note the single unresolved backend question:
  - zip on-demand vs zip immediately after generate success

### Done When

- agent can restate:
  - there are only two main screens
  - backend owns runtime state
  - template format is `v2` only
  - output is YOLO only
  - one generate job runs at a time

### Do Not Do Yet

- do not scaffold code before understanding repo boundaries

## Phase 1: Repo Skeleton

### Goal

Create the independent repo structure without implementing business logic yet.

### Must Do

- create frontend app area
- create backend app area
- create engine area or engine package boundary
- create shared contract area
- create backend-owned runtime directories for:
  - `app_resources`
  - working workspace temp root

### Should Do

- add top-level README for repo purpose
- add ignore rules for runtime temp artifacts
- place default white background under backend-owned resources

### Done When

- repo structure reflects:
  - frontend app
  - backend app
  - engine boundary
  - shared contract boundary
  - spec directory

### Do Not Do Yet

- do not build full UI
- do not wire real generate logic yet

## Phase 2: Shared Contract

### Goal

Create a stable contract layer before UI and backend drift apart.

### Must Do

- define template schema `v2`
- add example working-template payload
- add example validation issue payload
- add example job payload

### Should Do

- keep contract artifacts readable by both frontend and backend tooling
- align field names exactly with backend spec

### Done When

- frontend and backend can both point to the same template `v2` shape

### Do Not Do Yet

- do not invent additional template fields beyond spec

## Phase 3: Backend App Shell

### Goal

Bring up a runnable backend shell with correct runtime ownership.

### Must Do

- scaffold FastAPI app
- add health endpoint
- create backend settings for:
  - resource root
  - runtime temp root
- create workspace initialization logic
- create default white background copy path logic

### Should Do

- isolate route layer from service layer
- isolate filesystem helpers from request handling

### Done When

- backend starts
- `GET /api/health` returns `{"status":"ok"}`
- backend can initialize clean runtime workspace

### Do Not Do Yet

- do not add websocket
- do not add database

## Phase 4: Frontend App Shell

### Goal

Bring up a desktop-first app shell that matches the product layout.

### Must Do

- scaffold React + TypeScript + Vite app
- set up Tailwind CSS
- set up base UI primitives
- create top-level app flow with exactly:
  - `Upload`
  - `Editor`
- create empty layout states for both screens

### Should Do

- set up server-state layer
- set up editor-local state layer
- set up form layer for future dialogs and inspector

### Done When

- app renders a basic `Upload` screen
- app can route or switch into a basic `Editor` shell
- layout supports:
  - left panel
  - center canvas area
  - right inspector area

### Do Not Do Yet

- do not implement full editor behavior
- do not style beyond the established clean app-shell direction

## Phase 5: Asset Upload Flow

### Goal

Implement the first end-to-end meaningful product flow:
upload archive, derive inventory, enter editor.

### Backend Must Do

- implement `POST /api/assets/upload`
- validate `.zip` and `.rar`
- enforce class and subtype structure rules
- ignore only allowed system artifacts
- reject all other hidden files and invalid layout
- rebuild workspace from accepted upload
- create fresh working template with default white background

### Frontend Must Do

- implement archive upload UI
- show upload errors clearly
- call upload endpoint
- on success, switch to `Editor`
- immediately load `GET /api/working-template`

### Done When

- valid upload transitions `Upload -> Editor`
- invalid upload stays on `Upload` with clear error
- editor receives inventory from backend snapshot

### Do Not Do Yet

- do not add client-side folder remapping wizard
- do not add archive import shortcuts beyond the spec

## Phase 6: Working Template Read And Save

### Goal

Make backend snapshot and frontend editor state sync correctly.

### Backend Must Do

- implement `GET /api/working-template`
- implement `PUT /api/working-template`
- validate template `v2` on save
- save only if there is no validation error
- return full snapshot on successful save

### Frontend Must Do

- load working snapshot into editor state
- preserve active scene after save
- support local dirty state before save
- display latest backend validation state

### Done When

- editor loads from backend snapshot
- save updates backend template
- failed save does not pretend success

### Do Not Do Yet

- do not support template file import
- do not support template `v1`

## Phase 7: Background Scene Management

### Goal

Support multiple backgrounds inside the working template.

### Backend Must Do

- implement background upload endpoint
- implement background delete endpoint
- auto-create background scene on upload
- prevent deletion of the last remaining scene

### Frontend Must Do

- render background list
- support select active scene
- support add background
- support delete background
- keep scene-local blocks tied to the active background scene

### Done When

- user can add background
- user can switch scenes
- user cannot delete the last scene

### Do Not Do Yet

- do not add background library browser
- do not add persistent background catalog

## Phase 8: Block Editor Core

### Goal

Implement the MVP editor behavior for blocks.

### Must Do

- support `Select` mode
- support `Draw` mode
- create `single_class_block` on drag
- assign default block values from spec
- render block overlays on canvas
- support block selection
- support drag to move
- support drag corner to resize
- sync bbox edits into inspector

### Should Do

- color blocks by class
- show class label overlays

### Done When

- user can create, select, move, and resize blocks
- inspector reflects selected block
- block list reflects current active scene blocks

### Do Not Do Yet

- do not add extra block types
- do not add full freeform design-tool behavior

## Phase 9: Validation Panel And JSON Mode

### Goal

Provide enough power and transparency for technical users.

### Must Do

- render validation panel
- distinguish errors vs warnings
- update panel from local editor state
- add JSON mode for current working template only

### Should Do

- make validation panel easy to scan by path and message
- keep JSON mode clearly marked as advanced

### Done When

- user can inspect validation issues
- user can edit raw working template JSON locally before save

### Do Not Do Yet

- do not add external JSON file import
- do not auto-migrate old schema

## Phase 10: Preview Flow

### Goal

Implement manual preview generation for the selected scene.

### Backend Must Do

- implement `POST /api/working-template/preview`
- render preview from saved template and selected scene
- write preview artifact into preview workspace
- return preview URL

### Frontend Must Do

- auto-save before preview
- call preview endpoint only on explicit user action
- show returned preview in editor
- show error toast on preview failure

### Done When

- selected scene can be previewed on demand
- preview does not auto-run on every edit

### Do Not Do Yet

- do not add live preview regeneration

## Phase 11: Generate Job Lifecycle

### Goal

Implement generation as a background job with polling.

### Backend Must Do

- implement `POST /api/jobs`
- implement `GET /api/jobs/{job_id}`
- implement `POST /api/jobs/{job_id}/cancel`
- keep one running job at a time
- persist job metadata in file JSON
- expose real `generated_count` if engine can support it

### Frontend Must Do

- implement generate dialog
- enforce generate preconditions
- auto-save before create job
- poll job status while running dialog is open
- support cancel action

### Done When

- user can start one job
- second job is blocked while first job is running
- running dialog shows progress state
- cancel path is wired

### Do Not Do Yet

- do not add websocket
- do not add parallel jobs

## Phase 12: Export And Download

### Goal

Let the user retrieve the generated dataset.

### Backend Must Do

- implement `POST /api/jobs/{job_id}/export`
- implement `GET /api/jobs/{job_id}/download`
- support only `format = "yolo"`
- reuse existing zip if already exported

### Frontend Must Do

- open success modal when job succeeds
- trigger export on download action
- trigger download from returned URL

### Done When

- successful generate leads to success modal
- user can click download and receive dataset zip

### Do Not Do Yet

- do not implement COCO export

## Phase 13: Leave Warning And UX Polish

### Goal

Respect the temporary-data nature of MVP.

### Must Do

- warn before reload or leave when possible
- return to `Upload` after reload
- keep feedback channels aligned:
  - inline for generate blockers
  - toast for short failures and short success notices
  - dialog for blocking states

### Should Do

- add clear empty states
- keep desktop-first layout stable

### Done When

- working-data risk is communicated clearly
- UX feedback channels match the spec

## Phase 14: Final MVP Verification

### Goal

Confirm that the implemented product matches the spec, not just that code runs.

### Must Verify

- exactly two main screens exist
- asset upload accepts only `.zip` and `.rar`
- invalid archive structure is rejected
- template format is `v2` only
- generate launches from `Editor` as a dialog
- only one job can run at a time
- success path uses modal
- preview failure uses toast
- generate failure uses toast
- backend owns runtime filesystem state
- frontend does not become the source of truth for workspace artifacts

### Final Done When

- one clean end-to-end flow works:
  - upload valid archive
  - enter editor
  - edit template
  - preview selected scene
  - start generate
  - wait for success
  - download YOLO zip

## Explicit Non-Goals During MVP Build

Do not implement unless the spec changes:

- COCO export
- template `v1` compatibility
- multi-user auth
- cloud object storage
- SSR
- websocket job updates
- external queue
- collaborative editing
- advanced undo and redo
- model training from the website
