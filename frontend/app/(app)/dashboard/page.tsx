"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { IntentBreakdownChart, LeadsPerDayChart, StatTile } from "@/components/dashboard/charts";
import { IntentBadge, ScorePill } from "@/components/leads/intent-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

export default function DashboardPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => api.get<DashboardStats>("/leads/stats"),
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <Card className="mx-auto max-w-md text-center">
        <CardHeader>
          <CardTitle>Couldn&apos;t load the dashboard</CardTitle>
          <CardDescription>The API may still be starting up.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => refetch()}>Retry</Button>
        </CardContent>
      </Card>
    );
  }

  const buyCount = data.by_intent["BUY"] ?? 0;
  const sellCount = data.by_intent["SELL"] ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Your intent-lead pipeline at a glance.</p>
        </div>
        <Link href="/campaigns/new">
          <Button>New campaign</Button>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Total leads" value={data.total_leads} hint={`avg score ${data.avg_score}`} />
        <StatTile label="Buy intent" value={buyCount} hint="posts wanting to purchase" />
        <StatTile label="Sell intent" value={sellCount} hint="posts offering to sell" />
        <StatTile label="Campaigns" value={data.campaigns} hint="active product radars" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Leads by intent</CardTitle>
            <CardDescription>Classification across all campaigns</CardDescription>
          </CardHeader>
          <CardContent>
            <IntentBreakdownChart data={data.by_intent} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">New leads per day</CardTitle>
            <CardDescription>Last 14 days</CardDescription>
          </CardHeader>
          <CardContent>
            <LeadsPerDayChart data={data.leads_last_14_days} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base">Recent leads</CardTitle>
            <CardDescription>Latest classified posts</CardDescription>
          </div>
          <Link href="/leads" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.recent_leads.length === 0 && (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No leads yet — create a campaign and run it.
            </p>
          )}
          {data.recent_leads.map((lead) => (
            <div key={lead.id} className="flex items-center justify-between gap-3 rounded-md border p-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{lead.title ?? lead.content.slice(0, 80)}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {lead.source_key} · {lead.author ?? "unknown"} · {formatDateTime(lead.posted_at ?? lead.created_at)}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                {lead.classification && <IntentBadge intent={lead.classification.intent} />}
                <ScorePill score={lead.score} />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
