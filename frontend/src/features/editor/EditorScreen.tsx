import { useEffect, useMemo, useRef, useState, Fragment } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Download, Eye, Plus, Save, Trash2, WandSparkles, Maximize, Layers, Settings2, RefreshCcw, Droplets, Scan, Check, MousePointer2, SquareDashed, Info, FileText } from "lucide-react";
import { Layer, Rect, Stage, Text as KonvaText, Transformer, Image as KonvaImage } from "react-konva";
import type Konva from "konva";
import {
  cancelJob,
  createJob,
  deleteBackground,
  exportJob,
  fetchJob,
  fetchWorkingTemplate,
  previewScene,
  saveTemplate,
  uploadBackground
} from "../../api/client";
import type { SplitConfig } from "../../api/client";
import { useBackgroundImage } from "../../hooks/use-background-image";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Dialog } from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { useEditorStore, createBlockFromBBox, getActiveScene, updateSelectedBlock } from "../../store/editor-store";
import { cn, clamp } from "../../lib/utils";
import type { AnchorValue, BackgroundScene, Block, TemplateV2, WorkingTemplateSnapshot } from "../../types/contracts";

const generateSchema = z.object({
  count: z.coerce.number().int().min(1)
});

const anchorOptions: AnchorValue[] = [
  "top_left",
  "top_center",
  "top_right",
  "center_left",
  "center",
  "center_right",
  "bottom_left",
  "bottom_center",
  "bottom_right"
];

const CLASS_COLOR_PALETTE: Record<string, string> = {
  figure:      "#1d8fff",
  table:       "#00a86b",
  note:        "#ff8a00",
  text:        "#a855f7",
  dimension:   "#ec4899",
  symbol:      "#14b8a6",
  stamp:       "#f59e0b",
  titleblock:  "#6366f1",
  border:      "#64748b",
};

/** Return a stable color for any class name — palette first, then HSL hash. */
function getClassColor(className: string): string {
  if (CLASS_COLOR_PALETTE[className]) return CLASS_COLOR_PALETTE[className];
  // Deterministic hue from class name characters
  let hash = 0;
  for (let i = 0; i < className.length; i++) {
    hash = (hash * 31 + className.charCodeAt(i)) >>> 0;
  }
  const hue = hash % 360;
  return `hsl(${hue}, 70%, 48%)`;
}

function runtimeAssetUrl(path: string) {
  return `/api/runtime/${path}`;
}

function nextSceneBlockId(blocks: Block[]) {
  const used = new Set(blocks.map((block) => block.id));
  let index = 1;
  while (true) {
    const candidate = `block_${String(index).padStart(3, "0")}`;
    if (!used.has(candidate)) {
      return candidate;
    }
    index += 1;
  }
}

export function EditorScreen({
  snapshot,
  onRefresh
}: {
  snapshot: WorkingTemplateSnapshot;
  onRefresh: () => Promise<void>;
}) {
  const initializeSnapshot = useEditorStore((state) => state.initializeSnapshot);
  const template = useEditorStore((state) => state.template);
  const inventory = useEditorStore((state) => state.inventory);
  const validation = useEditorStore((state) => state.validation);
  const activeSceneId = useEditorStore((state) => state.activeSceneId);
  const selectedBlockId = useEditorStore((state) => state.selectedBlockId);
  const mode = useEditorStore((state) => state.mode);
  const previewUrl = useEditorStore((state) => state.previewUrl);
  const jsonMode = useEditorStore((state) => state.jsonMode);
  const dirty = useEditorStore((state) => state.dirty);
  const setActiveScene = useEditorStore((state) => state.setActiveScene);
  const setMode = useEditorStore((state) => state.setMode);
  const selectBlock = useEditorStore((state) => state.selectBlock);
  const updateTemplate = useEditorStore((state) => state.updateTemplate);
  const markClean = useEditorStore((state) => state.markClean);
  const setPreviewUrl = useEditorStore((state) => state.setPreviewUrl);
  const setJsonMode = useEditorStore((state) => state.setJsonMode);
  const pushToast = useEditorStore((state) => state.pushToast);

  const [generateOpen, setGenerateOpen] = useState(false);
  const [runningOpen, setRunningOpen] = useState(false);
  const [successOpen, setSuccessOpen] = useState(false);
  const [dialogMessage, setDialogMessage] = useState<string | null>(null);
  const [jsonText, setJsonText] = useState("");
  const [draftRect, setDraftRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [jobId, setJobId] = useState<string | null>(snapshot.job.active_job_id);
  const [lastCount, setLastCount] = useState<number>(0);
  const [exportFormat, setExportFormat] = useState<"yolo" | "coco">("yolo");
  // Split state: two slider thumbs as percentages (0-100)
  // trainEnd = boundary between train and valid, validEnd = boundary between valid and test
  const [trainEnd, setTrainEnd] = useState(70);
  const [validEnd, setValidEnd] = useState(90); // validEnd - trainEnd = valid %, 100 - validEnd = test %
  const backgroundInputRef = useRef<HTMLInputElement | null>(null);
  const transformerRef = useRef<Konva.Transformer | null>(null);
  const selectedRectRef = useRef<Konva.Rect | null>(null);

  useEffect(() => {
    initializeSnapshot(snapshot);
  }, [initializeSnapshot, snapshot]);

  useEffect(() => {
    if (template) {
      setJsonText(JSON.stringify(template, null, 2));
    }
  }, [template, jsonMode]);

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (useEditorStore.getState().screen === "editor") {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  const activeScene = useMemo<BackgroundScene | null>(() => {
    if (!template || !activeSceneId) {
      return null;
    }
    return template.background_scenes.find((scene) => scene.id === activeSceneId) ?? null;
  }, [activeSceneId, template]);

  const selectedBlock = useMemo<Block | null>(() => {
    return activeScene?.blocks.find((block) => block.id === selectedBlockId) ?? null;
  }, [activeScene, selectedBlockId]);

  const backgroundImage = useBackgroundImage(activeScene ? runtimeAssetUrl(activeScene.background.image_path) : null);
  const previewImage = useBackgroundImage(previewUrl);
  const sceneWidth = activeScene ? activeScene.canvas_size_range.width[1] : 1600;
  const sceneHeight = activeScene ? activeScene.canvas_size_range.height[1] : 1000;
  const canvasWidth = 860;
  const canvasHeight = Math.max(420, Math.round((sceneHeight / sceneWidth) * canvasWidth));

  useEffect(() => {
    if (selectedBlockId && selectedRectRef.current && transformerRef.current) {
      transformerRef.current.nodes([selectedRectRef.current]);
      transformerRef.current.getLayer()?.batchDraw();
    } else if (transformerRef.current) {
      transformerRef.current.nodes([]);
      transformerRef.current.getLayer()?.batchDraw();
    }
  }, [selectedBlockId, activeScene]);

  // Keyboard shortcut for deleting blocks
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        document.activeElement instanceof HTMLInputElement ||
        document.activeElement instanceof HTMLTextAreaElement ||
        (document.activeElement as HTMLElement)?.isContentEditable
      ) {
        return;
      }
      if ((event.key === "Delete" || event.key === "Backspace") && selectedBlockId) {
        event.preventDefault();
        const blockIdToDelete = selectedBlockId;
        selectBlock(null);
        useEditorStore.getState().updateTemplate((draft) => {
          const scene = draft.background_scenes.find((item) => item.id === activeSceneId);
          if (scene) {
            scene.blocks = scene.blocks.filter((item) => item.id !== blockIdToDelete);
          }
          return draft;
        });
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedBlockId, activeSceneId, selectBlock]);

  const saveMutation = useMutation({
    mutationFn: async (nextTemplate: TemplateV2) => saveTemplate(nextTemplate),
    onSuccess: (data) => {
      initializeSnapshot(data);
      markClean(data.validation);
      pushToast("Working template saved.", "success");
    },
    onError: (error) => {
      pushToast(extractErrorMessage(error), "error");
    }
  });

  const previewMutation = useMutation({
    mutationFn: async (backgroundSceneId: string) => previewScene(backgroundSceneId),
    onSuccess: (data) => {
      const url = `${data.preview_url}?ts=${Date.now()}`;
      setPreviewUrl(url);
      window.open(url, "_blank");
    },
    onError: (error) => {
      pushToast(extractErrorMessage(error) || "Preview could not be generated for the selected scene.", "error");
    }
  });

  const uploadBackgroundMutation = useMutation({
    mutationFn: async (file: File) => {
      if (dirty && template) {
        await saveTemplate(template);
      }
      return uploadBackground(file);
    },
    onSuccess: async (data) => {
      const snap = await fetchWorkingTemplate();
      const newScene = snap.template.background_scenes.find((s) => s.id === data.background_scene_id);
      if (newScene) {
        updateTemplate((draft) => {
          draft.background_scenes.push(newScene);
          return draft;
        });
        setActiveScene(newScene.id);
        useEditorStore.getState().markClean();
      }
      pushToast("Background added.", "success");
    },
    onError: (error) => pushToast(extractErrorMessage(error), "error")
  });

  const deleteBackgroundMutation = useMutation({
    mutationFn: async (sceneId: string) => {
      if (dirty && template) {
        await saveTemplate(template);
      }
      return deleteBackground(sceneId);
    },
    onSuccess: async (data, sceneId) => {
      updateTemplate((draft) => {
        draft.background_scenes = draft.background_scenes.filter((s) => s.id !== sceneId);
        return draft;
      });
      setActiveScene(data.active_background_scene_id);
      useEditorStore.getState().markClean();
      pushToast("Background removed.", "success");
    },
    onError: (error) => pushToast(extractErrorMessage(error), "error")
  });

  const createJobMutation = useMutation({
    mutationFn: createJob,
    onSuccess: (data) => {
      setGenerateOpen(false);
      setRunningOpen(true);
      setJobId(data.id);
      setDialogMessage(null);
    },
    onError: (error) => {
      setDialogMessage(extractErrorMessage(error));
    }
  });

  const cancelJobMutation = useMutation({
    mutationFn: cancelJob,
    onSuccess: () => {
      setRunningOpen(false);
      setJobId(null);
      pushToast("Generation cancelled.", "success");
    }
  });

  const exportMutation = useMutation({
    mutationFn: ({ jobId, format, split }: { jobId: string; format: "yolo" | "coco"; split: SplitConfig }) =>
      exportJob(jobId, format, split),
    onSuccess: (data) => {
      window.open(data.download_url, "_blank");
    },
    onError: (error) => pushToast(extractErrorMessage(error), "error")
  });

  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => fetchJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" ? 1000 : false;
    }
  });

  useEffect(() => {
    const job = jobQuery.data;
    if (!job) {
      return;
    }
    setLastCount(job.count);
    if (job.status === "succeeded") {
      setRunningOpen(false);
      setSuccessOpen(true);
    } else if (job.status === "failed") {
      setRunningOpen(false);
      pushToast(job.error || "Generation failed due to an unexpected error. Please try again.", "error");
    } else if (job.status === "cancelled") {
      setRunningOpen(false);
    }
  }, [jobQuery.data, pushToast]);

  const form = useForm<{ count: number }>({
    resolver: zodResolver(generateSchema),
    defaultValues: {
      count: 500
    }
  });

  const handleSaveIfNeeded = async (): Promise<boolean> => {
    if (dirty && template) {
      if (validation.has_error) {
        pushToast("Please fix validation errors before proceeding.", "error");
        return false;
      }
      try {
        await saveMutation.mutateAsync(template);
      } catch (e) {
        return false;
      }
    }
    return true;
  };

  const handlePreview = async () => {
    if (!template || !activeScene) {
      return;
    }
    if (validation.has_error) {
      pushToast("Please fix validation errors before previewing.", "error");
      return;
    }
    try {
      await saveMutation.mutateAsync(template);
    } catch (e) {
      return;
    }
    await previewMutation.mutateAsync(activeScene.id);
  };

  const handleOpenGenerate = async () => {
    const success = await handleSaveIfNeeded();
    if (!success) return;
    setGenerateOpen(true);
  };

  const handleSceneSwitch = async (sceneId: string) => {
    if (sceneId === activeSceneId) return;
    const success = await handleSaveIfNeeded();
    if (!success) return;
    setActiveScene(sceneId);
  };

  const handleGenerate = form.handleSubmit(async ({ count }) => {
    if (!template) {
      return;
    }
    if (validation.has_error) {
      setDialogMessage("Working template has validation errors. Please fix them before generating.");
      return;
    }
    if (snapshot.job.status === "running" || jobQuery.data?.status === "running") {
      setDialogMessage("A generation job is already running.");
      return;
    }
    const saved = await saveTemplate(template);
    initializeSnapshot(saved);
    markClean(saved.validation);
    setLastCount(count);
    await createJobMutation.mutateAsync(count);
  });

  const applyJson = () => {
    try {
      const parsed = JSON.parse(jsonText) as TemplateV2;
      updateTemplate(() => parsed);
    } catch {
      pushToast("JSON mode contains invalid JSON.", "error");
    }
  };

  const handleSceneField = (field: keyof BackgroundScene["canvas_size_range"], index: 0 | 1, value: string) => {
    updateTemplate((draft) => {
      const scene = draft.background_scenes.find((item) => item.id === activeSceneId);
      if (!scene) {
        return draft;
      }
      const nextValue = Math.max(1, Number.parseInt(value || "1", 10));
      scene.canvas_size_range[field][index] = nextValue;
      return draft;
    });
  };

  const handlePointerDown = (event: Konva.KonvaEventObject<MouseEvent>) => {
    if (mode !== "draw" || !activeScene) {
      return;
    }
    const stage = event.target.getStage();
    const point = stage?.getPointerPosition();
    if (!point) {
      return;
    }
    setDraftRect({ x: point.x, y: point.y, width: 0, height: 0 });
  };

  const handlePointerMove = (event: Konva.KonvaEventObject<MouseEvent>) => {
    if (mode !== "draw" || !draftRect) {
      return;
    }
    const stage = event.target.getStage();
    const point = stage?.getPointerPosition();
    if (!point) {
      return;
    }
    setDraftRect({
      x: draftRect.x,
      y: draftRect.y,
      width: point.x - draftRect.x,
      height: point.y - draftRect.y
    });
  };

  const handlePointerUp = () => {
    if (!draftRect || !activeScene) {
      return;
    }
    const left = Math.min(draftRect.x, draftRect.x + draftRect.width);
    const top = Math.min(draftRect.y, draftRect.y + draftRect.height);
    const width = Math.abs(draftRect.width);
    const height = Math.abs(draftRect.height);
    if (width > 14 && height > 14) {
      createBlockFromBBox([
        clamp(left / canvasWidth, 0, 1),
        clamp(top / canvasHeight, 0, 1),
        clamp(width / canvasWidth, 0.02, 1),
        clamp(height / canvasHeight, 0.02, 1)
      ]);
      const current = getActiveScene();
      selectBlock(current && current.blocks.length ? current.blocks[current.blocks.length - 1].id : null);
    }
    setDraftRect(null);
    setMode("select");
  };

  if (!template || !activeScene) {
    return null;
  }

  return (
    <div className="flex h-screen flex-col bg-white font-sans text-ink">
      {/* Global Header */}
      <header className="flex h-16 flex-shrink-0 items-center px-6 border-b border-line">
        <div className="flex items-center gap-2 flex-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
          </div>
          <span className="text-lg font-bold text-brand">Synthetic Data</span>
        </div>
        
        <div className="flex items-center justify-center gap-4 text-sm font-medium text-muted">
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-brand text-white text-[10px]">
              <Check strokeWidth={3} size={12} />
            </div>
            <span>Upload</span>
          </div>
          <span>&gt;</span>
          <div className="flex items-center gap-2 text-brand bg-brand/5 px-3 py-1.5 rounded-full">
            <div className="flex h-5 w-5 items-center justify-center rounded-full border border-brand text-[10px]">2</div>
            <span>Editor</span>
          </div>
        </div>
        <div className="flex-1"></div>
      </header>

      {/* Main Workspace */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Column: Scene Settings */}
        <aside className="scroll-thin w-[320px] flex-shrink-0 border-r border-line bg-white flex flex-col overflow-y-auto">
          <div className="px-6 py-5 text-xs font-bold tracking-widest text-muted uppercase">Scene Settings</div>
          
          <div className="px-6 pb-6 border-b border-line">
            <div className="flex items-center gap-2 font-bold text-ink mb-5">
              <Maximize size={18} className="text-brand"/> Canvas Geometry
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-muted">Width Min</label>
                <Input className="h-10 text-sm" value={activeScene.canvas_size_range.width[0]} onChange={(event) => handleSceneField("width", 0, event.target.value)} />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-muted">Width Max</label>
                <Input className="h-10 text-sm" value={activeScene.canvas_size_range.width[1]} onChange={(event) => handleSceneField("width", 1, event.target.value)} />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-muted">Height Min</label>
                <Input className="h-10 text-sm" value={activeScene.canvas_size_range.height[0]} onChange={(event) => handleSceneField("height", 0, event.target.value)} />
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-muted">Height Max</label>
                <Input className="h-10 text-sm" value={activeScene.canvas_size_range.height[1]} onChange={(event) => handleSceneField("height", 1, event.target.value)} />
              </div>
            </div>
            <div className="mt-5 flex items-center justify-between rounded-xl bg-slate-50 border border-line p-3">
              <div>
                <div className="text-sm font-semibold text-ink">Allow Overlap</div>
                <div className="text-[10px] text-muted">Objects can intersect</div>
              </div>
              <input
                type="checkbox"
                className="h-4 w-4 accent-brand rounded"
                checked={activeScene.allow_overlap ?? true}
                onChange={(event) =>
                  updateTemplate((draft) => {
                    const scene = draft.background_scenes.find((s) => s.id === activeSceneId);
                    if (scene) {
                      scene.allow_overlap = event.target.checked;
                    }
                    return draft;
                  })
                }
              />
            </div>
          </div>

          <div className="p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2 font-bold text-ink">
                <Layers size={18} className="text-brand"/> Background Scenes
              </div>
              <div className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-muted">{template.background_scenes.length} Scenes</div>
            </div>
            
            <div className="space-y-3">
              {template.background_scenes.map((scene) => (
                <div
                  key={scene.id}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-2xl border px-3 py-3 text-left transition relative group cursor-pointer",
                    scene.id === activeSceneId ? "border-brand border-[1.5px] bg-white shadow-sm" : "border-line bg-white hover:bg-slate-50"
                  )}
                  onClick={() => handleSceneSwitch(scene.id)}
                >
                  <img
                    src={runtimeAssetUrl(scene.background.image_path)}
                    alt={scene.background.name}
                    className="h-[3.25rem] w-[4.5rem] rounded-xl object-cover border border-line flex-shrink-0"
                  />
                  <div className="min-w-0 flex-1 pr-8">
                    <div className="truncate text-sm font-semibold text-ink">{scene.background.name}</div>
                  </div>
                  
                  {template.background_scenes.length > 1 && (
                    <button 
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 text-rose-500 hover:bg-rose-50 rounded-md border border-transparent hover:border-rose-100"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteBackgroundMutation.mutate(scene.id);
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
              <Button 
                className="w-full border-dashed border-2 py-6 text-muted hover:text-ink font-semibold bg-white border-line/50 hover:bg-slate-50 shadow-none" 
                onClick={() => backgroundInputRef.current?.click()}
              >
                <Plus size={16} className="mr-2" />
                Add Background
              </Button>
              <input
                ref={backgroundInputRef}
                type="file"
                accept=".png,.jpg,.jpeg"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    uploadBackgroundMutation.mutate(file);
                  }
                }}
              />
            </div>
          </div>
        </aside>

        {/* Center Column: Canvas */}
        <main className="flex-1 min-w-0 flex flex-col bg-[#fafbfc]">
          {/* Toolbar */}
          <div className="flex h-16 flex-shrink-0 items-center justify-between border-b border-line bg-white px-6">
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
              <button
                className={cn("flex items-center gap-2 rounded-lg px-4 py-1.5 text-sm font-semibold transition-colors", mode === "select" ? "bg-brand text-white shadow-sm" : "text-muted hover:text-ink")}
                onClick={() => setMode("select")}
              >
                <MousePointer2 size={16} />
                Select
              </button>
              <button
                className={cn("flex items-center gap-2 rounded-lg px-4 py-1.5 text-sm font-semibold transition-colors", mode === "draw" ? "bg-white text-ink shadow-sm" : "text-muted hover:text-ink")}
                onClick={() => setMode("draw")}
                disabled={!inventory.classes.length}
              >
                <SquareDashed size={16} />
                Draw
              </button>
            </div>
            
            <div className="flex items-center gap-3">
              <Button className="bg-white border-none shadow-none text-muted hover:text-ink font-semibold hover:bg-slate-50" onClick={() => void handlePreview()} disabled={previewMutation.isPending || saveMutation.isPending}>
                <Eye size={18} className="mr-2" />
                Preview
              </Button>
              <Button className="font-semibold shadow-sm ml-2" onClick={() => void handleOpenGenerate()} disabled={saveMutation.isPending}>
                Go to Generate
                <ArrowRight size={16} className="ml-2" />
              </Button>
            </div>
          </div>

          {/* Canvas Area */}
          <div className="flex-1 overflow-auto p-8 flex items-center justify-center">
            <div className="rounded-sm shadow-xl bg-white border border-line/50 overflow-hidden">
              <Stage
                width={canvasWidth}
                height={canvasHeight}
                onMouseDown={handlePointerDown}
                onMouseMove={handlePointerMove}
                onMouseUp={handlePointerUp}
              >
                <Layer>
                  {backgroundImage ? (
                    <KonvaImage image={backgroundImage} width={canvasWidth} height={canvasHeight} />
                  ) : (
                    <Rect width={canvasWidth} height={canvasHeight} fill="#f8fafc" />
                  )}
                  {activeScene.blocks.map((block) => {
                    const x = block.bbox[0] * canvasWidth;
                    const y = block.bbox[1] * canvasHeight;
                    const width = block.bbox[2] * canvasWidth;
                    const height = block.bbox[3] * canvasHeight;
                    const color = getClassColor(block.class);
                    const isSelected = block.id === selectedBlockId;
                    return (
                      <Fragment key={block.id}>
                        <Rect
                          ref={isSelected ? selectedRectRef : undefined}
                          x={x}
                          y={y}
                          width={width}
                          height={height}
                          fill={`${color}30`}
                          stroke={color}
                          strokeWidth={2}
                          draggable={mode === "select"}
                          onClick={() => selectBlock(block.id)}
                          onTap={() => selectBlock(block.id)}
                          onDragEnd={(event) => {
                            const node = event.target;
                            updateSelectedBlock((selected) => {
                              if (selected.id === block.id) {
                                selected.bbox = [
                                  clamp(node.x() / canvasWidth, 0, 1),
                                  clamp(node.y() / canvasHeight, 0, 1),
                                  block.bbox[2],
                                  block.bbox[3]
                                ];
                              }
                            });
                          }}
                          onTransformEnd={(event) => {
                            const node = event.target;
                            const scaleX = node.scaleX();
                            const scaleY = node.scaleY();
                            updateSelectedBlock((selected) => {
                              if (selected.id === block.id) {
                                selected.bbox = [
                                  clamp(node.x() / canvasWidth, 0, 1),
                                  clamp(node.y() / canvasHeight, 0, 1),
                                  clamp((node.width() * scaleX) / canvasWidth, 0.02, 1),
                                  clamp((node.height() * scaleY) / canvasHeight, 0.02, 1)
                                ];
                              }
                            });
                            node.scaleX(1);
                            node.scaleY(1);
                          }}
                        />
                      </Fragment>
                    );
                  })}
                  {draftRect && (
                    <Rect
                      x={draftRect.x}
                      y={draftRect.y}
                      width={draftRect.width}
                      height={draftRect.height}
                      fill="rgba(29,143,255,0.16)"
                      stroke="#1d8fff"
                      dash={[8, 6]}
                    />
                  )}
                  <Transformer
                    ref={transformerRef}
                    rotateEnabled={false}
                    keepRatio={false}
                    enabledAnchors={["top-left", "top-center", "top-right", "middle-right", "bottom-right", "bottom-center", "bottom-left", "middle-left"]}
                    borderStroke="#1d8fff"
                    anchorFill="#fff"
                    anchorStroke="#1d8fff"
                    anchorSize={8}
                    anchorCornerRadius={4}
                  />
                </Layer>
              </Stage>
            </div>
          </div>
        </main>

        {/* Right Column: Block Inspector */}
        <aside className="scroll-thin w-[340px] flex-shrink-0 border-l border-line bg-white flex flex-col overflow-y-auto">
          <div className="px-6 py-5 text-xs font-bold tracking-widest text-muted uppercase">Block Inspector</div>
          {!selectedBlock ? (
            <div className="px-6 pb-6">
              <div className="rounded-2xl border border-dashed border-line p-8 text-center text-sm text-muted">
                Select a block on the canvas to view and edit its properties.
              </div>
            </div>
          ) : (
            <>
              {/* Block Header */}
              <div className="px-6 pb-5 flex items-center justify-between border-b border-line">
                <div className="text-brand font-bold text-sm">{selectedBlock.id}</div>
                <button 
                  className="text-rose-500 hover:bg-rose-50 p-2 rounded-lg transition-colors border border-rose-100"
                  onClick={() => {
                    selectBlock(null);
                    updateTemplate((draft) => {
                      const scene = draft.background_scenes.find((item) => item.id === activeScene.id);
                      if (scene) {
                        scene.blocks = scene.blocks.filter((item) => item.id !== selectedBlock.id);
                      }
                      return draft;
                    });
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>

              {/* Spatial Logic */}
              <div className="px-6 py-6 border-b border-line">
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2 font-bold text-ink text-sm">
                    <Settings2 size={16} className="text-muted"/> Spatial Logic
                  </div>
                </div>

                <div className="mb-5">
                  <label className="mb-3 block text-[10px] font-bold uppercase tracking-wider text-muted">Anchor Class</label>
                  <div className="space-y-2">
                    {inventory.classes.map((assetClass) => {
                      const classColor = getClassColor(assetClass.name);
                      const isSelected = selectedBlock.class === assetClass.name;
                      return (
                        <button 
                          key={assetClass.name}
                          className={cn("w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-colors", isSelected ? "bg-slate-50" : "border-line bg-white hover:bg-slate-50")}
                          style={{ borderColor: isSelected ? classColor : undefined }}
                          onClick={() => updateSelectedBlock((block) => {
                            block.class = assetClass.name;
                            block.allowed_subtypes = assetClass.subtypes.map((s) => s.name);
                          })}
                        >
                          <div 
                            className={cn("w-3 h-3 rounded-full border-[3px]")} 
                            style={{ 
                              borderColor: isSelected ? classColor : "#cbd5e1", 
                              backgroundColor: isSelected ? classColor : "transparent" 
                            }} 
                          />
                          <span className="text-sm font-semibold" style={{ color: classColor }}>{assetClass.name}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="mb-5">
                  <label className="mb-3 block text-[10px] font-bold uppercase tracking-wider text-muted">Anchor Subtypes</label>
                  <div className="space-y-3">
                    {(inventory.classes.find((item) => item.name === selectedBlock.class)?.subtypes ?? []).map((subtype) => (
                      <label key={subtype.name} className="flex items-center gap-3 text-sm font-medium text-ink cursor-pointer">
                        <div className={cn("w-4 h-4 rounded-sm flex items-center justify-center border transition-colors", selectedBlock.allowed_subtypes.includes(subtype.name) ? "bg-brand border-brand text-white" : "border-line bg-white")}>
                          {selectedBlock.allowed_subtypes.includes(subtype.name) && <Check size={12} strokeWidth={3}/>}
                        </div>
                        <input
                          type="checkbox"
                          className="hidden"
                          checked={selectedBlock.allowed_subtypes.includes(subtype.name)}
                          onChange={(event) =>
                            updateSelectedBlock((block) => {
                              if (event.target.checked) {
                                block.allowed_subtypes = [...new Set([...block.allowed_subtypes, subtype.name])];
                              } else {
                                block.allowed_subtypes = block.allowed_subtypes.filter((value) => value !== subtype.name);
                              }
                            })
                          }
                        />
                        {subtype.name}
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="mb-3 block text-[10px] font-bold uppercase tracking-wider text-muted">Position Anchor</label>
                  <div className="grid grid-cols-3 gap-2 p-4 bg-slate-50 rounded-2xl border border-line w-fit mx-auto">
                    {anchorOptions.map((anchor) => (
                      <button
                        key={anchor}
                        type="button"
                        className={cn(
                          "w-8 h-8 rounded-lg flex items-center justify-center transition-colors",
                          selectedBlock.position_anchor === anchor ? "bg-brand text-white shadow-sm border border-brand" : "bg-white border border-line text-slate-300 hover:border-muted hover:text-muted"
                        )}
                        onClick={() => updateSelectedBlock((block) => {
                          block.position_anchor = block.position_anchor === anchor ? null : anchor;
                        })}
                      >
                        <div className="w-1.5 h-1.5 rounded-full bg-current" />
                      </button>
                    ))}
                  </div>
                  <div className="mt-3 text-center text-[10px] italic text-muted">Random placement if none selected</div>
                </div>
              </div>

              {/* Parameters */}
              <div className="px-6 py-6 border-b border-line">
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2 font-bold text-ink text-sm">
                    <Info size={16} className="text-muted"/> Parameters
                  </div>
                </div>
                
                <div className="mb-5">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted">Object Capacity</label>
                    <span className="font-bold text-sm">{selectedBlock.capacity}</span>
                  </div>
                  <input
                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand"
                    type="range"
                    min={1}
                    max={10}
                    value={selectedBlock.capacity}
                    onChange={(event) => updateSelectedBlock((block) => {
                      block.capacity = Number(event.target.value);
                    })}
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted">Skip Probability</label>
                    <span className="font-bold text-sm">{selectedBlock.skip_prob.toFixed(2)}</span>
                  </div>
                  <input
                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand"
                    type="range"
                    min={0}
                    max={0.99}
                    step={0.01}
                    value={selectedBlock.skip_prob}
                    onChange={(event) => updateSelectedBlock((block) => {
                      block.skip_prob = Number(event.target.value);
                    })}
                  />
                </div>
              </div>

              {/* Augmentation */}
              <div className="px-6 py-6">
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2 font-bold text-ink text-sm">
                    <RefreshCcw size={16} className="text-muted"/> Augmentation
                  </div>
                </div>
                
                <div className="mb-5">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted">Rotation Max</label>
                    <span className="font-bold text-sm">{selectedBlock.augmentation.rotation_max}°</span>
                  </div>
                  <input
                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand"
                    type="range"
                    min={0}
                    max={180}
                    value={selectedBlock.augmentation.rotation_max}
                    onChange={(event) => updateSelectedBlock((block) => {
                      block.augmentation.rotation_max = Number(event.target.value);
                    })}
                  />
                </div>

                <div className="mb-5">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted">Blur Max</label>
                    <span className="font-bold text-sm">{selectedBlock.augmentation.blur_max}px</span>
                  </div>
                  <input
                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand"
                    type="range"
                    min={0}
                    max={10}
                    step={0.1}
                    value={selectedBlock.augmentation.blur_max}
                    onChange={(event) => updateSelectedBlock((block) => {
                      block.augmentation.blur_max = Number(event.target.value);
                    })}
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted">Noise Max</label>
                    <span className="font-bold text-sm">{Math.round(selectedBlock.augmentation.noise_max * 100)}%</span>
                  </div>
                  <input
                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand"
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={selectedBlock.augmentation.noise_max}
                    onChange={(event) => updateSelectedBlock((block) => {
                      block.augmentation.noise_max = Number(event.target.value);
                    })}
                  />
                </div>
              </div>
            </>
          )}
        </aside>
      </div>

      <Dialog open={generateOpen}>
        <form onSubmit={handleGenerate}>
          <div className="flex items-center gap-3 text-brand">
            <WandSparkles size={24} />
            <div className="text-sm font-semibold uppercase tracking-[0.25em]">Start New Generation</div>
          </div>
          <h2 className="mt-4 text-4xl font-extrabold text-ink">Specify the dataset scale</h2>
          <p className="mt-3 text-muted">Generation runs in the backend workspace and will sample scenes using each scene weight.</p>
          <div className="mt-8">
            <label className="mb-2 block text-sm font-semibold text-ink">Total images to generate</label>
            <Controller
              control={form.control}
              name="count"
              render={({ field }) => <Input type="number" min={1} {...field} />}
            />
            <div className="mt-2 text-sm text-muted">Count must be an integer greater than or equal to 1.</div>
          </div>
          {validation.has_warning && (
            <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Working template has warnings. You can still generate, but results may be suboptimal.
            </div>
          )}
          {dialogMessage && (
            <div className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
              {dialogMessage}
            </div>
          )}
          <div className="mt-8 flex gap-3">
            <Button type="button" className="flex-1 bg-white text-ink border border-line hover:bg-slate-50" onClick={() => setGenerateOpen(false)}>
              Close
            </Button>
            <Button type="submit" className="flex-1">
              Start Generation
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={runningOpen}>
        <div className="text-center">
          <h2 className="text-4xl font-extrabold text-ink">Generating Dataset</h2>
          <p className="mt-4 text-muted">The backend is building the dataset in your local workspace.</p>
          <div className="mt-8 h-3 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand transition-all"
              style={{
                width: `${Math.min(
                  100,
                  ((jobQuery.data?.generated_count ?? 0) / Math.max(1, (jobQuery.data?.count ?? lastCount) || 1)) * 100
                )}%`
              }}
            />
          </div>
          <div className="mt-3 text-sm font-semibold text-muted">
            {jobQuery.data?.generated_count ?? 0} / {(jobQuery.data?.count ?? lastCount)} generated
          </div>
          <div className="mt-8">
            <Button className="w-full bg-rose-600 hover:bg-rose-700" onClick={() => jobId && cancelJobMutation.mutate(jobId)}>
              Cancel
            </Button>
          </div>
        </div>
      </Dialog>

      <Dialog open={successOpen}>
        <SuccessDialog
          jobId={jobId}
          lastCount={lastCount}
          exportFormat={exportFormat}
          setExportFormat={setExportFormat}
          trainEnd={trainEnd}
          setTrainEnd={setTrainEnd}
          validEnd={validEnd}
          setValidEnd={setValidEnd}
          onClose={() => setSuccessOpen(false)}
          onDownload={(split) => jobId && exportMutation.mutate({ jobId, format: exportFormat, split })}
          isExporting={exportMutation.isPending}
        />
      </Dialog>
    </div>
  );
}

function extractErrorMessage(error: unknown) {
  if (typeof error === "string") {
    return error;
  }
  if (typeof error === "object" && error !== null) {
    const maybeDetail = (error as { detail?: unknown }).detail;
    if (typeof maybeDetail === "string") {
      return maybeDetail;
    }
    if (typeof maybeDetail === "object" && maybeDetail !== null && "message" in maybeDetail) {
      return String((maybeDetail as { message: string }).message);
    }
  }
  return "Request failed.";
}

// ---------------------------------------------------------------------------
// SuccessDialog — train / valid / test split selector + format toggle
// ---------------------------------------------------------------------------

const SPLIT_COLORS = {
  train: { bar: "#7c3aed", text: "text-violet-600", bg: "bg-violet-50", border: "border-violet-200", label: "Train", icon: "🧠" },
  valid: { bar: "#0ea5e9", text: "text-sky-500",    bg: "bg-sky-50",    border: "border-sky-200",    label: "Valid", icon: "🛡" },
  test:  { bar: "#f59e0b", text: "text-amber-500",  bg: "bg-amber-50",  border: "border-amber-200",  label: "Test",  icon: "🧪" },
} as const;

function SuccessDialog({
  jobId,
  lastCount,
  exportFormat,
  setExportFormat,
  trainEnd,
  setTrainEnd,
  validEnd,
  setValidEnd,
  onClose,
  onDownload,
  isExporting,
}: {
  jobId: string | null;
  lastCount: number;
  exportFormat: "yolo" | "coco";
  setExportFormat: (f: "yolo" | "coco") => void;
  trainEnd: number;
  setTrainEnd: (v: number) => void;
  validEnd: number;
  setValidEnd: (v: number) => void;
  onClose: () => void;
  onDownload: (split: SplitConfig) => void;
  isExporting: boolean;
}) {
  const MIN_GAP = 5; // minimum % each boundary must be separated

  const trainPct = trainEnd;
  const validPct = validEnd - trainEnd;
  const testPct  = 100 - validEnd;

  const trainCount = Math.round((trainPct / 100) * lastCount);
  const validCount = Math.round((validPct / 100) * lastCount);
  const testCount  = lastCount - trainCount - validCount;

  const sliderRef = useRef<HTMLDivElement>(null);

  /** Convert a pointer event X to a 0-100 value clamped to the slider bounds */
  const pxToVal = (clientX: number): number => {
    const rect = sliderRef.current?.getBoundingClientRect();
    if (!rect) return 0;
    return Math.max(0, Math.min(100, Math.round(((clientX - rect.left) / rect.width) * 100)));
  };

  const startDrag = (thumb: "train" | "valid") => (e: React.PointerEvent) => {
    e.currentTarget.setPointerCapture(e.pointerId);

    const onMove = (ev: PointerEvent) => {
      const val = pxToVal(ev.clientX);
      if (thumb === "train") {
        const clamped = Math.max(MIN_GAP, Math.min(val, validEnd - MIN_GAP));
        setTrainEnd(clamped);
      } else {
        const clamped = Math.max(trainEnd + MIN_GAP, Math.min(val, 100 - MIN_GAP));
        setValidEnd(clamped);
      }
    };

    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  const handleDownload = () => {
    const total = trainPct + validPct + testPct; // always 100
    onDownload({
      train: trainPct / total,
      valid: validPct / total,
      test:  testPct  / total,
    });
  };

  return (
    <div>
      {/* Header */}
      <div className="text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border-[3px] border-ink text-ink">
          <Check strokeWidth={3} size={24} />
        </div>
        <h2 className="mt-5 text-2xl font-extrabold text-ink">Dataset Generated!</h2>
        <p className="mt-2 text-sm text-muted">
          Your synthetic object detection dataset is<br />ready for use.
        </p>
      </div>

      {/* Split cards */}
      <div className="mt-8 grid grid-cols-3 gap-3">
        {(["train", "valid", "test"] as const).map((key) => {
          const cfg = SPLIT_COLORS[key];
          const pct  = key === "train" ? trainPct : key === "valid" ? validPct : testPct;
          const cnt  = key === "train" ? trainCount : key === "valid" ? validCount : testCount;
          return (
            <div key={key} className={cn("rounded-2xl border px-3 py-3 text-center", cfg.bg, cfg.border)}>
              <div className="text-base mb-0.5">{cfg.icon}</div>
              <div className={cn("text-xs font-bold uppercase tracking-wider mb-1", cfg.text)}>{cfg.label}</div>
              <div className={cn("text-2xl font-extrabold", cfg.text)}>{pct}%</div>
              <div className="text-[11px] text-muted font-medium mt-0.5">{cnt.toLocaleString()} IMAGES</div>
            </div>
          );
        })}
      </div>

      {/* Dual-range slider */}
      <div className="mt-5 px-1" ref={sliderRef}>
        <div className="relative h-3 rounded-full bg-slate-100 select-none" style={{ cursor: "default" }}>
          {/* Train segment */}
          <div
            className="absolute top-0 h-full rounded-l-full"
            style={{ left: 0, width: `${trainEnd}%`, backgroundColor: SPLIT_COLORS.train.bar }}
          />
          {/* Valid segment */}
          <div
            className="absolute top-0 h-full"
            style={{ left: `${trainEnd}%`, width: `${validPct}%`, backgroundColor: SPLIT_COLORS.valid.bar }}
          />
          {/* Test segment */}
          <div
            className="absolute top-0 h-full rounded-r-full"
            style={{ left: `${validEnd}%`, right: 0, backgroundColor: SPLIT_COLORS.test.bar }}
          />

          {/* Train/Valid thumb */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 rounded-full bg-white border-4 shadow-md cursor-ew-resize z-10 transition-shadow hover:shadow-lg"
            style={{ left: `${trainEnd}%`, borderColor: SPLIT_COLORS.train.bar }}
            onPointerDown={startDrag("train")}
          />

          {/* Valid/Test thumb */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 rounded-full bg-white border-4 shadow-md cursor-ew-resize z-10 transition-shadow hover:shadow-lg"
            style={{ left: `${validEnd}%`, borderColor: SPLIT_COLORS.test.bar }}
            onPointerDown={startDrag("valid")}
          />
        </div>
      </div>

      {/* Export format */}
      <div className="mt-6 flex items-center justify-between border-t border-line pt-5">
        <span className="text-sm font-semibold text-muted">Export Format</span>
        <div className="flex bg-slate-50 rounded-full p-1 border border-line">
          {(["yolo", "coco"] as const).map((fmt) => (
            <button
              key={fmt}
              className={cn(
                "px-4 py-1 text-xs font-bold rounded-full transition-colors uppercase",
                exportFormat === fmt ? "bg-blue-100 text-blue-600 shadow-sm" : "text-muted hover:text-ink"
              )}
              onClick={() => setExportFormat(fmt)}
            >
              {fmt}
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="mt-5 flex gap-3">
        <Button
          className="flex-1 bg-white text-ink border border-line shadow-none hover:bg-slate-50"
          onClick={onClose}
        >
          Close
        </Button>
        <Button
          className="flex-1"
          onClick={handleDownload}
          disabled={isExporting}
        >
          <Download size={18} className="mr-2" />
          {isExporting ? "Preparing…" : "Download Dataset"}
        </Button>
      </div>
    </div>
  );
}
