"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { AdminSettings, Source, User } from "@/lib/types";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b py-2.5 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{children}</span>
    </div>
  );
}

export default function SettingsPage() {
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api.get<User>("/auth/me") });
  const { data: settings, isLoading } = useQuery({
    queryKey: ["admin-settings"],
    queryFn: () => api.get<AdminSettings>("/admin/settings"),
  });
  const { data: sources } = useQuery({
    queryKey: ["sources"],
    queryFn: () => api.get<Source[]>("/sources"),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground">Account and effective runtime configuration.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Account</CardTitle>
        </CardHeader>
        <CardContent>
          <Row label="Email">{me?.email ?? "…"}</Row>
          <Row label="Name">{me?.full_name ?? "—"}</Row>
          <Row label="Role">{me?.is_admin ? "Admin" : "Member"}</Row>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Runtime</CardTitle>
          <CardDescription>
            Values come from environment variables — change them in .env and restart.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && <Skeleton className="h-32" />}
          {settings && (
            <>
              <Row label="LLM provider">
                <span className="flex items-center gap-2">
                  {settings.llm_provider}
                  <Badge variant={settings.llm_available ? "secondary" : "destructive"}>
                    {settings.llm_available ? "active" : "falling back to rules"}
                  </Badge>
                </span>
              </Row>
              <Row label="Classifier model">
                <code className="text-xs">{settings.llm_model}</code>
              </Row>
              <Row label="Search backend">{settings.search_backend}</Row>
              <Row label="Background jobs">
                {settings.celery_enabled ? "Celery (Redis)" : "in-process fallback"}
              </Row>
              <Row label="Environment">{settings.environment}</Row>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Data sources</CardTitle>
          <CardDescription>
            Sources missing keys are skipped at run time. Add keys under Integrations or in .env.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {sources?.map((source) => (
            <div key={source.key} className="flex items-center justify-between rounded-md border p-3 text-sm">
              <div>
                <div className="font-medium">{source.name}</div>
                <div className="text-xs text-muted-foreground">{source.description}</div>
              </div>
              <Badge
                variant={
                  !source.implemented
                    ? "outline"
                    : source.enabled && source.available
                      ? "secondary"
                      : "destructive"
                }
              >
                {!source.implemented
                  ? "not supported"
                  : !source.enabled
                    ? "disabled"
                    : source.available
                      ? "ready"
                      : `needs ${source.missing_keys.join(", ")}`}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
