"use client";

import { Clock, Gauge, TrendingUp } from "lucide-react";
import { Card, SectionLabel, Badge } from "@/components/ui/primitives";
import { ConfidenceLevel, EvaluationResult, PredictionConfidence } from "@/lib/api";
import { cn, currency, percent } from "@/lib/utils";

const CONF_TONE: Record<ConfidenceLevel, "buy" | "brand" | "caution" | "pass"> = {
  High: "buy",
  Medium: "brand",
  Low: "caution",
  "Very low": "pass",
};

export function ConfidenceBadge({ c }: { c?: PredictionConfidence | null }) {
  if (!c) return null;
  return (
    <Badge tone={CONF_TONE[c.level] ?? "slate"} title={c.basis}>
      {Math.round(c.score * 100)}% · {c.level}
    </Badge>
  );
}

export function PredictionConfidenceCard({ r }: { r: EvaluationResult }) {
  const rows: { label: string; c: PredictionConfidence | null }[] = [
    { label: "Resale price", c: r.resale_confidence },
    { label: "Market value (MMR)", c: r.market_value_confidence },
    { label: "Days-to-sell", c: r.days_band_confidence },
    { label: "Buy / Pass call", c: r.buy_pass_confidence },
  ];
  return (
    <Card>
      <SectionLabel>Prediction confidence</SectionLabel>
      <div className="space-y-2.5">
        {rows.map(({ label, c }) =>
          c ? (
            <div key={label}>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-slate-600">
                  <Gauge size={14} className="text-slate-400" />
                  {label}
                </span>
                <ConfidenceBadge c={c} />
              </div>
              <p className="mt-0.5 pl-6 text-[11px] leading-snug text-slate-400">{c.basis}</p>
            </div>
          ) : null
        )}
      </div>
    </Card>
  );
}

export function FinancialSummary({ r }: { r: EvaluationResult }) {
  const f = r.financial_summary;
  const rows = [
    ["Purchase price", currency(f.purchase_price)],
    ["Estimated repairs", currency(f.estimated_repairs)],
    ["Predicted resale", currency(f.predicted_resale_price)],
    ["Holding cost", currency(f.total_holding_cost)],
  ];
  return (
    <Card>
      <SectionLabel>Financial summary</SectionLabel>
      <dl className="space-y-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between text-sm">
            <dt className="text-slate-500">{k}</dt>
            <dd className="font-mono text-slate-800">{v}</dd>
          </div>
        ))}
        <div className="my-2 border-t border-dashed border-slate-200" />
        <div className="flex items-center justify-between">
          <dt className="text-sm font-semibold text-slate-700">Net profit</dt>
          <dd
            className={cn(
              "font-mono text-lg font-bold",
              f.net_profit >= 0 ? "text-buy" : "text-pass"
            )}
          >
            {currency(f.net_profit)}
          </dd>
        </div>
        <div className="flex items-center justify-between text-sm">
          <dt className="text-slate-500">Return on investment</dt>
          <dd className="font-mono font-semibold text-slate-800">{percent(f.roi)}</dd>
        </div>
      </dl>
    </Card>
  );
}

const RISK_TONE: Record<string, "buy" | "caution" | "pass"> = {
  Low: "buy",
  Medium: "caution",
  High: "pass",
};

export function RiskSummary({ r }: { r: EvaluationResult }) {
  const s = r.risk_summary;
  return (
    <Card>
      <SectionLabel>Risk & timing</SectionLabel>
      <div className="space-y-3">
        <Row icon={<Clock size={15} />} label="Days-to-sell band">
          <Badge tone="brand">{s.days_to_sell_band}</Badge>
          {s.days_to_sell_benchmark && (
            <span className="ml-2 font-mono text-xs text-slate-500">
              ~{Math.round(s.days_to_sell_benchmark)} days
            </span>
          )}
        </Row>
        <Row icon={<Gauge size={15} />} label="Overall risk">
          <Badge tone={RISK_TONE[s.risk_level] ?? "slate"}>{s.risk_level}</Badge>
        </Row>
        <Row icon={<TrendingUp size={15} />} label="Market demand">
          <span className="text-sm text-slate-700">{s.market_demand}</span>
        </Row>
      </div>
    </Card>
  );
}

function Row({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-sm text-slate-500">
        <span className="text-slate-400">{icon}</span>
        {label}
      </span>
      <span className="flex items-center">{children}</span>
    </div>
  );
}

export function TopFactors({ r }: { r: EvaluationResult }) {
  const hasImpact = r.top_factors.some((f) => f.impact);
  return (
    <Card>
      <SectionLabel>Key factors</SectionLabel>
      {hasImpact && (
        <p className="mb-2 text-[11px] text-slate-400">
          Impact = how much each feature moves the resale estimate versus a typical car.
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {r.top_factors.map((f) => {
          const positive = f.impact?.startsWith("+");
          return (
            <div
              key={f.factor}
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5"
            >
              <div className="text-[10px] uppercase tracking-wide text-slate-400">
                {f.factor}
              </div>
              <div className="text-sm font-semibold text-slate-800">{f.value}</div>
              {f.impact && (
                <div
                  className={cn(
                    "font-mono text-[11px] font-semibold",
                    positive ? "text-buy" : "text-pass"
                  )}
                >
                  {f.impact}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {r.notes.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-slate-500">
          {r.notes.map((n, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="text-slate-300">•</span>
              {n}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
