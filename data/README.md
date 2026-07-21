# Data

Provenance and dictionary for the datasets used by the IDSS. The raw data files
are committed to the repo (under `raw/`) so it runs end to end after a clone;
this document records what they are and where they came from.

## Training source (single source)

The models train on one real source, `raw/car_prices.csv`, loaded and cleaned by
`src/idss/data/dataset.py`. We use a single coherent source rather than blending
several (see "Why one source" below).

### `raw/car_prices.csv`: wholesale/auction, with condition and MMR
- ~558,000 real US wholesale/auction records; model years ~1990-2015, from a
  public vehicle wholesale-auction dataset.
- Columns include: year, make, model, trim, body, transmission, vin, state,
  condition, odometer, color, interior, seller, mmr, sellingprice (the resale
  target), saledate.
- Provides real sold prices, the only condition signal, and a real MMR (Manheim
  Market Report) wholesale benchmark.

### Days-to-sell benchmark: `raw/2016-10-dtt.xls`
- A make/segment "days to turn" benchmark: monthly average days-to-sell by
  manufacturer/make/segment (Oct 2015 to Oct 2016).
- Joined by make to derive the M2 days-to-sell band (Fast <=60, Moderate 61-90,
  Slow 91-120, Very slow >120; calibrated to the observed ~40-105 day spread,
  median ~71).
- Caveat: aggregate (not per-car) and a different period, so it is treated as an
  approximate benchmark.

## Cleaned schema (after `dataset.load_car_prices()`)
`price (sellingprice), mmr, year, mileage, condition, make, model, body,
transmission, state, color`

Cleaning: parse numeric strings; drop rows missing price/mmr/year/mileage/make/model;
apply sanity bounds (price $500-$250k, mileage 1-400k, year 1990-2015); sanitize the
`transmission` column (only `automatic`/`manual` are valid, other values are
contaminated and set to unknown); de-duplicate.

## Train / validation / test splits
`dataset.train_val_test_split()` produces a random, seeded split written to
`data/processed/` (gitignored):
- test (~20%): held out for final metrics.
- val (~15% of the remainder): used to tune the M3 decision threshold.
- train: everything else.

## Market value (MMR)
`car_prices` ships a real `mmr` column, so the IDSS uses the real MMR, not a proxy,
in two ways:
1. As a model feature (`market_value`) for M1/M2/M3. MMR is an external market
   benchmark published before the sale, not derived from this row's sale price, so
   it is a legitimate (non-leaking) feature and the strongest single predictor of
   resale.
2. As a make/model/year median lookup (`src/idss/data/mmr_lookup.py`) for
   user-entered vehicles that do not supply an MMR, with progressive fallback
   (make/model/year, then make/model, then make, then global) and sample-size
   tracking for a reliability score.

## Why one source (not a blend)
An earlier version blended three sources (`true_car_listings.csv`, `car_prices.csv`,
`used_cars.csv`) with a `source_channel` flag. That was dropped because:
- Inconsistent naming across sources caused MMR/model lookups to miss and fall back
  to a near-useless make-level median (for example, "median of all Toyotas").
- Mixed price levels (retail asking vs. wholesale sold) made "resale" an ambiguous
  number that sat above the wholesale MMR benchmark it was compared against.
- Only `car_prices` has real MMR and condition, the two signals the whole decision
  rests on.

Using `car_prices` alone gives consistent naming, a real MMR benchmark, condition
grades, and one price basis (wholesale) that is directly comparable to MMR.

## Data source
`raw/car_prices.csv` and `raw/2016-10-dtt.xls` are committed under `data/raw/`, so
no separate download is needed. They are a public vehicle wholesale-auction
dataset and a make-level days-to-turn benchmark, respectively — a bundled market
snapshot so the repo runs offline. To replace them, place files with the same
names and schema under `data/raw/`.

## Rejected sources
- `car_sales_data.csv` and duplicates: synthetic, with randomly paired make/model
  ("Nissan F-150") and no real signal.
- `car-price-prediction` and the Georgian `train.csv`/`test.csv`: different schema
  (Levy, Airbags), not used.
- Moroccan used-cars dataset: wrong market and currency.
- `car_sales_demographics.csv`: buyer demographics only, not useful for pricing.

## Future
- Live current-market prices via the MarketCheck or Auto.dev API, the only path to
  truly current pricing (see `.env.example`).
- A per-car listing/entry date would enable a real per-vehicle days-to-sell model.
