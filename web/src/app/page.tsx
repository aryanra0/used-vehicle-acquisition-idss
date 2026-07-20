import Link from "next/link";
import {
  ArrowRight,
  Car,
  TrendingUp,
  Clock,
  Scale,
  Gauge,
  ShieldCheck,
  SlidersHorizontal,
  Calculator,
  CircleCheck,
  Database,
  BadgeCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

const primaryBtn =
  "inline-flex items-center gap-2 rounded-full bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-lift transition hover:bg-brand-700";
const secondaryBtn =
  "inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-800 ring-1 ring-slate-200 transition hover:bg-slate-50 hover:ring-slate-300";

export default function Landing() {
  return (
    <div className="landing-bg min-h-screen">
      <Nav />
      <main>
        <Hero />
        <Stats />
        <HowItWorks />
        <Models />
        <DecisionLogic />
        <Trust />
        <CtaBanner />
      </main>
      <SiteFooter />
    </div>
  );
}

/* Navigation */
function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/70 nav-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <BrandMark />
          <span className="text-sm font-semibold tracking-tight text-slate-900">
            Used Vehicle <span className="text-gradient">IDSS</span>
          </span>
        </Link>
        <div className="hidden items-center gap-7 text-sm text-slate-600 md:flex">
          <a href="#how" className="transition hover:text-slate-900">
            How it works
          </a>
          <a href="#models" className="transition hover:text-slate-900">
            Models
          </a>
          <a href="#decision" className="transition hover:text-slate-900">
            Decision logic
          </a>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-xs font-medium text-slate-400 sm:block">
            MSCI 436 · Group 16
          </span>
          <Link
            href="/app"
            className="inline-flex items-center gap-1.5 rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-lift transition hover:bg-brand-700"
          >
            Launch the tool <ArrowRight size={15} />
          </Link>
        </div>
      </nav>
    </header>
  );
}

function BrandMark() {
  return (
    <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-sky-500 text-white shadow-lift">
      <Car size={18} />
    </span>
  );
}

/* Hero */
function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[560px] hero-mesh" aria-hidden />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[560px] hero-grid" aria-hidden />
      <div className="relative mx-auto max-w-6xl px-4 pb-16 pt-16 sm:px-6 sm:pt-20 lg:pb-24">
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white/70 px-3 py-1 text-xs font-semibold text-brand-700 backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
              MSCI 436 · Decision Support Systems
            </span>
            <h1 className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
              Should you buy this car,{" "}
              <span className="text-gradient">and what&apos;s the most you should pay?</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-600">
              An intelligent decision support system for used-car buyers. Enter a vehicle and three
              models estimate its resale value, how quickly it will sell, and whether it clears your
              margin, turning auction data into a clear Buy or Pass with a recommended ceiling
              price.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/app" className={primaryBtn}>
                Launch the tool <ArrowRight size={16} />
              </Link>
              <a href="#how" className={secondaryBtn}>
                See how it works
              </a>
            </div>
            <div className="mt-6 flex items-center gap-2 text-sm text-slate-500">
              <ShieldCheck size={16} className="text-brand-500" />
              Anchored to the Manheim Market Report (MMR)
            </div>
          </div>
          <VerdictPreview />
        </div>
      </div>
    </section>
  );
}

function VerdictPreview() {
  return (
    <div className="card card-gradient accent-top relative p-6 shadow-lift">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            Recommendation
          </div>
          <div className="text-lg font-semibold text-slate-900">2015 Kia Sorento</div>
          <div className="text-xs text-slate-500">SUV · 25,000 mi · good condition</div>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-buy-soft px-3 py-1 text-sm font-bold text-buy ring-1 ring-inset ring-buy-ring">
          <BadgeCheck size={15} /> Buy
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Metric label="Max purchase price" value="$14,200" strong />
        <Metric label="Est. resale value" value="$16,050" />
        <Metric label="Days to sell" value="~52 · Fast" />
        <Metric label="Expected ROI" value="+18.4%" tone="buy" />
      </div>
      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
          <span>Confidence</span>
          <span className="font-semibold text-slate-700">82% · High</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-500 to-sky-500"
            style={{ width: "82%" }}
          />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 text-[11px] text-slate-400">
        <ShieldCheck size={13} /> Anchored to MMR $15,900 · illustrative preview
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
  strong,
}: {
  label: string;
  value: string;
  tone?: "buy";
  strong?: boolean;
}) {
  return (
    <div className="rounded-xl border border-slate-100 bg-white/70 px-3 py-2.5">
      <div className="text-[11px] font-medium text-slate-400">{label}</div>
      <div
        className={cn(
          "tnum mt-0.5 font-semibold",
          strong ? "text-lg" : "text-base",
          tone === "buy" ? "text-buy" : "text-slate-900"
        )}
      >
        {value}
      </div>
    </div>
  );
}

/* Stats strip */
function Stats() {
  const items = [
    { value: "558K", label: "auction records", sub: "US wholesale sales, 1990-2015" },
    { value: "3", label: "models in concert", sub: "resale · days-to-sell · buy/pass" },
    { value: "0.966", label: "resale R²", sub: "MAE ≈ $956 on held-out data" },
    { value: "MMR", label: "market anchor", sub: "Manheim Market Report benchmark" },
  ];
  return (
    <section className="mx-auto max-w-6xl px-4 pb-6 sm:px-6">
      <div className="grid grid-cols-2 gap-6 rounded-2xl border border-slate-200 bg-white/70 p-6 shadow-card backdrop-blur sm:grid-cols-4">
        {items.map((it) => (
          <div key={it.label} className="text-center sm:text-left">
            <div className="tnum text-3xl font-bold tracking-tight text-slate-900">{it.value}</div>
            <div className="mt-1 text-sm font-medium text-slate-700">{it.label}</div>
            <div className="text-xs text-slate-400">{it.sub}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* Section header */
function SectionHead({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <div className="text-xs font-semibold uppercase tracking-widest text-brand-600">
        {eyebrow}
      </div>
      <h2 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">{title}</h2>
      {children && <p className="mt-4 text-lg leading-relaxed text-slate-600">{children}</p>}
    </div>
  );
}

/* How it works */
function HowItWorks() {
  const steps = [
    {
      n: 1,
      icon: Car,
      title: "Describe the vehicle",
      body: "Year, make, model, mileage, condition, and the listing price you're weighing. No listing price? It's valued at a typical wholesale acquisition.",
    },
    {
      n: 2,
      icon: Database,
      title: "Three models score it",
      body: "Resale value, a days-to-sell band, and the probability it clears your margin, each grounded in real auction data and the MMR benchmark.",
    },
    {
      n: 3,
      icon: Scale,
      title: "Get a Buy or Pass",
      body: "A face-value verdict, a recommended maximum price, and a per-prediction confidence breakdown you can defend.",
    },
  ];
  return (
    <section id="how" className="mx-auto max-w-6xl scroll-mt-24 px-4 py-20 sm:px-6">
      <SectionHead eyebrow="How it works" title="From a listing to a decision in one screen">
        You stay in control at every step. This is decision support, not autopilot.
      </SectionHead>
      <div className="mt-14 grid gap-6 md:grid-cols-3">
        {steps.map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.n} className="card relative overflow-hidden p-6">
              <span className="pointer-events-none absolute -right-2 -top-4 text-7xl font-bold text-slate-100 select-none">
                {s.n}
              </span>
              <span className="relative grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-inset ring-brand-100">
                <Icon size={20} />
              </span>
              <h3 className="relative mt-4 text-lg font-semibold text-slate-900">{s.title}</h3>
              <p className="relative mt-2 text-sm leading-relaxed text-slate-600">{s.body}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/* Models */
function Models() {
  const models = [
    {
      id: "M1",
      icon: TrendingUp,
      title: "Resale value",
      task: "Regression",
      body: "Predicts the wholesale price the car will resell for, using its MMR benchmark as the single strongest signal.",
      chips: ["MAE ≈ $956", "R² 0.966", "MAPE 11.4%"],
    },
    {
      id: "M2",
      icon: Clock,
      title: "Days to sell",
      task: "Classification",
      body: "Bands the expected time on the lot into Fast, Moderate, Slow, or Very slow, using the make-level Edmunds benchmark.",
      chips: ["4 bands", "Edmunds Days-To-Turn"],
    },
    {
      id: "M3",
      icon: Scale,
      title: "Buy / Pass",
      task: "Calibrated classification",
      body: "Estimates the probability the vehicle clears your target margin when bought near wholesale. It drives the verdict.",
      chips: ["F1 0.89", "ROC-AUC 0.84", "calibrated"],
    },
  ];
  return (
    <section id="models" className="scroll-mt-24 bg-white/50 py-20">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHead eyebrow="The models" title="Three models, one recommendation">
          Each answers a different question, and together they turn a single vehicle into an
          actionable call.
        </SectionHead>
        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {models.map((m) => {
            const Icon = m.icon;
            return (
              <div key={m.id} className="card flex flex-col p-6">
                <div className="flex items-center justify-between">
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-inset ring-brand-100">
                    <Icon size={20} />
                  </span>
                  <span className="rounded-full bg-slate-900 px-2.5 py-1 text-xs font-bold tracking-wide text-white">
                    {m.id}
                  </span>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-slate-900">{m.title}</h3>
                <div className="text-xs font-medium uppercase tracking-wide text-brand-600">
                  {m.task}
                </div>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{m.body}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {m.chips.map((c) => (
                    <span
                      key={c}
                      className="tnum rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* Decision logic */
function DecisionLogic() {
  const rules = [
    "Expected ROI ≥ target margin (default 15%)",
    "Expected gross profit ≥ minimum (default $1,000)",
    "Confidence ≥ risk tolerance (default 0.60)",
  ];
  const formula = `Max price =
  Predicted resale
  − Repairs
  − (Holding cost/day × Days to sell)
  − (Target margin × Predicted resale)`;
  return (
    <section id="decision" className="mx-auto max-w-6xl scroll-mt-24 px-4 py-20 sm:px-6">
      <div className="grid items-start gap-10 lg:grid-cols-2">
        <div>
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-inset ring-brand-100">
            <SlidersHorizontal size={20} />
          </span>
          <h2 className="mt-5 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            The controls change the decision, not just the view
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-slate-600">
            Every threshold is yours to move. Tighten the target margin, raise the minimum profit,
            or demand more confidence, and the recommendation updates instantly. That interactivity
            is the point. The same car can be a Buy for one buyer and a Pass for another.
          </p>
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white/70 p-5 shadow-card">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Recommend Buy only when all hold
            </div>
            <ul className="mt-3 space-y-2.5">
              {rules.map((r) => (
                <li key={r} className="flex items-start gap-2.5 text-sm text-slate-700">
                  <CircleCheck size={18} className="mt-0.5 shrink-0 text-buy" />
                  <span className="tnum">{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="rounded-2xl bg-slate-900 p-6 shadow-lift">
          <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-400">
            <Calculator size={14} /> Recommended maximum price
          </div>
          <pre className="tnum overflow-x-auto font-mono text-[13px] leading-relaxed text-slate-100">
            {formula}
          </pre>
          <div className="mt-5 border-t border-slate-800 pt-4">
            <p className="text-sm leading-relaxed text-slate-300">
              A ceiling, not a target. When the listing price sits below this line, you pay the
              listing; the max price is your walk-away point in the negotiation.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* Trust */
function Trust() {
  const items = [
    {
      icon: Gauge,
      title: "Confidence on every call",
      body: "Each prediction carries its own reliability score, level, and basis, so you know when to trust the number and when to dig deeper.",
    },
    {
      icon: ShieldCheck,
      title: "Anchored to the market",
      body: "Low-confidence resale estimates are pulled toward the MMR benchmark, so rare or exotic vehicles stay grounded instead of guessed.",
    },
    {
      icon: BadgeCheck,
      title: "Honest advisory flags",
      body: "Salvage-range prices, implausible ROI, and valuation divergence are surfaced up front as warnings, without overriding the verdict.",
    },
  ];
  return (
    <section className="bg-white/50 py-20">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHead eyebrow="Built to be trusted" title="Numbers you can put your name on">
          A recommendation is only useful if you can defend it in the room.
        </SectionHead>
        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {items.map((it) => {
            const Icon = it.icon;
            return (
              <div key={it.title} className="card p-6">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-inset ring-brand-100">
                  <Icon size={20} />
                </span>
                <h3 className="mt-4 text-lg font-semibold text-slate-900">{it.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{it.body}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* CTA banner */
function CtaBanner() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <div className="relative overflow-hidden rounded-3xl bg-slate-900 px-8 py-14 text-center shadow-lift">
        <div
          className="pointer-events-none absolute inset-0"
          aria-hidden
          style={{
            background:
              "radial-gradient(600px 300px at 20% 0%, rgba(99,102,241,0.35) 0%, transparent 60%), radial-gradient(600px 300px at 85% 100%, rgba(14,165,233,0.30) 0%, transparent 60%)",
          }}
        />
        <div className="relative">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Try it on a real vehicle
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-slate-300">
            Adjust the inputs, move the thresholds, and watch the Buy/Pass call and ceiling price
            respond in real time.
          </p>
          <div className="mt-8 flex justify-center">
            <Link
              href="/app"
              className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-100"
            >
              Launch the tool <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/* Footer */
function SiteFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white/60">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="flex flex-col gap-8 sm:flex-row sm:justify-between">
          <div className="max-w-md">
            <div className="flex items-center gap-2.5">
              <BrandMark />
              <span className="text-sm font-semibold tracking-tight text-slate-900">
                Used Vehicle <span className="text-gradient">IDSS</span>
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-slate-500">
              Decision support only. Estimates value at the wholesale level from 2014-2015 auction
              data. A human buyer makes the final call.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-10 text-sm">
            <div>
              <div className="font-semibold text-slate-700">Built with</div>
              <ul className="mt-3 space-y-1.5 text-slate-500">
                <li>Python · scikit-learn</li>
                <li>FastAPI</li>
                <li>Next.js · React</li>
                <li>Tailwind CSS</li>
              </ul>
            </div>
            <div>
              <div className="font-semibold text-slate-700">Project</div>
              <ul className="mt-3 space-y-1.5 text-slate-500">
                <li>MSCI 436</li>
                <li>Decision Support Systems</li>
                <li>Group 16</li>
                <li>
                  <Link href="/app" className="text-brand-600 transition hover:text-brand-700">
                    Launch the tool
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div className="mt-10 border-t border-slate-100 pt-6 text-xs text-slate-400">
          MSCI 436 course project · Group 16 · For academic demonstration.
        </div>
      </div>
    </footer>
  );
}
