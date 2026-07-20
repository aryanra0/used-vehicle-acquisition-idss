"use client";

import { Card, SectionLabel } from "@/components/ui/primitives";
import { EvaluationResult, PredictionConfidence } from "@/lib/api";
import { ConfidenceBadge } from "@/components/Summaries";
import { currency } from "@/lib/utils";

export function PriceComparison({
  r,
  listingPrice,
}: {
  r: EvaluationResult;
  listingPrice: number | null;
}) {
  const rows = [
    {
      label: "Predicted resale",
      value: r.predicted_resale_price,
      color: "#4f46e5",
      conf: r.resale_confidence,
    },
    {
      label: "Market value (MMR)",
      value: r.market_value_mmr ?? 0,
      color: "#0ea5e9",
      conf: r.market_value_confidence,
    },
    { label: "Max purchase price (ceiling)", value: r.max_purchase_price, color: "#16a34a", conf: null },
    listingPrice
      ? { label: "Listing price", value: listingPrice, color: "#d97706", conf: null }
      : null,
  ].filter(Boolean) as {
    label: string;
    value: number;
    color: string;
    conf: PredictionConfidence | null;
  }[];

  const max = Math.max(...rows.map((x) => x.value), 1);

  return (
    <Card>
      <SectionLabel>Price comparison</SectionLabel>
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="mb-1 flex items-center justify-between gap-2 text-xs">
              <span className="flex items-center gap-2 text-slate-600">
                {row.label}
                {row.conf && <ConfidenceBadge c={row.conf} />}
              </span>
              <span className="font-mono font-semibold text-slate-800">
                {currency(row.value)}
              </span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${(row.value / max) * 100}%`,
                  background: `linear-gradient(90deg, ${row.color}cc, ${row.color})`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
      {r.price_guidance && (
        <div className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-snug text-slate-600">
          {r.price_guidance}
        </div>
      )}
    </Card>
  );
}
