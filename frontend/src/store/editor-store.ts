import { create } from "zustand";
import { validateTemplateLocal } from "../features/editor/validation";
import type {
  AssetInventory,
  BackgroundScene,
  Block,
  TemplateV2,
  ValidationResult,
  WorkingTemplateSnapshot
} from "../types/contracts";
import { clamp } from "../lib/utils";

type EditorMode = "select" | "draw";

interface ToastState {
  id: number;
  title: string;
  tone: "success" | "error";
}

interface EditorStore {
  screen: "upload" | "editor";
  template: TemplateV2 | null;
  inventory: AssetInventory;
  validation: ValidationResult;
  activeSceneId: string | null;
  selectedBlockId: string | null;
  mode: EditorMode;
  dirty: boolean;
  previewUrl: string | null;
  jsonMode: boolean;
  toasts: ToastState[];
  initializeSnapshot: (snapshot: WorkingTemplateSnapshot) => void;
  setScreen: (screen: "upload" | "editor") => void;
  setActiveScene: (sceneId: string) => void;
  setMode: (mode: EditorMode) => void;
  selectBlock: (blockId: string | null) => void;
  updateTemplate: (updater: (template: TemplateV2) => TemplateV2) => void;
  markClean: (validation?: ValidationResult) => void;
  setPreviewUrl: (url: string | null) => void;
  setJsonMode: (value: boolean) => void;
  pushToast: (title: string, tone: "success" | "error") => void;
  dismissToast: (id: number) => void;
}

function nextBlockId(blocks: Block[]) {
  const used = new Set(blocks.map((block) => block.id));
  let index = 1;
  while (true) {
    const candidate = `block_${index.toString().padStart(3, "0")}`;
    if (!used.has(candidate)) {
      return candidate;
    }
    index += 1;
  }
}

function activeScene(template: TemplateV2 | null, activeSceneId: string | null): BackgroundScene | null {
  if (!template || !activeSceneId) {
    return null;
  }
  return template.background_scenes.find((scene) => scene.id === activeSceneId) ?? null;
}

function recomputeValidation(template: TemplateV2, inventory: AssetInventory) {
  return validateTemplateLocal(template, inventory);
}

export const useEditorStore = create<EditorStore>((set, get) => ({
  screen: "upload",
  template: null,
  inventory: { classes: [] },
  validation: { issues: [], has_error: false, has_warning: false },
  activeSceneId: null,
  selectedBlockId: null,
  mode: "select",
  dirty: false,
  previewUrl: null,
  jsonMode: false,
  toasts: [],
  initializeSnapshot: (snapshot) =>
    set((state) => ({
      template: snapshot.template,
      inventory: snapshot.inventory,
      validation: snapshot.validation,
      activeSceneId: state.activeSceneId && snapshot.template.background_scenes.some((scene) => scene.id === state.activeSceneId)
        ? state.activeSceneId
        : snapshot.template.background_scenes[0]?.id ?? null,
      selectedBlockId: null,
      screen: state.screen === "editor" ? "editor" : state.screen,
      dirty: false
    })),
  setScreen: (screen) => set({ screen }),
  setActiveScene: (sceneId) => set({ activeSceneId: sceneId, selectedBlockId: null }),
  setMode: (mode) => set({ mode }),
  selectBlock: (blockId) => set({ selectedBlockId: blockId }),
  updateTemplate: (updater) =>
    set((state) => {
      if (!state.template) {
        return {};
      }
      const template = updater(structuredClone(state.template));
      return {
        template,
        validation: recomputeValidation(template, state.inventory),
        dirty: true
      };
    }),
  markClean: (validation) =>
    set((state) => ({
      dirty: false,
      validation: validation ?? (state.template ? recomputeValidation(state.template, state.inventory) : state.validation)
    })),
  setPreviewUrl: (url) => set({ previewUrl: url }),
  setJsonMode: (value) => set({ jsonMode: value }),
  pushToast: (title, tone) =>
    set((state) => ({
      toasts: [...state.toasts, { id: Date.now() + Math.random(), title, tone }]
    })),
  dismissToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id)
    }))
}));

export function getActiveScene() {
  const { template, activeSceneId } = useEditorStore.getState();
  return activeScene(template, activeSceneId);
}

export function createBlockFromBBox(bbox: [number, number, number, number]) {
  const { template, activeSceneId, inventory } = useEditorStore.getState();
  if (!template || !activeSceneId || !inventory.classes.length) {
    return;
  }
  useEditorStore.getState().updateTemplate((draft) => {
    const scene = draft.background_scenes.find((item) => item.id === activeSceneId);
    if (!scene) {
      return draft;
    }
    const defaultClass = inventory.classes[0];
    scene.blocks.push({
      id: nextBlockId(scene.blocks),
      bbox,
      class: defaultClass.name,
      allowed_subtypes: defaultClass.subtypes.map((subtype) => subtype.name),
      capacity: 1,
      skip_prob: 0,
      position_anchor: null,
      augmentation: {
        rotation_max: 0,
        blur_max: 0,
        noise_max: 0
      }
    });
    return draft;
  });
  const scene = getActiveScene();
  if (scene) {
    useEditorStore.getState().selectBlock(scene.blocks.length ? scene.blocks[scene.blocks.length - 1].id : null);
  }
}

export function updateSelectedBlock(updater: (block: Block) => void) {
  const { template, activeSceneId, selectedBlockId } = useEditorStore.getState();
  if (!template || !activeSceneId || !selectedBlockId) {
    return;
  }
  useEditorStore.getState().updateTemplate((draft) => {
    const scene = draft.background_scenes.find((item) => item.id === activeSceneId);
    const block = scene?.blocks.find((item) => item.id === selectedBlockId);
    if (block) {
      updater(block);
    }
    return draft;
  });
}

export function updateSelectedBlockBBox(bbox: [number, number, number, number]) {
  updateSelectedBlock((block) => {
    block.bbox = [
      clamp(bbox[0], 0, 1),
      clamp(bbox[1], 0, 1),
      clamp(bbox[2], 0.02, 1),
      clamp(bbox[3], 0.02, 1)
    ];
  });
}
