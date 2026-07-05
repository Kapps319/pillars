"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { Integration } from "@/lib/types";

const PROVIDERS: Record<string, string[]> = {
  reddit: ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"],
  google: ["GOOGLE_API_KEY", "GOOGLE_CSE_ID"],
  anthropic: ["ANTHROPIC_API_KEY"],
  openai: ["OPENAI_API_KEY"],
  twitter: ["TWITTER_BEARER"],
};

const schema = z.object({
  provider: z.string().min(1),
  key_name: z.string().min(1).regex(/^[A-Z0-9_]+$/, "UPPER_SNAKE_CASE"),
  value: z.string().min(1, "Value is required"),
});
type FormValues = z.infer<typeof schema>;

export default function IntegrationsPage() {
  const queryClient = useQueryClient();
  const { data: integrations, isLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => api.get<Integration[]>("/integrations"),
  });

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { provider: "reddit", key_name: "REDDIT_CLIENT_ID" },
  });

  const provider = watch("provider");

  const saveMutation = useMutation({
    mutationFn: (values: FormValues) => api.post<Integration>("/integrations", values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      reset({ provider, key_name: PROVIDERS[provider]?.[0] ?? "", value: "" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/integrations/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["integrations"] }),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Integrations & API keys</h1>
        <p className="text-sm text-muted-foreground">
          Keys are encrypted at rest and shown masked. Environment variables take precedence at run
          time.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Add / update a key</CardTitle>
          <CardDescription>
            e.g. a Reddit script app (reddit.com/prefs/apps) or a Google Custom Search key.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit((values) => saveMutation.mutate(values))}
            className="grid gap-4 sm:grid-cols-3"
            noValidate
          >
            <div className="space-y-1.5">
              <Label htmlFor="provider">Provider</Label>
              <Select
                id="provider"
                {...register("provider")}
                onChange={(e) => {
                  setValue("provider", e.target.value);
                  setValue("key_name", PROVIDERS[e.target.value]?.[0] ?? "");
                }}
              >
                {Object.keys(PROVIDERS).map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="key_name">Key</Label>
              <Select id="key_name" {...register("key_name")}>
                {(PROVIDERS[provider] ?? []).map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
              </Select>
              {errors.key_name && <p className="text-xs text-destructive">{errors.key_name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="value">Value</Label>
              <Input id="value" type="password" placeholder="secret value" {...register("value")} />
              {errors.value && <p className="text-xs text-destructive">{errors.value.message}</p>}
            </div>
            <div className="sm:col-span-3">
              <Button type="submit" disabled={isSubmitting || saveMutation.isPending}>
                {saveMutation.isPending ? "Saving…" : "Save key"}
              </Button>
              {saveMutation.isError && (
                <span className="ml-3 text-sm text-destructive">
                  {(saveMutation.error as Error).message}
                </span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Stored keys</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
          {integrations?.length === 0 && (
            <p className="py-4 text-center text-sm text-muted-foreground">No keys stored yet.</p>
          )}
          {integrations?.map((integration) => (
            <div
              key={integration.id}
              className="flex items-center justify-between rounded-md border p-3 text-sm"
            >
              <div>
                <div className="font-medium">{integration.key_name}</div>
                <div className="text-xs text-muted-foreground">
                  {integration.provider} · <code>{integration.masked_value}</code>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Delete ${integration.key_name}`}
                onClick={() => deleteMutation.mutate(integration.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Where to get keys</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong className="text-foreground">Reddit</strong> — create a “script” app at
            reddit.com/prefs/apps (free).
          </p>
          <p>
            <strong className="text-foreground">Google</strong> — Custom Search JSON API key +
            Programmable Search Engine ID (100 free queries/day).
          </p>
          <p>
            <strong className="text-foreground">Anthropic / OpenAI</strong> — enables the LLM
            classifier stage (set LLM_PROVIDER accordingly).
          </p>
          <p>
            <strong className="text-foreground">X / Twitter</strong> — paid API; the adapter ships
            disabled by default.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
