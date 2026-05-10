# Independent Repo Structure

## Purpose

Define product-level packaging for the independent website repo.

This file answers:

- what top-level parts the repo should have
- what belongs to frontend
- what belongs to backend
- where runtime data should live
- where system resources should live

This file does not define detailed source trees.

## Required Top-Level Parts

Agents should assume the independent repo contains these logical parts:

1. frontend app
2. backend app
3. generation engine
4. shared contract area
5. spec

## Ownership Rules

### Frontend App

Frontend is the browser UI.

Frontend owns:

- screen flow
- editor-local state
- dialogs and toasts
- API calls

Frontend does not own:

- extracted asset files
- working template on disk
- preview image files on disk
- generated output on disk
- system resource files

### Backend App

Backend is the local runtime owner.

Backend owns:

- asset upload handling
- working workspace reset
- working template persistence
- preview generation
- generate job execution
- export generation
- runtime filesystem state

### Generation Engine

Generation engine is internal reusable logic used by backend.

Generation engine is not a user-facing app.

Engine owns domain logic such as:

- inventory scan
- template load and save
- validation
- preview render
- dataset generation

### Shared Contract

Shared contract area exists to reduce drift between frontend and backend.

Minimum expected artifacts:

- template schema `v2`
- example working-template payload
- example validation payload
- example job payload

## Runtime Data Placement

### `app_resources`

`app_resources` belongs to backend.

Reason:

- backend reads it directly
- backend copies default resources into working workspace
- frontend does not need raw access to these files

Example:

- default white background image

### Working Workspace

Working workspace belongs to backend.

Expected contents:

- `assets/`
- `backgrounds/`
- `template.json`
- `previews/`
- `jobs/`

Reason:

- backend controls lifecycle of these artifacts
- backend validates, previews, generates, exports, and resets them
- frontend only sees state through API

## Frontend State Rule

Frontend may keep local UI state in memory.

Allowed frontend state examples:

- selected scene
- selected block
- draw mode
- unsaved form values
- modal state
- current preview URL

Frontend must not be treated as source of truth for:

- asset inventory persistence
- saved template on disk
- generated dataset output

## Recommended Repo Shape

This is a logical shape, not a locked directory tree:

```text
independent repo
|- frontend app
|- backend app
|  |- app_resources
|  |- working workspace
|- generation engine
|- shared contract
|- spec
```

## Fixed Decisions

1. The independent repo has two main apps: frontend and backend.
2. Generation engine is internal to backend usage, not a third UX app.
3. `app_resources` belongs under backend ownership.
4. Working workspace belongs under backend ownership.
5. Frontend does not own runtime filesystem artifacts.
6. A shared contract area is allowed and recommended.

## Not Decided Here

This file does not decide:

- exact folder names
- exact Python package layout
- exact frontend package layout
- exact dev and prod command structure
- exact monorepo tool choice
