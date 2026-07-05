"use client";

import type { LeadStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export const LEAD_STATUSES: LeadStatus[] = ["NEW", "SAVED", "CONTACTED", "REJECTED"];

const STYLES: Record<LeadStatus, string> = {
  NEW: "border-border bg-secondary text-secondary-foreground",
  SAVED: "border-transparent bg-accent text-accent-foreground",
  CONTACTED: "border-transparent bg-primary/15 text-primary",
  REJECTED: "border-transparent bg-muted text-muted-foreground line-through",
};

export function StatusChip({ status }: { status: LeadStatus }) {
  return (
    <span className={cn("inline-flex rounded-full border px-2 py-0.5 text-xs font-medium", STYLES[status])}>
      {status}
    </span>
  );
}

export function StatusActions({
  current,
  onChange,
  disabled,
}: {
  current: LeadStatus;
  onChange: (status: LeadStatus) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {LEAD_STATUSES.map((status) => (
        <button
          key={status}
          type="button"
          disabled={disabled || status === current}
          onClick={() => onChange(status)}
          className={cn(
            "rounded-full border px-2.5 py-1 text-xs font-medium transition-colors hover:bg-accent disabled:cursor-default",
            status === current
              ? "border-primary bg-primary/10 text-primary"
              : "border-border text-muted-foreground",
          )}
        >
          {status}
        </button>
      ))}
    </div>
  );
}
