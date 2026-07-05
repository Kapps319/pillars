"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { LeadDrawer } from "@/components/leads/lead-drawer";
import { LeadsTable } from "@/components/leads/leads-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Campaign, Job, Lead, Page, RunCampaignResponse } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

const JOB_BADGE: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  SUCCESS: "secondary",
  RUNNING: "default",
  PENDING: "outline",
  FAILED: "destructive",
};

export default function CampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const campaignId = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const { data: campaign, isLoading } = useQuery({
    queryKey: ["campaign", campaignId],
    queryFn: () => api.get<Campaign>(`/campaigns/${campaignId}`),
  });

  const { data: jobs } = useQuery({
    queryKey: ["jobs", campaignId],
    queryFn: () => api.get<Job[]>(`/campaigns/${campaignId}/jobs`),
    refetchInterval: (query) =>
      query.state.data?.some((j) => j.status === "PENDING" || j.status === "RUNNING") ? 2000 : false,
  });

  const { data: leads } = useQuery({
    queryKey: ["leads", { campaign_id: campaignId }, jobs?.[0]?.status],
    queryFn: () => api.get<Page<Lead>>(`/leads?campaign_id=${campaignId}&page_size=50`),
  });

  const runMutation = useMutation({
    mutationFn: () => api.post<RunCampaignResponse>(`/campaigns/${campaignId}/run`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs", campaignId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/campaigns/${campaignId}`),
    onSuccess: () => router.push("/campaigns"),
  });

  if (isLoading || !campaign) {
    return <Skeleton className="h-64" />;
  }

  const lastJob = jobs?.[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">{campaign.name}</h1>
            <Badge variant="secondary">{campaign.intent_target}</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            “{campaign.product_keyword}”
            {campaign.location ? ` · ${campaign.location}` : ""} · min confidence{" "}
            {campaign.min_confidence} · sources: {campaign.sources.join(", ")}
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
            <Play className="h-4 w-4" />
            {runMutation.isPending ? "Starting…" : "Run now"}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Delete campaign"
            onClick={() => {
              if (confirm("Delete this campaign (and hide its leads)?")) deleteMutation.mutate();
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {runMutation.isError && (
        <p className="text-sm text-destructive">
          {(runMutation.error as Error).message ?? "Failed to start job"}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Runs</CardTitle>
          <CardDescription>
            Sources missing API keys are skipped and reported here — never fatal.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {(jobs ?? []).length === 0 && (
            <p className="py-2 text-sm text-muted-foreground">Never run. Hit “Run now”.</p>
          )}
          {jobs?.slice(0, 5).map((job) => (
            <div key={job.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3 text-sm">
              <div className="flex items-center gap-3">
                <Badge variant={JOB_BADGE[job.status] ?? "outline"}>{job.status}</Badge>
                <span className="text-muted-foreground">{formatDateTime(job.created_at)}</span>
              </div>
              <div className="text-xs text-muted-foreground">
                {Object.entries(job.stats).map(([source, stat]) => (
                  <span key={source} className="mr-3">
                    {source}:{" "}
                    {"created" in stat
                      ? `${stat.created as number} new / ${stat.fetched as number} fetched`
                      : ((stat.skipped as string) ?? (stat.error as string) ?? "—")}
                  </span>
                ))}
                {job.error && <span className="text-destructive">{job.error}</span>}
              </div>
            </div>
          ))}
          {lastJob?.status === "RUNNING" && (
            <p className="text-xs text-muted-foreground">Refreshing every 2s while the job runs…</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base">Leads ({leads?.total ?? 0})</CardTitle>
            <CardDescription>Top 50 by score — full filters on the Leads page</CardDescription>
          </div>
          <Link href={`/leads?campaign_id=${campaignId}`} className="text-sm text-primary hover:underline">
            Open in Leads
          </Link>
        </CardHeader>
        <CardContent>
          <LeadsTable
            leads={leads?.items ?? []}
            onSelect={setSelectedLead}
            emptyHint="Run the campaign to collect leads."
          />
        </CardContent>
      </Card>

      <LeadDrawer lead={selectedLead} onClose={() => setSelectedLead(null)} />
    </div>
  );
}
