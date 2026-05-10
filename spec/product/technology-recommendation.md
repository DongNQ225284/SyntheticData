# Technology Recommendation

## Purpose

Define the default implementation stack for the independent website repo.

## Input Constraints

Should assume these constraints are fixed:

- local-first MVP
- single-user MVP
- two main screens only: `Upload` and `Editor`
- backend owns runtime filesystem state
- generator logic already exists in Python
- one running generate job at a time
- polling is enough for MVP
- output format is YOLO only in MVP

## Mockup Interpretation

Read the mockups as:

- desktop-like web app
- clean, bright, utility-oriented UI
- multi-panel app shell
- modal-heavy workflow
- structured editor with canvas interaction

Technology implication:

- frontend must be strong at app shell, async state, and canvas interaction
- backend must be strong at short request-response flow plus background job execution

## Frontend Recommendation

Decision:

- `React`
- `TypeScript`
- `Vite`
- `Tailwind CSS`
- `shadcn/ui`
- `TanStack Query`
- `Zustand`
- `React Hook Form`
- `Zod`
- `react-konva`

Why:

- `React + TypeScript` fit a stateful editor-like app.
- `Vite` is a better default than SSR frameworks for this local-first app.
- `Tailwind CSS` fits the clean mockup style and speeds up exact implementation.
- `shadcn/ui` provides clean primitives without imposing heavy visual identity.
- `TanStack Query` fits snapshot loading, mutation flow, and job polling.
- `Zustand` is enough for local editor state.
- `React Hook Form + Zod` fit generate dialog and inspector forms.
- `react-konva` is a safe default for drag, resize, hit-testing, and overlays.

Do not choose by default:

- `Next.js`
- `Nuxt`
- `Material UI`
- `Redux Toolkit`
- raw DOM-only canvas implementation

Why not:

- SSR is unnecessary here.
- `Material UI` pushes the visual style away from the mockups.
- Redux adds more structure than MVP needs.
- raw DOM canvas logic becomes fragile once editor interactions grow.

## Backend Recommendation

Decision:

- `FastAPI`
- `Python 3`
- `Pydantic v2`
- `Uvicorn`
- in-process background worker
- file-based runtime state

Why:

- existing generation logic is Python
- backend spec already matches API-first FastAPI shape
- `Pydantic v2` is suitable for schema-heavy request and response modeling
- `Uvicorn` is sufficient for local runtime
- in-process worker is enough because only one job runs at a time
- file-based runtime matches the filesystem-as-source-of-truth rule

Do not choose by default:

- `Django`
- `Flask`
- `Node.js` backend
- `NestJS`
- `Celery`
- `Redis`

Why not:

- `Django` is heavier than needed
- `Flask` provides less structure than this app needs
- Node backend creates an unnecessary boundary with the Python engine
- external queue infrastructure is premature for MVP

## Engine Recommendation

Decision:

- keep generation engine in Python
- import engine functions directly into backend
- do not shell out to CLI in normal backend flow

Why:

- direct function calls are easier to test
- direct function calls are easier to debug
- CLI orchestration adds avoidable process and path complexity

Do not choose by default:

- separate engine microservice
- shell-based orchestration
- JavaScript reimplementation of generation logic

## Shared Contract Recommendation

Decision:

- keep a shared contract area for schema and example payloads

Minimum expected artifacts:

- template schema `v2`
- example working-template payload
- example validation issue payload
- example job payload

## Default State Split

Frontend state split:

- server state: `TanStack Query`
- editor-local state: `Zustand`
- form state: `React Hook Form`

Interpretation:

- inventory snapshot is server state
- backend working-template snapshot is server state
- selected scene is editor-local state
- selected block is editor-local state
- dirty editor buffer is editor-local state
- generate dialog input is form state

## Default Execution Model

Backend execution model:

- short request-response for upload, save, validate, preview trigger
- background execution for generate jobs
- polling for job status
- file JSON for job metadata

Do not introduce by default:

- websocket
- external queue
- database

Only change this if product constraints change.

## Final Recommendation

Treat this as the default stack:

- frontend: `React + TypeScript + Vite + Tailwind CSS + shadcn/ui + TanStack Query + Zustand + React Hook Form + Zod + react-konva`
- backend: `FastAPI + Python 3 + Pydantic v2 + Uvicorn + in-process worker + file-based runtime`
- engine: Python engine imported directly by backend
- contract: shared schema and payload examples

## Decision Strength

Strong defaults:

- `React`
- `FastAPI`
- Python-native engine reuse
- file-based runtime
- polling instead of websocket
- in-process worker instead of external queue

Flexible defaults:

- `shadcn/ui`
- `Zustand`
- `react-konva`

If an agent proposes an alternative, it must explain:

- what problem the default choice fails to solve
- what concrete complexity the alternative removes
- what new complexity the alternative adds
