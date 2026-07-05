"use client";

import { ExternalLink } from "lucide-react";

import { IntentBadge, ScorePill } from "@/components/leads/intent-badge";
import { StatusChip } from "@/components/leads/status-chip";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Lead } from "@/lib/types";
import { formatDateTime, formatPrice } from "@/lib/utils";

export function LeadsTable({
  leads,
  onSelect,
  emptyHint = "No leads match these filters.",
}: {
  leads: Lead[];
  onSelect: (lead: Lead) => void;
  emptyHint?: string;
}) {
  if (leads.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">{emptyHint}</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Post</TableHead>
          <TableHead>Intent</TableHead>
          <TableHead>Score</TableHead>
          <TableHead>Price</TableHead>
          <TableHead>Location</TableHead>
          <TableHead>Source</TableHead>
          <TableHead>Posted</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {leads.map((lead) => (
          <TableRow key={lead.id} className="cursor-pointer" onClick={() => onSelect(lead)}>
            <TableCell className="max-w-[320px]">
              <div className="truncate font-medium">{lead.title ?? lead.content.slice(0, 70)}</div>
              <div className="truncate text-xs text-muted-foreground">
                {lead.author ?? "unknown"} · {lead.content.slice(0, 90)}
              </div>
            </TableCell>
            <TableCell>{lead.classification ? <IntentBadge intent={lead.classification.intent} /> : "—"}</TableCell>
            <TableCell>
              <ScorePill score={lead.score} />
            </TableCell>
            <TableCell className="whitespace-nowrap tabular-nums">
              {formatPrice(lead.price_value, lead.price_currency)}
            </TableCell>
            <TableCell className="whitespace-nowrap">{lead.location ?? "—"}</TableCell>
            <TableCell>
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                {lead.source_key}
                {lead.url && <ExternalLink className="h-3 w-3" />}
              </span>
            </TableCell>
            <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
              {formatDateTime(lead.posted_at ?? lead.created_at)}
            </TableCell>
            <TableCell>
              <StatusChip status={lead.status} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
