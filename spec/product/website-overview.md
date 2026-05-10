# Product Overview

## Purpose

Define the product shape of the SyntheticDataset Website.

This file answers:

- what the product is
- what MVP must do
- what MVP must not do
- what major decisions are already fixed

This file does not define detailed API payloads or UI component internals.

## Current Starting Point

The current repo is a CLI dataset generator with this functional pipeline:

1. Read object assets from disk.
2. Read template layout JSON.
3. Validate template against asset inventory.
4. Generate dataset output.
5. Export YOLO labels, `data.yaml`, and `metadata.jsonl`.

Existing reusable capabilities:

- scan class and subtype inventory from asset folders
- load template JSON
- save template JSON
- validate template
- render static template preview
- generate dataset from template

Missing website capabilities today:

- real frontend
- upload flow from browser
- background job flow for web UX
- export management for web UX
- full drag-and-drop editor

## Product Goal

Convert the CLI tool into a local-first website that lets the user:

1. Upload an asset archive from their machine.
2. Infer class and subtype structure from the uploaded archive.
3. Create or edit a working layout template through UI.
4. Preview and validate the template before generate.
5. Start dataset generation from the browser.
6. Download generated dataset output as a zip file.
7. Manage multiple backgrounds in one template, with separate block layout per background.

## Fixed Product Constraints

 should treat these as binding:

- MVP is local-first.
- MVP is single-user.
- MVP has no auth.
- MVP has no multi-user collaboration.
- MVP does not require external object storage.
- MVP keeps data on local filesystem.
- MVP reuses existing generator logic instead of replacing the generation model.
- MVP supports template schema `v2` only.
- MVP does not keep backward compatibility for template `v1`.

## MVP Scope

MVP includes:

- asset archive upload
- asset inventory derivation
- working template creation and editing
- background management inside the template
- preview generation
- template validation
- background generate job
- running dialog
- success modal
- download generated dataset as zip
- YOLO export only

MVP excludes:

- COCO export
- auto background removal
- collaborative editing
- complex template versioning
- advanced undo and redo
- model training from the website
- cloud deployment concerns

## Main User Flow

MVP has exactly two main screens:

1. `Upload`
2. `Editor`

Expected flow:

1. User uploads a valid asset archive.
2. Backend resets the current working workspace and rebuilds it from the new inventory.
3. Frontend moves from `Upload` to `Editor`.
4. User edits the working template, backgrounds, blocks, and validation state.
5. User triggers `Generate` from inside `Editor`.
6. Frontend shows running state while polling backend job status.
7. On success, frontend shows success modal and allows download.
8. On failure, frontend shows error toast and keeps user in `Editor`.

## Architectural Shape

### Frontend

Frontend is a local-first browser UI client.

Frontend responsibilities:

- guide the user through `Upload` and `Editor`
- display inventory, preview, validation state, and job state
- manage editor-local state
- open generate dialog
- warn about temporary working data

Frontend is not the source of truth for persisted runtime artifacts.

### Backend

Backend wraps the existing generation engine.

Backend responsibilities:

- receive and validate uploaded asset archives
- manage working workspace
- manage working template
- validate template
- render preview
- execute generate jobs
- export zip output

Backend owns runtime filesystem state.

### Engine

Engine remains the reusable generation logic.

Engine responsibilities:

- inventory scanning
- template load and save
- template validation
- preview rendering
- dataset generation

## Temporary Data Rule

Working data in MVP is temporary.

 should assume:

- asset inventory can be lost
- uploaded backgrounds can be lost
- working template can be lost
- previews can be lost
- generated output can be lost if not downloaded

Frontend must warn users before reload or leave when possible.

## Source Of Truth By Topic

- product scope and major decisions: this file
- repo packaging: `spec/product/independent-repo-structure.md`
- recommended stack: `spec/product/technology-recommendation.md`
- UI structure and interactions: `spec/frontend/website-ui.md`
- API contract and storage model: `spec/backend/website-api.md`

## Fixed Decisions

1. Website MVP is local-first and single-user.
2. Only two main screens exist: `Upload` and `Editor`.
3. `Generate` is opened from `Editor` as a dialog, not a main screen.
4. Output format in MVP is YOLO only.
5. Asset upload accepts `.zip` and `.rar` only.
6. Asset upload must follow strict folder structure and is rejected immediately if invalid.
7. Template is created and edited in the UI; template import from user machine is not supported in MVP.
8. Website works with template schema `v2` only.
9. Editor MVP supports drag and resize on canvas.
10. Editor MVP supports `single_class_block` only.
11. A template can contain multiple backgrounds and each background has its own block layout.
12. A new template starts with one default white background scene.
13. Backend allows only one running generate job at a time.
14. Validation errors and warnings before generate are shown inline in the generate dialog.
15. Preview failure and generate failure use error toast.
16. Generate success uses success modal.

## Non-Goals

 should not optimize for these in the first implementation:

- SEO
- SSR
- cloud-native infrastructure
- external job queue
- multi-user correctness
- backward compatibility with template `v1`
