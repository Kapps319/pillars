"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Campaign } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

export default function CampaignsPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => api.get<Campaign[]>("/campaigns"),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Campaigns</h1>
          <p className="text-sm text-muted-foreground">
            A campaign scans your selected sources for one product/market.
          </p>
        </div>
        <Link href="/campaigns/new">
          <Button>
            <Plus className="h-4 w-4" /> New campaign
          </Button>
        </Link>
      </div>

      {isLoading && (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-36" />
          ))}
        </div>
      )}

      {isError && (
        <Card className="text-center">
          <CardContent className="py-8">
            <p className="mb-3 text-sm text-muted-foreground">Failed to load campaigns.</p>
            <Button onClick={() => refetch()}>Retry</Button>
          </CardContent>
        </Card>
      )}

      {data && data.length === 0 && (
        <Card className="text-center">
          <CardContent className="py-10">
            <p className="mb-1 font-medium">No campaigns yet</p>
            <p className="mb-4 text-sm text-muted-foreground">
              Create one for any product — F1 tickets, laptops, apartments…
            </p>
            <Link href="/campaigns/new">
              <Button>Create your first campaign</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {data?.map((campaign) => (
          <Link key={campaign.id} href={`/campaigns/${campaign.id}`}>
            <Card className="h-full transition-colors hover:border-primary/40">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base">{campaign.name}</CardTitle>
                  <Badge variant="secondary">{campaign.intent_target}</Badge>
                </div>
                <CardDescription>
                  “{campaign.product_keyword}”{campaign.location ? ` · ${campaign.location}` : ""}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex items-center justify-between text-sm text-muted-foreground">
                <span>
                  <span className="font-semibold text-foreground">{campaign.lead_count ?? 0}</span> leads
                </span>
                <span>
                  {campaign.last_job_status
                    ? `last run ${campaign.last_job_status.toLowerCase()} · ${formatDateTime(campaign.last_job_at)}`
                    : "never run"}
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
