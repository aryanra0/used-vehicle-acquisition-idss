"use client";

import { Card, Field, Select, Slider, TextInput, SectionLabel } from "@/components/ui/primitives";
import { Assumptions, Options, VehicleInput } from "@/lib/api";
import { percent } from "@/lib/utils";

export function InputRail({
  options,
  vehicle,
  setVehicle,
  assumptions,
  setAssumptions,
  predictedDays,
}: {
  options: Options | null;
  vehicle: VehicleInput;
  setVehicle: (v: VehicleInput) => void;
  assumptions: Assumptions;
  setAssumptions: (a: Assumptions) => void;
  // The model's predicted days-to-sell, shown as the holding-period placeholder.
  predictedDays?: number | null;
}) {
  const upV = (patch: Partial<VehicleInput>) => setVehicle({ ...vehicle, ...patch });
  const upA = (patch: Partial<Assumptions>) => setAssumptions({ ...assumptions, ...patch });
  const models = options?.models_by_make[vehicle.make] ?? [];

  return (
    <div className="space-y-4">
      <Card>
        <SectionLabel>Vehicle</SectionLabel>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Make">
            <Select
              options={options?.makes ?? []}
              placeholder="Select make"
              value={vehicle.make}
              onChange={(e) => upV({ make: e.target.value, model: "" })}
            />
          </Field>
          <Field label="Model">
            <Select
              options={models}
              placeholder={vehicle.make ? "Select model" : "Pick make first"}
              value={vehicle.model}
              onChange={(e) => upV({ model: e.target.value })}
            />
          </Field>
          <Field label="Year">
            <TextInput
              type="number"
              min={options?.year_min ?? 1990}
              max={options?.year_max ?? 2016}
              placeholder="e.g. 2015"
              value={vehicle.year ?? ""}
              onChange={(e) =>
                upV({ year: e.target.value === "" ? undefined : Number(e.target.value) })
              }
            />
          </Field>
          <Field label="Mileage">
            <TextInput
              type="number"
              min={0}
              placeholder="e.g. 45000"
              value={vehicle.odometer ?? ""}
              onChange={(e) =>
                upV({ odometer: e.target.value === "" ? undefined : Number(e.target.value) })
              }
            />
          </Field>
          <Field label="Body">
            <Select
              options={options?.bodies ?? []}
              placeholder="Any"
              value={vehicle.body}
              onChange={(e) => upV({ body: e.target.value })}
            />
          </Field>
          <Field label="Transmission">
            <Select
              options={options?.transmissions ?? []}
              placeholder="Any"
              value={vehicle.transmission}
              onChange={(e) => upV({ transmission: e.target.value })}
            />
          </Field>
          <Field label="State">
            <Select
              options={options?.states ?? []}
              placeholder="Any"
              value={vehicle.state}
              onChange={(e) => upV({ state: e.target.value })}
            />
          </Field>
          <Field label="Color">
            <Select
              options={options?.colors ?? []}
              placeholder="Any"
              value={vehicle.color}
              onChange={(e) => upV({ color: e.target.value })}
            />
          </Field>
        </div>
        <div className="mt-3">
          <Field
            label="Listing / asking price"
            hint="Leave blank to evaluate at a wholesale acquisition price"
          >
            <TextInput
              type="number"
              min={0}
              placeholder="e.g. 15000"
              value={vehicle.listing_price ?? ""}
              onChange={(e) =>
                upV({
                  listing_price: e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </Field>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2">
          <Slider
            label="Condition score"
            value={vehicle.condition}
            min={1}
            max={100}
            step={1}
            onChange={(v) => upV({ condition: v })}
            format={(v) => `${v} / 100`}
          />
        </div>
      </Card>

      <Card>
        <SectionLabel>Assumptions</SectionLabel>
        <div className="space-y-4">
          <Slider
            label="Target profit margin"
            value={assumptions.target_profit_margin}
            min={0}
            max={1}
            step={0.01}
            onChange={(v) => upA({ target_profit_margin: v })}
            format={(v) => percent(v, 0)}
          />
          <div>
            <Slider
              label="Acquisition discount (wholesale)"
              value={assumptions.acquisition_discount}
              min={0}
              max={1}
              step={0.01}
              onChange={(v) => upA({ acquisition_discount: v })}
              format={(v) => percent(v, 0)}
            />
            <p className="mt-1 text-[11px] text-slate-400">
              {vehicle.listing_price != null
                ? "Ignored while a listing price is set; clear it to evaluate at a wholesale discount."
                : "Applied below market value (MMR) since no listing price is set."}
            </p>
          </div>
          <Slider
            label="Risk tolerance (min confidence)"
            value={assumptions.risk_tolerance}
            min={0}
            max={1}
            step={0.01}
            onChange={(v) => upA({ risk_tolerance: v })}
            format={(v) => percent(v, 0)}
          />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Holding cost / day ($)">
              <TextInput
                type="number"
                min={0}
                value={assumptions.holding_cost_per_day}
                onChange={(e) => upA({ holding_cost_per_day: Number(e.target.value) })}
              />
            </Field>
            <Field
              label="Holding period (days)"
              hint={
                predictedDays != null
                  ? `Blank = model estimate (~${Math.round(predictedDays)} days)`
                  : "Blank = use model estimate"
              }
            >
              <TextInput
                type="number"
                min={0}
                placeholder={
                  predictedDays != null ? String(Math.round(predictedDays)) : "model estimate"
                }
                value={assumptions.holding_period_days ?? ""}
                onChange={(e) =>
                  upA({
                    holding_period_days:
                      e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </Field>
            <Field
              label="Min dollar profit ($)"
              hint="A deal must clear at least this gross profit to be a Buy"
            >
              <TextInput
                type="number"
                min={0}
                value={assumptions.min_dollar_profit}
                onChange={(e) => upA({ min_dollar_profit: Number(e.target.value) })}
              />
            </Field>
            <Field label="Estimated repairs ($)">
              <TextInput
                type="number"
                min={0}
                value={assumptions.repair_estimate}
                onChange={(e) => upA({ repair_estimate: Number(e.target.value) })}
              />
            </Field>
          </div>
        </div>
      </Card>
    </div>
  );
}
