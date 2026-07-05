export type IntentLabel = "BUY" | "SELL" | "MENTION" | "SPAM";
export type IntentTarget = "BUYERS" | "SELLERS" | "BOTH";
export type LeadStatus = "NEW" | "SAVED" | "CONTACTED" | "REJECTED";
export type JobStatus = "PENDING" | "RUNNING" | "SUCCESS" | "FAILED";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Campaign {
  id: number;
  name: string;
  product_keyword: string;
  intent_target: IntentTarget;
  location: string | null;
  date_from: string | null;
  date_to: string | null;
  min_confidence: number;
  sources: string[];
  created_at: string;
  updated_at: string;
  lead_count?: number;
  last_job_status?: JobStatus | null;
  last_job_at?: string | null;
}

export interface Classification {
  intent: IntentLabel;
  confidence: number;
  reasons: string[];
  extracted: Record<string, unknown>;
  model: string;
  rule_signals: Record<string, string[]>;
}

export interface Lead {
  id: number;
  campaign_id: number;
  source_key: string;
  external_id: string;
  url: string | null;
  author: string | null;
  title: string | null;
  content: string;
  posted_at: string | null;
  product: string | null;
  price_value: number | null;
  price_currency: string | null;
  location: string | null;
  event_date: string | null;
  status: LeadStatus;
  score: number;
  created_at: string;
  classification: Classification | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Job {
  id: number;
  campaign_id: number;
  status: JobStatus;
  started_at: string | null;
  finished_at: string | null;
  stats: Record<string, Record<string, unknown>>;
  error: string | null;
  created_at: string;
}

export interface RunCampaignResponse {
  job: Job;
  execution: "celery" | "inline";
}

export interface Source {
  key: string;
  name: string;
  description: string;
  enabled: boolean;
  available: boolean;
  missing_keys: string[];
  required_keys: string[];
  implemented: boolean;
}

export interface Integration {
  id: number;
  provider: string;
  key_name: string;
  masked_value: string;
  created_at: string;
  updated_at: string;
}

export interface AdminSettings {
  llm_provider: string;
  llm_available: boolean;
  llm_model: string;
  search_backend: string;
  celery_enabled: boolean;
  sources_enabled: string[];
  environment: string;
}

export interface DashboardStats {
  total_leads: number;
  by_intent: Record<string, number>;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  campaigns: number;
  avg_score: number;
  recent_leads: Lead[];
  leads_last_14_days: { date: string; count: number }[];
}

export interface LeadFilters {
  campaign_id?: number;
  intent?: IntentLabel;
  status?: LeadStatus;
  min_score?: number;
  source?: string;
  location?: string;
  product?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: "score" | "posted_at" | "created_at" | "status";
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}
