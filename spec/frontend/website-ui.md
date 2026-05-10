# Frontend UI Spec

## Purpose

Define the UI behavior of the website MVP.

This file is optimized for implementation agents:

- screen boundaries are explicit
- interaction rules are explicit
- feedback channels are explicit
- do not infer extra screens or hidden flows

## Fixed UI Constraints

Agents should assume these are already fixed:

- only two main screens exist: `Upload` and `Editor`
- `Generate` is a dialog launched from `Editor`
- MVP is desktop-first
- mobile support is view-oriented, not full editor parity
- working data is temporary
- UI works with template schema `v2` only
- editor supports drag and resize on canvas
- editor supports `single_class_block` only

## Global UI Goals

The UI should let the user:

1. upload asset archive
2. inspect inferred inventory
3. edit working template
4. preview and validate template
5. start generate
6. observe progress
7. download result

## Global UI Rules

### State Visibility

UI should always make these visible somewhere in the app:

- asset inventory
- working template state
- validation state
- current preview
- job state
- output readiness

### Temporary Data Warning

UI must communicate that working data is temporary.

Frontend should:

- warn before reload or leave when platform allows
- return to `Upload` after reload
- not expose a dedicated `Reset` button in MVP

### Validation Responsibility

Frontend may validate local editor state for responsiveness, but backend remains the final authority.

Implication:

- local validation can update immediately
- save, preview, and generate still require backend validation

## Screen 1: Upload

### Purpose

Let the user provide a valid asset archive and derive inventory from it.

### Required UI Parts

- archive upload area
- structure guidance
- asset inventory table or panel

### Upload Rules

Accepted user input:

- drag and drop archive
- file picker archive

Accepted archive types:

- `.zip`
- `.rar`

Expected archive structure example:

- `class_name/subtype_name/image.png`

Behavior after successful upload:

1. backend resets working workspace
2. backend rebuilds workspace from new inventory
3. frontend moves to `Editor`
4. frontend calls `GET /api/working-template`

### Inventory Presentation

Inventory UI should show:

- class name
- subtype name
- subtype file count
- root-level file count when present

### Upload Error States

Frontend must support clear errors for:

- unsupported archive type
- invalid folder structure
- upload failure
- duplicate file rename side effects when relevant

## Screen 2: Editor

### Purpose

Let the user create and edit a working template without editing full JSON by hand.

### Layout

Desktop layout should use three main columns:

- left column: template and scene navigation
- center column: canvas
- right column: inspector

### Required Editor Areas

- template header
- background list
- block list
- preview canvas
- inspector
- validation panel
- optional JSON mode

## Template Header

### Visible Items

- working template name
- latest validation state

### Actions

- `Save`
- `Preview`
- `Go to Generate`

### Rules

- `Save` calls `PUT /api/working-template`
- frontend sends only the `template` object
- successful save returns full working snapshot
- failed save due to validation error is not considered saved
- successful save preserves active background scene selection
- `Preview` must auto-save first
- preview does not auto-run on every small change
- `Go to Generate` opens dialog on top of `Editor`

## Background List

### Purpose

Switch and manage `background_scene` entries within the current template.

### Visible Items

- scene thumbnail
- scene name or id
- active state

### Rules

- first loaded scene becomes default active scene
- each uploaded background creates a new `background_scene`
- `background_scene_id` format is `bg_001`, `bg_002`, and so on
- first default scene comes from the system white background
- last remaining scene cannot be deleted
- each scene has its own block layout
- each scene has `scene_weight`, default `1`
- uploaded backgrounds are temporary and can be lost on reload

## Block List

### Purpose

Display and manage blocks for the currently active background scene.

### Visible Items

- block id
- block class
- compact bbox summary

### Actions

- add block
- select block
- duplicate block
- delete block

### Block Creation Rules

New block creation in MVP:

- user enters `Draw` mode
- user drags a rectangle on canvas
- frontend creates a `single_class_block`

Default values:

- `id` uses `block_001`, `block_002`, and so on
- `class` defaults to the first class in inventory
- `allowed_subtypes` defaults to all subtypes of that class
- `capacity = 1`
- `skip_prob = 0`
- `augmentation.rotation_max = 0`
- `augmentation.blur_max = 0`
- `augmentation.noise_max = 0`

Restriction:

- block creation is disabled if inventory is empty

## Preview Canvas

### Visible Items

- active background image
- page frame
- block rectangles
- class-colored overlays
- class labels

### Required Interactions

- click block to select
- hover block to highlight
- drag block to move
- drag corner to resize
- sync bbox changes back into inspector
- drag in `Draw` mode to create a new block

## Inspector

### Empty State

If no block is selected:

- inspector should be disabled or blank
- UI should prompt user to select a block

### Sections

- template meta
- canvas settings
- selected background
- block settings

### Template Meta Fields

- `name`
- `description`
- `version`

### Canvas Settings Fields

- width min
- width max
- height min
- height max

UI rule:

- use compact min/max inputs
- placeholders `Min` and `Max` are sufficient

### Selected Background Fields

- background name or id
- background thumbnail
- selected state
- `scene_weight`

### Block Settings

Common block fields:

- `id`
- `bbox`
- `skip_prob`
- `position_anchor`
- `augmentation`

`position_anchor` rules:

- valid values are:
  - `top_left`
  - `top_center`
  - `top_right`
  - `center_left`
  - `center`
  - `center_right`
  - `bottom_left`
  - `bottom_center`
  - `bottom_right`
- null is allowed
- UI uses a 3x3 grid
- if anchor is selected, object placement uses exact anchor matching
- if anchor would overflow the block, object must be scaled down to fit
- if no anchor is selected, object placement is random inside the block but still must fit

`augmentation` rules:

- object contains:
  - `rotation_max`
  - `blur_max`
  - `noise_max`
- values are upper bounds
- generate-time interpretation:
  - `rotation_max` maps to `[-value, +value]`
  - `blur_max` maps to `[0, value]`
  - `noise_max` maps to `[0, value]`

### `single_class_block` Fields

- `class`
- `allowed_subtypes`
- `capacity`
- `position_anchor`
- `augmentation`

UI rules:

- `allowed_subtypes` uses checkbox list
- default is all subtypes of selected class checked
- `capacity` is integer `1..10`
- `capacity` uses slider in MVP

## Validation Panel

### Purpose

Show validation issues for the current local editor state.

### Visible Data

- errors
- warnings
- issue path
- issue message

### Rules

- panel reflects local editor state immediately
- backend still re-validates on save, preview, and generate
- if any error exists, generate must be blocked in UI
- if only warnings exist, generate remains allowed
- if backend rejects `POST /api/jobs`, frontend should show short message and return user focus to validation panel

## JSON Mode

### Purpose

Provide a power-user escape hatch.

### Rules

- JSON mode edits the current working template only
- JSON mode does not import template files from user machine
- JSON edits remain local editor state until user saves

## Generate Flow

### Generate Input Dialog

Required items:

- title
- `count` input
- hint that count must be integer `>= 1`
- `Start Generation` button
- close action

Rules:

- dialog opens on top of `Editor`
- frontend does not expose manual `seed`
- frontend does not expose config selector in MVP

### Generate Preconditions

Frontend may allow start only if:

- no validation error exists
- inventory is valid
- no job is currently running
- `count` is integer `>= 1`

### Generate Start Rules

When user presses `Start Generation`:

1. frontend auto-saves working template
2. if save fails due to validation error, keep dialog open and show inline message
3. if save succeeds, frontend calls `POST /api/jobs`

Additional rules:

- if warnings exist, show inline warning but still allow generate
- if job is already running, dialog may open but start button must be disabled
- validation and job-running messages use inline dialog messages, not toast

Suggested warning text:

- `Working template has warnings. You can still generate, but results may be suboptimal.`

Suggested running-job text:

- `A generation job is already running.`

### Scene Distribution Rule

User enters a total `count`.

Backend generates one image at a time.
For each image, backend randomly chooses a `background_scene` using `scene_weight`.

Implication:

- equal weights mean equal probability
- small total counts can produce uneven scene counts

## Running Dialog

After successful start:

- close input dialog
- open blocking running dialog
- show progress from `generated_count / count`
- show progress bar
- show `Cancel` action

## Success And Failure Feedback

### Generate Success

Rules:

- frontend polls `GET /api/jobs/{job_id}`
- when status becomes `succeeded`, close running dialog
- open success modal immediately
- user download action calls `POST /api/jobs/{job_id}/export` with `{ "format": "yolo" }`
- repeated download may reuse the previous download URL

Success modal must show:

- total image count
- download dataset button

MVP note:

- only `YOLO` is enabled
- `COCO` shown in mockups is phase-later only

### Generate Failure

Rules:

- close running dialog
- show error toast
- keep user in `Editor`

Suggested text:

- `Generation failed due to an unexpected error. Please try again.`

### Preview Failure

Rules:

- do not open dedicated failure modal
- show error toast

Suggested text:

- `Preview could not be generated for the selected scene.`

## Feedback Channel Rules

Use `toast` for:

- save success
- background upload success
- preview failure
- generate failure
- short export failure

Use `inline message` for:

- validation errors before generate
- warnings before generate
- invalid `count`
- running-job block in generate dialog

Use `dialog` or `modal` for:

- generate input
- generation running state
- generation success
- leave or reload warning

## Empty States

Frontend must support explicit empty states for:

- no asset uploaded yet
- no valid template yet
- no job yet

## Responsive Scope

Desktop is the primary target for MVP.

Mobile support only needs:

- status viewing
- no full editor parity

## Fixed Decisions

1. MVP is desktop-first.
2. Only two main screens exist: `Upload` and `Editor`.
3. Generate is not a main screen.
4. Canvas supports drag and resize in MVP.
5. JSON mode exists.
6. Invalid asset archive structure is rejected immediately.
7. Asset upload accepts `.zip` and `.rar` only.
8. Generate failure closes running dialog and shows error toast.
9. Preview failure shows error toast.
10. Validation errors and warnings before generate are shown inline in the generate dialog.
