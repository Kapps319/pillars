"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { Campaign, Source } from "@/lib/types";
import { cn } from "@/lib/utils";

const schema = z.object({
  name: z.string().min(1, "Give the campaign a name").max(255),
  product_keyword: z.string().min(1, "What product are you hunting?").max(255),
  intent_target: z.enum(["BUYERS", "SELLERS", "BOTH"]),
  location: z.string().max(255).optional(),
  date_from: z.string().optional(),
  date_to: z.string().optional(),
  min_confidence: z.coerce.number().min(0).max(100),
});
type FormValues = z.infer<typeof schema>;

export default function NewCampaignPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [selectedSources, setSelectedSources] = useState<string[]>(["mock"]);

  const { data: sources } = useQuery({
    queryKey: ["sources"],
    queryFn: () => api.get<Source[]>("/sources"),
  });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { intent_target: "BOTH", min_confidence: 0 },
  });

  function toggleSource(key: string) {
    setSelectedSources((current) =>
      current.includes(key) ? current.filter((k) => k !== key) : [...current, key],
    );
  }

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      const campaign = await api.post<Campaign>("/campaigns", {
        ...values,
        location: values.location || null,
        date_from: values.date_from || null,
        date_to: values.date_to || null,
        sources: selectedSources,
      });
      router.push(`/campaigns/${campaign.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create campaign");
    }
  }

  const selectable = sources?.filter((s) => s.implemented) ?? [];

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">New campaign</h1>
        <p className="text-sm text-muted-foreground">
          Plug in any product or market — the classifier does the rest.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">What are you looking for?</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="name">Campaign name</Label>
              <Input id="name" placeholder="Abu Dhabi GP ticket radar" {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="product_keyword">Product keyword</Label>
              <Input
                id="product_keyword"
                placeholder="Abu Dhabi GP tickets"
                {...register("product_keyword")}
              />
              {errors.product_keyword && (
                <p className="text-xs text-destructive">{errors.product_keyword.message}</p>
              )}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="intent_target">Intent type</Label>
                <Select id="intent_target" {...register("intent_target")}>
                  <option value="BOTH">Buyers & sellers</option>
                  <option value="BUYERS">Buyers only</option>
                  <option value="SELLERS">Sellers only</option>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="location">Location (optional)</Label>
                <Input id="location" placeholder="Abu Dhabi" {...register("location")} />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="date_from">From (optional)</Label>
                <Input id="date_from" type="date" {...register("date_from")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="date_to">To (optional)</Label>
                <Input id="date_to" type="date" {...register("date_to")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="min_confidence">Min confidence (0–100)</Label>
                <Input id="min_confidence" type="number" min={0} max={100} {...register("min_confidence")} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sources</CardTitle>
            <CardDescription>
              Sources without API keys are skipped automatically at run time — add keys under
              Integrations to activate them.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            {selectable.map((source) => {
              const selected = selectedSources.includes(source.key);
              return (
                <button
                  type="button"
                  key={source.key}
                  onClick={() => toggleSource(source.key)}
                  className={cn(
                    "rounded-md border p-3 text-left text-sm transition-colors",
                    selected ? "border-primary bg-primary/5" : "hover:bg-accent",
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{source.name}</span>
                    {!source.available && (
                      <span className="text-[10px] uppercase text-muted-foreground">keys needed</span>
                    )}
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{source.description}</p>
                </button>
              );
            })}
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex gap-2">
          <Button type="submit" disabled={isSubmitting || selectedSources.length === 0}>
            {isSubmitting ? "Creating…" : "Create campaign"}
          </Button>
          <Button type="button" variant="ghost" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
