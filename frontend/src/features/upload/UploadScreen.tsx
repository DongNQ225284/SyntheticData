import { UploadCloud, Info, CheckCircle2, FileText } from "lucide-react";
import type { DragEvent } from "react";
import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { uploadArchive } from "../../api/client";
import { Button } from "../../components/ui/button";
import { useEditorStore } from "../../store/editor-store";

export function UploadScreen({ onUploaded }: { onUploaded: () => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const pushToast = useEditorStore((state) => state.pushToast);

  const uploadMutation = useMutation({
    mutationFn: uploadArchive,
    onSuccess: () => {
      onUploaded();
    },
    onError: (error) => {
      const message = typeof error === "string" ? error : JSON.stringify(error);
      pushToast(message, "error");
    }
  });

  const handleFile = (file: File | null) => {
    if (!file) return;
    uploadMutation.mutate(file);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    handleFile(event.dataTransfer.files[0] ?? null);
  };

  return (
    <div className="flex min-h-screen flex-col bg-white font-sans text-ink">
      {/* Top Header */}
      <header className="flex h-16 items-center px-6 border-b border-line">
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
        
        <div className="flex items-center gap-4 text-sm font-medium text-muted">
          <div className="flex items-center gap-2 text-brand bg-brand/5 px-3 py-1.5 rounded-full">
            <div className="flex h-5 w-5 items-center justify-center rounded-full border border-brand text-[10px]">1</div>
            <span>Upload</span>
          </div>
          <span>&gt;</span>
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-full border border-muted text-[10px]">2</div>
            <span>Editor</span>
          </div>
        </div>
        <div className="flex-1"></div>
      </header>

      {/* Main Content */}
      <main className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        <div className="text-center w-full max-w-4xl">
          <h1 className="text-[3.25rem] font-extrabold tracking-tight text-ink mb-4">
            Generate Synthetic Datasets
          </h1>
          <p className="mx-auto max-w-2xl text-[1.1rem] text-muted mb-12 leading-relaxed">
            Upload an asset archive, compose scene layouts, and generate synthetic training images for high-performance object detection.
          </p>

          <div
            className={`mx-auto w-full max-w-[56rem] rounded-[1.5rem] border-[1.5px] border-dashed transition-all duration-200 px-8 py-16 ${
              dragging ? "border-brand bg-brand/5 scale-[1.02]" : "border-line bg-white hover:border-brand/50"
            }`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div className="mx-auto flex max-w-md flex-col items-center text-center">
              <div className="mb-6 flex h-[4.5rem] w-[4.5rem] items-center justify-center rounded-full border-2 border-brand/10 bg-white text-brand shadow-sm">
                <FileText size={32} strokeWidth={1.5} />
              </div>
              
              <h2 className="mb-3 text-2xl font-bold">Upload asset archive</h2>
              <p className="mb-8 text-muted">
                Drag and drop or choose a <span className="font-semibold text-ink">.zip</span> or <span className="font-semibold text-ink">.rar</span> file containing your object segments.
              </p>

              <Button 
                type="button" 
                onClick={() => inputRef.current?.click()} 
                disabled={uploadMutation.isPending}
                className="mb-8 flex h-11 items-center gap-2 rounded-lg px-6 font-semibold shadow-sm"
              >
                <UploadCloud size={18} />
                {uploadMutation.isPending ? "Processing..." : "Select Archive"}
              </Button>
              <input
                ref={inputRef}
                type="file"
                accept=".zip,.rar"
                className="hidden"
                onChange={(event) => handleFile(event.target.files?.[0] ?? null)}
              />

              <div className="flex items-center gap-2 rounded-full border border-line bg-slate-50/50 px-4 py-1.5 text-xs font-medium text-muted">
                <Info size={14} />
                <span>Expected structure: class/subtype/image_files</span>
              </div>
            </div>
          </div>

          <div className="mt-8 flex justify-center gap-10 text-xs font-medium text-muted">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} />
              <span>Max size: 2GB</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} />
              <span>Transparent PNGs only</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} />
              <span>Sequential processing</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

