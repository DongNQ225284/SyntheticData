import type { ReactNode } from "react";
import { Card } from "./card";

export function Dialog({
  open,
  children
}: {
  open: boolean;
  children: ReactNode;
}) {
  if (!open) {
    return null;
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/25 p-6 backdrop-blur-sm">
      <Card className="w-full max-w-xl border border-brand/20 bg-white p-8">{children}</Card>
    </div>
  );
}
