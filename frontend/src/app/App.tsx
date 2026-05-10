import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchWorkingTemplate } from "../api/client";
import { ToastViewport } from "../components/ui/toast";
import { EditorScreen } from "../features/editor/EditorScreen";
import { UploadScreen } from "../features/upload/UploadScreen";
import { useEditorStore } from "../store/editor-store";

export function App() {
  const screen = useEditorStore((state) => state.screen);
  const setScreen = useEditorStore((state) => state.setScreen);
  const initializeSnapshot = useEditorStore((state) => state.initializeSnapshot);
  const pushToast = useEditorStore((state) => state.pushToast);
  const [refreshToken, setRefreshToken] = useState(0);

  const workingTemplateQuery = useQuery({
    queryKey: ["working-template", refreshToken],
    queryFn: fetchWorkingTemplate,
    enabled: screen === "editor"
  });

  useEffect(() => {
    if (workingTemplateQuery.data) {
      initializeSnapshot(workingTemplateQuery.data);
    }
  }, [initializeSnapshot, workingTemplateQuery.data]);

  const refresh = async () => {
    setRefreshToken((value) => value + 1);
    await workingTemplateQuery.refetch();
  };

  return (
    <>
      {screen === "upload" ? (
        <UploadScreen
          onUploaded={() => {
            setScreen("editor");
            void refresh();
          }}
        />
      ) : workingTemplateQuery.data ? (
        <EditorScreen snapshot={workingTemplateQuery.data} onRefresh={refresh} />
      ) : workingTemplateQuery.isError ? (
        <div className="flex min-h-screen items-center justify-center">
          <button
            className="rounded-2xl border border-line bg-white px-5 py-3 text-sm font-semibold"
            onClick={() => {
              pushToast("Unable to load working template snapshot.", "error");
              void refresh();
            }}
          >
            Retry loading editor
          </button>
        </div>
      ) : (
        <div className="flex min-h-screen items-center justify-center text-sm text-muted">Loading editor workspace...</div>
      )}
      <ToastViewport />
    </>
  );
}
