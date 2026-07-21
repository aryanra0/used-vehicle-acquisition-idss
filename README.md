# Used Vehicle Acquisition IDSS

A decision support tool for used-car dealers. You describe a vehicle, and it
estimates the resale value, how long the car will take to sell, and whether the
deal clears your margin. The output is a Buy or Pass call with a recommended
maximum purchase price and a confidence score for each prediction.

Course project for MSCI 436 (Decision Support Systems), Group 16.

## What it does

- Predicts wholesale resale value (M1), a days-to-sell band (M2), and buy/pass
  profitability (M3).
- Anchors every vehicle to its MMR (Manheim Market Report) wholesale benchmark.
- Turns ROI, gross profit, and confidence into a face-value Buy or Pass call.
- Scores the confidence of each prediction and raises advisory warnings when the
  inputs or outputs look off (abnormally low price, implausible ROI, valuation
  divergence). Warnings do not override the verdict.
- Recommends a maximum purchase price to use as a negotiation ceiling.

## Quickstart

You need Python 3.9+ and Node 18+. The app has two parts: a Python API and a
Next.js web UI. Run the steps below from the repository root.

### 1. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. (Optional) Retrain the models

Pre-trained models are already committed under `models/` (~5 MB), so you can
skip straight to step 3 and the app works out of the box. Retrain only if you
want to reproduce them from scratch: this reads `data/raw/car_prices.csv`,
writes the train/val/test splits to `data/processed/`, and overwrites the
models in `models/`. It takes a few minutes on the full dataset; add
`--sample 40000` for a quick run while developing.

```bash
cd src
PYTHONPATH=. python3 -m idss.train
```

### 3. Start the API

From the `src/` directory, on port 8000:

```bash
PYTHONPATH=. python3 -m uvicorn idss.api.main:app --port 8000
```

Check it is up at http://localhost:8000/health.

### 4. Start the web app

In a second terminal:

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000. The landing page links to the tool at `/app`. Fill
in a make, model, year, and mileage to get a recommendation.

## Architecture

- Backend: Python and scikit-learn (HistGradientBoosting), served with FastAPI
  (`src/idss`).
- Frontend: Next.js and React dashboard (`web/`).
- Models: M1 resale (regression), M2 days-to-sell band (classification), M3
  buy/pass (calibrated classification), plus an MMR lookup and a days-to-turn
  benchmark.

## The three models

| ID | Model | Task | Target |
|----|-------|------|--------|
| M1 | Resale price | Regression | Wholesale sold price ($) |
| M2 | Days-to-sell band | Classification | Fast <=60 / Moderate 61-90 / Slow 91-120 / Very slow >120 |
| M3 | Profitability (buy/pass) | Calibrated classification | P(clears target margin if bought ~20% below MMR) |

MMR is used both as a model feature (the strongest single predictor of sale
price) and as a make/model/year lookup at serve time.

### Metrics on the held-out test set

- M1: MAE ~$956, MAPE 11.4%, R2 0.966. Beats the "just quote MMR" baseline
  (MAE ~$1,091).
- M2: accuracy ~1.0. The band is essentially a deterministic function of the
  make benchmark, so this number is not a measure of skill; see the
  unseen-make generalization check in the training summary.
- M3: F1 0.89, ROC-AUC 0.84, AUC-PR 0.94. The "always Buy" baseline already
  scores F1 0.87 (positive rate 0.77), so AUC and AUC-PR are the real skill
  indicators.

## Data

The models train on `car_prices.csv` — ~558k US wholesale/auction records, each
with a real MMR (Manheim Market Report) benchmark and a condition grade. It is a
single, coherent wholesale source, so the resale target and the MMR benchmark
are directly comparable. Days-to-sell comes from a make-level days-to-turn
benchmark (`2016-10-dtt.xls`).

A market snapshot is bundled under `data/raw/` so the repo runs end to end
offline out of the box. To value vehicles against current market prices instead,
enable live pricing (see "Live current-market pricing" below).

See `data/README.md` for the data dictionary.

## Decision logic

The defaults below are user-adjustable. Recommend Buy only when all three hold,
otherwise Pass:

1. Expected ROI >= target margin (default 15%)
2. Expected gross profit >= minimum (default $1,000)
3. Confidence >= risk tolerance (default 0.60)

```
MaxPurchasePrice = PredictedResale - Repairs - (HoldingCostPerDay x PredictedDaysToSell) - (TargetMargin x PredictedResale)
```

When no listing price is supplied, the vehicle is evaluated at a wholesale
acquisition price (default 20% below MMR). The max purchase price is a ceiling,
not a target: when a listing price is below it, you pay the listing, not the
ceiling.

### Confidence and data-quality flags

- Each prediction (resale, market value, days-to-sell, buy/pass) carries its own
  reliability score, level, and basis.
- Buy/pass confidence is the weaker of the profit-model probability and the
  resale-estimate reliability.
- A low-confidence resale estimate is reconciled toward MMR (a confidence-weighted
  blend, not a hard cap), so rare vehicles are anchored to the benchmark instead
  of trusted blindly.
- Advisory flags (abnormally low price, implausible ROI, resale-vs-MMR
  divergence, zero mileage) are shown prominently but do not change the Buy/Pass
  verdict.

## Repository structure

```
.
├── README.md
├── requirements.txt
├── data/
│   ├── README.md              # data dictionary and provenance
│   ├── raw/                   # car_prices.csv (primary), 2016-10-dtt.xls (committed)
│   └── processed/             # train/val/test splits (regenerated by training)
├── docs/PRD.md                # product requirements document
├── src/idss/
│   ├── data/                  # dataset loading, MMR lookup, DTT benchmark, live pricing
│   ├── features/              # feature engineering (shared train/serve)
│   ├── models/                # M1 resale, M2 dts band, M3 buy/pass, registry
│   ├── decision/              # buy/pass and max-price rules
│   ├── service/               # evaluation orchestration and confidence scoring
│   └── api/                   # FastAPI app
├── web/                       # Next.js dashboard
└── models/                    # trained artifacts (committed, ~5 MB)
```

## Live current-market pricing (optional)

Out of the box the app values vehicles from the bundled market snapshot. To
price against live market values instead — recommended for recent model years —
set a `MARKETCHECK_API_KEY` (see `.env.example`) and the app uses a live market
value as the resale anchor. The provider is pluggable in
`src/idss/data/live_pricing.py`.

## Tests

```bash
PYTHONPATH=src python3 -m pytest
```

The trained models are committed, so the full suite runs out of the box. (Tests
that need models are skipped automatically only if `models/` is empty, e.g. if
you have cleared it.)

## Disclaimer

Decision support only. Estimates are at the wholesale level and, unless live
pricing is enabled, reflect the bundled market snapshot rather than live market
conditions. A human buyer makes the final call.
