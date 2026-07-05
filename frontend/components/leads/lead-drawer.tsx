"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";

import { IntentBadge, ScorePill } from "@/components/leads/intent-badge";
import { StatusActions, StatusChip } from "@/components/leads/status-chip";
import { Drawer } from "@/components/ui/drawer";
import { api } from "@/lib/api";
import type { Lead, LeadStatus } from "@/lib/types";
import { formatDateTime, formatPrice } from "@/lib/utils";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-sm">{children}</div>
    </div>
  );
}

export function LeadDrawer({ lead, onClose }: { lead: Lead | null; onClose: () => void }) {
  const queryClient = useQueryClient();

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: LeadStatus }) =>
      api.patch<Lead>(`/leads/${id}/status`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      onClose();
    },
  });

  const classification = lead?.classification;

  return (
    <Drawer
      open={lead !== null}
      onClose={onClose}
      title={
        lead && (
          <div className="flex items-center gap-2">
            {classification && <IntentBadge intent={classification.intent} />}
            <span className="truncate">{lead.title ?? "Lead detail"}</span>
          </div>
        )
      }
    >
      {lead && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-4">
            <Field label="Score">
              <ScorePill score={lead.score} />
            </Field>
            {classification && (
              <Field label="Confidence">
                <span className="tabular-nums">{classification.confidence}%</span>
              </Field>
            )}
            <Field label="Status">
              <StatusChip status={lead.status} />
            </Field>
            <Field label="Classifier">
              <code className="text-xs">{classification?.model ?? "—"}</code>
            </Field>
          </div>

          <div className="rounded-md border bg-muted/40 p-4 text-sm leading-relaxed">
            {lead.content}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Source">{lead.source_key}</Field>
            <Field label="Author">{lead.author ?? "—"}</Field>
            <Field label="Product">{lead.product ?? "—"}</Field>
            <Field label="Price">{formatPrice(lead.price_value, lead.price_currency)}</Field>
            <Field label="Location">{lead.location ?? "—"}</Field>
            <Field label="Date mentioned">{lead.event_date ?? "—"}</Field>
            <Field label="Posted">{formatDateTime(lead.posted_at)}</Field>
            <Field label="Collected">{formatDateTime(lead.created_at)}</Field>
          </div>

          {lead.url && (
            <a
              href={lead.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
            >
              View original post <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}

          {classification && classification.reasons.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Why this classification
              </div>
              <ul className="space-y-1.5">
                {classification.reasons.map((reason, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Set status
            </div>
            <StatusActions
              current={lead.status}
              disabled={statusMutation.isPending}
              onChange={(status) => statusMutation.mutate({ id: lead.id, status })}
            />
            {statusMutation.isError && (
              <p className="mt-2 text-xs text-destructive">Failed to update status. Try again.</p>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}
