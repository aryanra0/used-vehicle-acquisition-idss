"use client";

import { Check, X, TrendingUp, Radio, Database } from "lucide-react";
import { EvaluationResult } from "@/lib/api";
import { Badge } from "@/components/ui/primitives";
import { cn, currency, percent } from "@/lib/utils";

export function VerdictCard({ r }: { r: EvaluationResult }) {
  const buy = r.recommendation === "Buy";
  const live = r.price_source === "live";
  return (
    <div
      className={cn(
        "accent-top card relative overflow-hidden p-6",
        buy ? "ring-1 ring-buy-ring" : "ring-1 ring-pass-ring"
      )}
      style={{
        background: buy
          ? "linear-gradient(180deg,#ffffff 0%,#f0fdf4 100%)"
          : "linear-gradient(180deg,#ffffff 0%,#fef2f2 100%)",
      }}
    >
      <div className="mb-4 flex items-center gap-2">
        <Badge tone={live ? "buy" : "slate"}>
          {live ? <Radio size={11} /> : <Database size={11} />}
          {live ? "Live market price" : "Model estimate"}
        </Badge>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div
            className={cn(
              "flex h-14 w-14 items-center justify-center rounded-2xl text-white shadow-lift",
              buy ? "bg-buy" : "bg-pass"
            )}
          >
            {buy ? <Check size={28} strokeWidth={3} /> : <X size={28} strokeWidth={3} />}
          </div>
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Recommendation
            </div>
            <div
              className={cn(
                "text-3xl font-bold leading-tight",
                buy ? "text-buy" : "text-pass"
              )}
            >
              {r.recommendation}
            </div>
          </div>
        </div>

        <div className="text-right" title={r.buy_pass_confidence?.basis ?? undefined}>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Confidence
          </div>
          <div className="font-mono text-2xl font-bold text-slate-800">
            {percent(r.confidence, 0)}
          </div>
          {r.buy_pass_confidence && (
            <div className="text-[11px] font-medium text-slate-500">
              {r.buy_pass_confidence.level}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Metric label="Max purchase price" value={currency(r.max_purchase_price)} big />
        <Metric
          label="Predicted resale"
          value={currency(r.predicted_resale_price)}
          sub={
            r.predicted_resale_low != null && r.predicted_resale_high != null
              ? `80% range ${currency(r.predicted_resale_low)} to ${currency(r.predicted_resale_high)}`
              : undefined
          }
        />
        <Metric
          label="Expected profit"
          value={currency(r.expected_gross_profit)}
          tone={r.expected_gross_profit >= 0 ? "buy" : "pass"}
          icon={<TrendingUp size={14} />}
        />
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  big,
  tone,
  icon,
  sub,
}: {
  label: string;
  value: string;
  big?: boolean;
  tone?: "buy" | "pass";
  icon?: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200/70 bg-white/70 px-4 py-3">
      <div className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        {icon}
        {label}
      </div>
      <div
        className={cn(
          "mt-1 font-mono font-bold",
          big ? "text-2xl" : "text-xl",
          tone === "buy" && "text-buy",
          tone === "pass" && "text-pass",
          !tone && "text-slate-900"
        )}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 font-mono text-[11px] text-slate-400">{sub}</div>}
    </div>
  );
}
