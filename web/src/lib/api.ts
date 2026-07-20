// Typed client for the IDSS FastAPI backend.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Options {
  makes: string[];
  models_by_make: Record<string, string[]>;
  bodies: string[];
  transmissions: string[];
  colors: string[];
  states: string[];
  year_min: number;
  year_max: number;
  condition_min: number;
  condition_max: number;
}

export interface Assumptions {
  target_profit_margin: number;
  min_dollar_profit: number;
  risk_tolerance: number;
  holding_cost_per_day: number;
  // null -> use the model's predicted days-to-sell; a number overrides it.
  holding_period_days: number | null;
  repair_estimate: number;
  acquisition_discount: number;
}

export interface VehicleInput {
  // year and odometer are optional so the form can start blank; the UI blocks
  // evaluation until they are filled (the API requires both).
  year?: number;
  make: string;
  model: string;
  odometer?: number;
  condition: number;
  body?: string;
  transmission?: string;
  trim?: string;
  color?: string;
  interior?: string;
  state?: string;
  mmr?: number | null;
  listing_price?: number | null;
}

export interface FinancialSummary {
  purchase_price: number;
  estimated_repairs: number;
  predicted_resale_price: number;
  total_holding_cost: number;
  net_profit: number;
  roi: number;
}

export interface RiskSummary {
  days_to_sell_band: string;
  days_to_sell_benchmark: number | null;
  market_demand: string;
  risk_level: string;
}

export type ConfidenceLevel = "High" | "Medium" | "Low" | "Very low";

export interface PredictionConfidence {
  score: number; // 0..1
  level: ConfidenceLevel;
  basis: string;
}

export interface DataQualityFlag {
  severity: "alert" | "warn" | "info";
  message: string;
}

export interface EvaluationResult {
  recommendation: "Buy" | "Pass";
  confidence: number;
  predicted_resale_price: number;
  predicted_resale_low: number | null;
  predicted_resale_high: number | null;
  days_to_sell_band: string;
  expected_gross_profit: number;
  roi: number;
  max_purchase_price: number;
  market_value_mmr: number | null;
  price_vs_mmr_delta: number | null;
  price_source: "live" | "model";
  coverage_warning: string | null;
  resale_confidence: PredictionConfidence | null;
  market_value_confidence: PredictionConfidence | null;
  days_band_confidence: PredictionConfidence | null;
  buy_pass_confidence: PredictionConfidence | null;
  data_quality_flags: DataQualityFlag[];
  price_guidance: string | null;
  financial_summary: FinancialSummary;
  risk_summary: RiskSummary;
  top_factors: { factor: string; value: string; impact?: string }[];
  notes: string[];
  prediction_id?: string;
}

export interface Metadata {
  defaults: Assumptions;
  trained_at: string | null;
  live_pricing_enabled: boolean;
  versions: Record<string, { saved_at: string | null; artifact: string | null }>;
}

export const DEFAULT_ASSUMPTIONS: Assumptions = {
  target_profit_margin: 0.15,
  min_dollar_profit: 1000,
  risk_tolerance: 0.6,
  holding_cost_per_day: 20,
  // Blank by default -> the model's predicted days-to-sell drives holding cost.
  holding_period_days: null,
  repair_estimate: 0,
  acquisition_discount: 0.2,
};

export async function fetchOptions(): Promise<Options> {
  const r = await fetch(`${API_BASE}/options`);
  if (!r.ok) throw new Error("Failed to load options");
  return r.json();
}

export async function fetchMetadata(): Promise<Metadata> {
  const r = await fetch(`${API_BASE}/metadata`);
  if (!r.ok) throw new Error("Failed to load metadata");
  return r.json();
}

// The UI presents condition on an intuitive 0-100 scale; the model was trained
// on a 1-49 grade. Convert at the network boundary so the API/model keep their
// native scale.
export function conditionToModelScale(display: number): number {
  const c = Math.round(1 + (display / 100) * 48);
  return Math.max(1, Math.min(49, c));
}

export async function evaluate(
  vehicle: VehicleInput,
  assumptions: Assumptions
): Promise<EvaluationResult> {
  const payload = {
    vehicle: { ...vehicle, condition: conditionToModelScale(vehicle.condition) },
    assumptions,
  };
  const r = await fetch(`${API_BASE}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Evaluation failed");
  return r.json();
}


