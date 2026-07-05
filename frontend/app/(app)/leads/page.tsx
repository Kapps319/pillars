"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { LeadDrawer } from "@/components/leads/lead-drawer";
import { LeadsTable } from "@/components/leads/leads-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, downloadCsv, leadQueryString } from "@/lib/api";
import type { Campaign, Lead, LeadFilters, Page } from "@/lib/types";

function LeadsPageInner() {
  const searchParams = useSearchParams();
  const initialCampaign = searchParams.get("campaign_id");

  const [filters, setFilters] = useState<LeadFilters>({
    campaign_id: initialCampaign ? Number(initialCampaign) : undefined,
    sort_by: "score",
    sort_dir: "desc",
    page: 1,
    page_size: 25,
  });
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [exporting, setExporting] = useState(false);

  const { data: campaigns } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => api.get<Campaign[]>("/campaigns"),
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["leads", filters],
    queryFn: () => api.get<Page<Lead>>(`/leads?${leadQueryString(filters)}`),
    placeholderData: keepPreviousData,
  });

  function setFilter<K extends keyof LeadFilters>(key: K, value: LeadFilters[K]) {
    setFilters((current) => ({ ...current, [key]: value, page: key === "page" ? (value as number) : 1 }));
  }

  async function onExport() {
    setExporting(true);
    try {
      await downloadCsv(filters);
    } finally {
      setExporting(false);
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / (filters.page_size ?? 25))) : 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Leads</h1>
          <p className="text-sm text-muted-foreground">
            {data ? `${data.total} leads` : "…"} · click a row for full detail & reasons
          </p>
        </div>
        <Button variant="outline" onClick={onExport} disabled={exporting || !data?.total}>
          <Download className="h-4 w-4" />
          {exporting ? "Exporting…" : "Export CSV"}
        </Button>
      </div>

      {/* Filter row */}
      <Card>
        <CardContent className="grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-7">
          <Select
            aria-label="Campaign"
            value={filters.campaign_id ?? ""}
            onChange={(e) => setFilter("campaign_id", e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">All campaigns</option>
            {campaigns?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <Select
            aria-label="Intent"
            value={filters.intent ?? ""}
            onChange={(e) => setFilter("intent", (e.target.value || undefined) as LeadFilters["intent"])}
          >
            <option value="">All intents</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
            <option value="MENTION">MENTION</option>
            <option value="SPAM">SPAM</option>
          </Select>
          <Select
            aria-label="Status"
            value={filters.status ?? ""}
            onChange={(e) => setFilter("status", (e.target.value || undefined) as LeadFilters["status"])}
          >
            <option value="">All statuses</option>
            <option value="NEW">NEW</option>
            <option value="SAVED">SAVED</option>
            <option value="CONTACTED">CONTACTED</option>
            <option value="REJECTED">REJECTED</option>
          </Select>
          <Select
            aria-label="Minimum score"
            value={filters.min_score ?? ""}
            onChange={(e) => setFilter("min_score", e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">Any score</option>
            <option value="50">Score ≥ 50</option>
            <option value="70">Score ≥ 70</option>
            <option value="85">Score ≥ 85</option>
          </Select>
          <Input
            aria-label="Location filter"
            placeholder="Location…"
            defaultValue={filters.location ?? ""}
            onBlur={(e) => setFilter("location", e.target.value || undefined)}
            onKeyDown={(e) => e.key === "Enter" && setFilter("location", e.currentTarget.value || undefined)}
          />
          <Input
            aria-label="Search text"
            placeholder="Search text…"
            defaultValue={filters.q ?? ""}
            onBlur={(e) => setFilter("q", e.target.value || undefined)}
            onKeyDown={(e) => e.key === "Enter" && setFilter("q", e.currentTarget.value || undefined)}
          />
          <Select
            aria-label="Sort"
            value={`${filters.sort_by}:${filters.sort_dir}`}
            onChange={(e) => {
              const [by, dir] = e.target.value.split(":");
              setFilters((current) => ({
                ...current,
                sort_by: by as LeadFilters["sort_by"],
                sort_dir: dir as LeadFilters["sort_dir"],
                page: 1,
              }));
            }}
          >
            <option value="score:desc">Score ↓</option>
            <option value="score:asc">Score ↑</option>
            <option value="posted_at:desc">Newest post</option>
            <option value="posted_at:asc">Oldest post</option>
            <option value="created_at:desc">Recently collected</option>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0 sm:p-2">
          {isLoading && (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          )}
          {isError && (
            <div className="py-10 text-center">
              <p className="mb-3 text-sm text-muted-foreground">Failed to load leads.</p>
              <Button onClick={() => refetch()}>Retry</Button>
            </div>
          )}
          {data && <LeadsTable leads={data.items} onSelect={setSelectedLead} />}
        </CardContent>
      </Card>

      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Page {data.page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={data.page <= 1}
              onClick={() => setFilter("page", data.page - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={data.page >= totalPages}
              onClick={() => setFilter("page", data.page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      <LeadDrawer lead={selectedLead} onClose={() => setSelectedLead(null)} />
    </div>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64" />}>
      <LeadsPageInner />
    </Suspense>
  );
}
