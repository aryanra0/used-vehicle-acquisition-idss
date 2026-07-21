"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";
import {
  Assumptions,
  DEFAULT_ASSUMPTIONS,
  EvaluationResult,
  Metadata,
  Options,
  VehicleInput,
  evaluate,
  fetchMetadata,
  fetchOptions,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { InputRail } from "@/components/InputRail";
import { VerdictCard } from "@/components/VerdictCard";
import { PriceComparison } from "@/components/PriceComparison";
import {
  FinancialSummary,
  PredictionConfidenceCard,
  RiskSummary,
  TopFactors,
} from "@/components/Summaries";
import { DataQualityFlag } from "@/lib/api";

// A blank starting point: every field is unset ("Any" / empty) so the tool
// opens clear and the user builds up a vehicle from scratch.
const BLANK_VEHICLE: VehicleInput = {
  make: "",
  model: "",
  year: undefined,
  odometer: undefined,
  condition: 50, // 0-100 UI scale; a slider can't be empty, so start neutral
  body: "",
  transmission: "",
  state: "",
  color: "",
  listing_price: null,
};

export default function Home() {
  const [options, setOptions] = useState<Options | null>(null);
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [vehicle, setVehicle] = useState<VehicleInput>(BLANK_VEHICLE);
  const [assumptions, setAssumptions] = useState<Assumptions>(DEFAULT_ASSUMPTIONS);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetchOptions().then(setOptions).catch(() => setError("Could not reach the API. Is it running on :8000?"));
    fetchMetadata().then(setMeta).catch(() => {});
  }, []);

  const run = useCallback(async (v: VehicleInput, a: Assumptions) => {
    // Only evaluate once the essentials are filled in, so a blank form stays clear.
    if (!v.make || !v.model || !Number.isFinite(v.year) || !Number.isFinite(v.odometer)) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await evaluate(v, a));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounced live recompute whenever inputs change.
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => run(vehicle, assumptions), 350);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [vehicle, assumptions, run]);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <Header loading={loading} />

      {error && (
        <div className="mb-4 rounded-lg border border-pass-ring bg-pass-soft px-4 py-2 text-sm text-pass">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
          <InputRail
            options={options}
            vehicle={vehicle}
            setVehicle={setVehicle}
            assumptions={assumptions}
            setAssumptions={setAssumptions}
            predictedDays={result?.risk_summary.days_to_sell_benchmark ?? null}
          />
          <div className="space-y-6">
            {result ? (
              <>
                {result.coverage_warning && (
                  <div className="flex items-start gap-2 rounded-xl border border-caution-ring bg-caution-soft px-4 py-3 text-sm text-caution">
                    <span className="mt-0.5 font-bold">!</span>
                    <span>{result.coverage_warning}</span>
                  </div>
                )}
                {result.data_quality_flags?.map((f, i) => (
                  <FlagBanner key={i} flag={f} />
                ))}
                <VerdictCard r={result} />
                <PriceComparison r={result} listingPrice={vehicle.listing_price ?? null} />
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <FinancialSummary r={result} />
                  <RiskSummary r={result} />
                </div>
                <PredictionConfidenceCard r={result} />
                <TopFactors r={result} />
              </>
            ) : (
              <div className="card flex h-64 items-center justify-center px-6 text-center text-slate-400">
                {loading
                  ? "Evaluating…"
                  : "Fill in the vehicle details (make, model, year, mileage) to see a recommendation"}
              </div>
            )}
          </div>
        </div>

      <footer className="mt-10 space-y-1 text-center text-xs text-slate-400">
        <p>
          Decision support only. Estimates are wholesale-level and, unless live pricing is
          enabled, reflect a bundled market snapshot rather than live market conditions. A
          human buyer makes the final call.
        </p>
        {meta && (
          <p>
            {meta.live_pricing_enabled
              ? "Live market pricing enabled"
              : "Model estimates (no live feed)"}
            {meta.trained_at
              ? ` · models trained ${new Date(meta.trained_at).toLocaleDateString()}`
              : ""}
          </p>
        )}
      </footer>
    </main>
  );
}

function Header({ loading }: { loading: boolean }) {
  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <Link
          href="/"
          className="mb-1 inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 transition hover:text-brand-600"
        >
          <ArrowLeft size={13} /> Overview
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">
          <span className="text-gradient">Used Vehicle IDSS</span>
        </h1>
        <p className="text-sm text-slate-500">
          Should you buy this car, and what&apos;s the most you should pay?
        </p>
      </div>
      {loading && <Loader2 className="animate-spin text-brand-500" size={18} />}
    </header>
  );
}

function FlagBanner({ flag }: { flag: DataQualityFlag }) {
  const styles: Record<DataQualityFlag["severity"], string> = {
    alert: "border-pass-ring bg-pass-soft text-pass",
    warn: "border-caution-ring bg-caution-soft text-caution",
    info: "border-slate-200 bg-slate-50 text-slate-600",
  };
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-xl border px-4 py-3 text-sm",
        styles[flag.severity] ?? styles.info
      )}
    >
      <span className="mt-0.5 font-bold">{flag.severity === "alert" ? "⚠" : "!"}</span>
      <span>{flag.message}</span>
    </div>
  );
}

