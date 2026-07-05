import type { IntentLabel } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Identity dot uses the validated chart palette; the text stays in ink tokens. */
const INTENT_DOT: Record<IntentLabel, string> = {
  BUY: "bg-[var(--viz-buy)]",
  SELL: "bg-[var(--viz-sell)]",
  MENTION: "bg-[var(--viz-mention)]",
  SPAM: "bg-[var(--viz-spam)]",
};

export function IntentBadge({ intent }: { intent: IntentLabel }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium">
      <span className={cn("h-2 w-2 rounded-full", INTENT_DOT[intent])} aria-hidden />
      {intent}
    </span>
  );
}

export function ScorePill({ score }: { score: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm tabular-nums">
      <span className="relative h-1.5 w-12 overflow-hidden rounded-full bg-muted" aria-hidden>
        <span
          className="absolute inset-y-0 left-0 rounded-full bg-[var(--viz-series-1)]"
          style={{ width: `${score}%` }}
        />
      </span>
      {score}
    </span>
  );
}
