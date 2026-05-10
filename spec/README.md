# SyntheticDataset Website Spec

## Purpose

This directory is the source of truth for the website-first version of SyntheticDataset.

This spec is optimized for implementation agents:

- read files in a fixed order
- treat `fixed decisions` as binding
- treat `open questions` as unresolved
- do not infer extra features beyond what is written

## Reading Order

Read these files in order:

1. [Product Overview](./product/website-overview.md)
2. [Independent Repo Structure](./product/independent-repo-structure.md)
3. [Technology Recommendation](./product/technology-recommendation.md)
4. [Frontend UI Spec](./frontend/website-ui.md)
5. [Backend API Spec](./backend/website-api.md)
6. [Implementation Checklist](./checklist.md)

## Document Roles

- `product/website-overview.md`
  Product scope, MVP boundaries, user flow, non-goals, and major fixed decisions.

- `product/independent-repo-structure.md`
  Repo packaging boundaries: frontend, backend, engine, contracts, runtime ownership.

- `product/technology-recommendation.md`
  Recommended implementation stack and default technical choices.

- `frontend/website-ui.md`
  UI structure, states, interactions, and feedback rules.

- `backend/website-api.md`
  Runtime model, storage model, payloads, endpoint contracts, and lifecycle rules.

- `agent-checklist.md`
  Recommended implementation order, phase checkpoints, and explicit MVP do-not-do-yet boundaries.

## Mockups

Mockups are design references, not feature guarantees.

Available mockups:

- `spec/mockups/visily-upload.png`
- `spec/mockups/visily-editor.png`
- `spec/mockups/visily-new-generation.png`
- `spec/mockups/visily-generation.png`
- `spec/mockups/visily-done.png`

## Global Interpretation Rules

- MVP is local-first.
- MVP is single-user.
- Only two main screens exist: `Upload` and `Editor`.
- Backend owns filesystem runtime state.
- Frontend is a browser UI client.
- Template format for the website is `v2` only.
- Asset upload is archive-based and strictly validated.
- Generator logic should be reused from existing Python code.
- Do not add cloud-first assumptions unless a later spec explicitly changes them.
