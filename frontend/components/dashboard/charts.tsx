"use client";

import type { IntentLabel } from "@/lib/types";

/** Chart colors come from CSS vars set in globals.css — both modes were
 *  validated with the dataviz palette checker (CVD ΔE > 35, light-mode
 *  sub-3:1 slots relieved with direct value labels in ink). */
const INTENT_VAR: Record<IntentLabel, string> = {
  BUY: "var(--viz-buy)",
  SELL: "var(--viz-sell)",
  MENTION: "var(--viz-mention)",
  SPAM: "var(--viz-spam)",
};
const INTENT_ORDER: IntentLabel[] = ["BUY", "SELL", "MENTION", "SPAM"];

export function IntentBreakdownChart({ data }: { data: Record<string, number> }) {
  const max = Math.max(1, ...INTENT_ORDER.map((k) => data[k] ?? 0));
  return (
    <div className="space-y-2.5" role="img" aria-label="Leads by intent">
      {INTENT_ORDER.map((intent) => {
        const value = data[intent] ?? 0;
        return (
          <div key={intent} className="group flex items-center gap-3 text-sm">
            <span className="w-16 shrink-0 text-xs font-medium text-muted-foreground">{intent}</span>
            <div className="relative h-5 flex-1">
              <div
                className="absolute inset-y-0 left-0 rounded-r"
                title={`${intent}: ${value} lead${value === 1 ? "" : "s"}`}
                style={{
                  width: `${(value / max) * 100}%`,
                  minWidth: value > 0 ? "4px" : 0,
                  background: INTENT_VAR[intent],
                }}
              />
              {/* direct value label in ink (relief rule for sub-3:1 slots) */}
              <span
                className="absolute top-1/2 -translate-y-1/2 pl-1.5 text-xs tabular-nums text-foreground"
                style={{ left: `min(${(value / max) * 100}%, calc(100% - 28px))` }}
              >
                {value}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function LeadsPerDayChart({ data: raw }: { data: { date: string; count: number }[] }) {
  // Fill the full 14-day window so quiet days render as gaps, not a stretched bar
  const byDate = new Map(raw.map((d) => [d.date, d.count]));
  const data: { date: string; count: number }[] = [];
  for (let i = 13; i >= 0; i--) {
    const day = new Date(Date.now() - i * 86_400_000).toISOString().slice(0, 10);
    data.push({ date: day, count: byDate.get(day) ?? 0 });
  }
  if (raw.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">No leads in the last 14 days.</p>;
  }
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div role="img" aria-label="New leads per day, last 14 days">
      <div className="flex h-28 items-end gap-[2px] border-b" style={{ borderColor: "var(--viz-axis)" }}>
        {data.map((day) => (
          <div
            key={day.date}
            className="group relative flex-1"
            title={`${day.date}: ${day.count} lead${day.count === 1 ? "" : "s"}`}
          >
            <div
              className="mx-auto w-full rounded-t transition-opacity group-hover:opacity-80"
              style={{
                height: `${Math.max(3, (day.count / max) * 104)}px`,
                background: "var(--viz-series-1)",
              }}
            />
            <span className="pointer-events-none absolute -top-6 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded border bg-card px-1.5 py-0.5 text-[10px] tabular-nums shadow-sm group-hover:block">
              {day.count}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[10px]" style={{ color: "var(--viz-muted-ink)" }}>
        <span>{data[0]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-lg border bg-card p-5">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="mt-1 text-3xl font-semibold">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
