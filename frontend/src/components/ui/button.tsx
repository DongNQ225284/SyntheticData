import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function Button({
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex h-11 items-center justify-center rounded-xl border border-brand/20 bg-brand px-4 font-semibold text-white shadow-panel transition hover:bg-[#147ee6] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
