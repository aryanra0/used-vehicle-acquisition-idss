# Product Requirements Document
## IDSS for Used Vehicle Acquisition

| Field | Value |
|---|---|
| Document status | v7 (single-source `car_prices`, real MMR as a model feature, FastAPI + Next.js) |
| Course / Team | MSCI 436, Group 16 |
| Product type | Intelligent Decision Support System (IDSS) |
| Last updated | 2026-07-20 |

---

## 1. Overview

### 1.1 Problem Statement
Used-car dealerships evaluate hundreds of listings each day across Craigslist, Facebook Marketplace, auctions, and dealer exchanges. Buy/pass decisions rely heavily on individual employee experience, incomplete market information, and manual price comparisons. This leads to:

- Overpaying for inventory, which compresses margins.
- Slow inventory turnover and capital tied up in aging stock.
- Inconsistent decisions between buyers on comparable vehicles.
- No systematic estimate of downstream risk (time-to-sell, demand).

Dealerships need a system that combines historical sales data and market benchmarks to recommend whether to buy a vehicle and the maximum price worth paying, with a transparent and adjustable financial rationale.

### 1.2 Product Vision
Build an IDSS that helps used-car dealerships make faster, more consistent, data-driven acquisition decisions by predicting resale value, expected time-to-sell, and expected profitability, while letting users adjust business assumptions and immediately see the effect on the recommendation.

### 1.3 Decision the System Supports
The IDSS augments the human buyer; it does not replace them. For a candidate vehicle it answers one primary question, Buy or Pass, supported by a recommended maximum purchase price and a quantified expectation of profit, time-to-sell, and risk. User-defined constraints (target profit margin, holding cost, risk tolerance, holding period) shift recommendations along a spectrum from aggressive (higher inventory, lower margin) to conservative (fewer, higher-margin deals). The buyer retains final authority.

### 1.4 Prediction Task Summary
| Aspect | Definition |
|---|---|
| Task type | Regression (resale price) plus classification (days-to-sell band and buy/pass). |
| Entity | A used vehicle's specifications (make, model, year, condition, mileage, and more). |
| Outcomes | Buy/pass decision plus expected profit, recommended max purchase price, and repair-cost estimate. |
| Resale label | Actual sold price from historical sales data (real transactions, not asking prices). |
| Days-to-sell label | Benchmark-level: average days-to-sell by make/segment (industry data), not per-car. |

### 1.5 Definitions
| Term | Definition |
|---|---|
| Resale price | Predicted price the dealer can sell the vehicle for after reconditioning. |
| Days-to-sell (DTS) | Predicted band of days from acquisition to sale: Fast (<=60), Moderate (61-90), Slow (91-120), Very slow (>120). |
| MMR | Manheim Market Report value, a wholesale market-value benchmark included per vehicle in the primary dataset. |
| Holding cost | Daily cost of keeping a vehicle in inventory (floor-plan interest, lot, insurance). |
| Max purchase price | Highest acquisition price that still meets the user's target margin given predicted resale, repairs, and holding cost. |
| Gross profit | Resale price minus purchase price, estimated repairs, and total holding cost. |
| ROI / ROIC | Gross profit divided by total invested capital (purchase plus repairs). |
| Confidence score | Per-prediction reliability (0-1) with a level and a plain-language basis. The Buy/Pass confidence is the weaker of the profit-model probability and the resale-estimate reliability. |
| Data-quality flag | An advisory warning (abnormally low price, implausible ROI, valuation divergence, zero mileage) shown alongside a recommendation without changing the face-value Buy/Pass verdict. |

---

## 2. Goals and Non-Goals

### 2.1 Business Goals
- Increase average gross profit per vehicle acquired.
- Reduce losses from overpaying for inventory.
- Improve inventory turnover (reduce average days-to-sell).
- Maximize return on invested capital (ROIC).
- Reduce manual appraisal time per vehicle.
- Improve decision consistency across buyers.

### 2.2 User Goals
Enable a buyer to quickly answer:
- Should I buy this vehicle?
- What is the maximum price I should pay?
- How much profit should I expect?
- How risky is this purchase?
- Roughly how long will it stay in inventory?

### 2.3 Non-Goals (for this version)
- Not an inventory-management or CRM system.
- Not a financing or lending recommendation engine.
- Does not execute purchases or negotiate automatically.
- Does not perform photo-based damage assessment or VIN scanning (see Future Enhancements).

---

## 3. Target Users

### 3.1 Primary
- Vehicle acquisition managers and dealership buyers.
- Inventory managers at used-vehicle dealerships.
- Independent used-car dealers.

### 3.2 Secondary
- Small automotive wholesalers.
- Fleet purchasing teams.
- Auction buyers.

### 3.3 Primary Persona
Maria, an acquisition manager at an independent dealership. She evaluates 40-80 listings a day, often on mobile at auctions with limited time. She needs a fast, defensible buy/pass call and a price ceiling she can negotiate against. She distrusts black-box outputs and wants to see the numbers behind a recommendation.

---

## 4. User Stories

Each story is written as: As a [user], I want [capability], so that [outcome].

- US-1 (Evaluation): As a buyer, I want to enter vehicle information and immediately see whether purchasing is profitable, so I can make a fast decision.
- US-2 (Pricing): As a buyer, I want a recommended maximum purchase price, so I know my negotiation ceiling without eroding profit.
- US-3 (Scenario planning): As an inventory manager, I want to change target margin, holding cost, and risk tolerance, so I can compare conservative vs. aggressive strategies.
- US-4 (Transparency): As a buyer, I want to see the main factors behind a recommendation and how listing, max, and resale prices compare, so I can trust and defend the decision.

---

## 5. Functional Requirements (Summary)

At a high level the system shall:

- Accept single-vehicle manual entry, with per-evaluation assumptions (holding cost, repair estimate).
- Predict resale price, a days-to-sell band, and profitability; output a Buy/Pass recommendation with a calibrated confidence score.
- Compute a recommended maximum purchase price and full financials (gross profit, ROI, holding cost).
- Let users adjust target margin, holding cost, risk tolerance, and holding period, and recompute instantly.
- Display Vehicle Summary, Price Comparison, Financial Summary, and Risk Summary, plus the top contributing factors.

---

## 6. Machine Learning Models

### 6.1 Model Summary
| ID | Model | Task | Target | Primary metric(s) |
|---|---|---|---|---|
| M1 | Resale Price Prediction | Regression | Actual sold price ($) | MAE, MAPE, RMSLE, R2 |
| M2 | Days-to-Sell Band | Multi-class classification | Sale-time band in days: Fast <=60, Moderate 61-90, Slow 91-120, Very slow >120 | Accuracy, F1, ROC-AUC |
| M3 | Profitability / Buy-Pass | Binary classification | P(clears target margin if bought at a wholesale discount below market value), mapped to Buy/Pass | F1, ROC-AUC, AUC-PR, calibration (with trivial-baseline F1) |

### 6.2 Modeling Approach
- Baselines first: linear regression (M1), majority-class and logistic regression (M2, M3) to set a floor.
- Primary models: gradient-boosted trees using scikit-learn `HistGradientBoosting` (regressor for M1, classifier for M2/M3). These are strong performers for tabular used-car price prediction and add no heavy dependencies. XGBoost and LightGBM are drop-in alternatives; Random Forest is a strong, interpretable option that performed best in the referenced sale-time study.
- Single-source training: all models train on one real dataset, `car_prices.csv` (~558k wholesale/auction records with real MMR and condition; see Section 7). An earlier version blended three sources with a `source_channel` flag. It was dropped because inconsistent naming caused benchmark lookups to miss and mixed retail/wholesale price levels made "resale" ambiguous relative to the wholesale MMR. Model year is a feature, so era is represented.
- Real MMR as a feature: the real Manheim MMR is used as the `market_value` feature. It is an external benchmark published before the sale (not derived from the sale price, so no leakage) and the strongest single predictor of resale.
- Price target handling (M1): apply a log transform to the right-skewed price and invert on output; evaluate error on the original dollar scale.
- Preprocessing (see Section 7.3): load and clean the source (parse numeric strings, sanity-bound price/mileage/year, sanitize the contaminated `transmission` column, de-duplicate), ordinal-encode categoricals for the tree models, log-transform the price target, and engineer a small set of features (vehicle age, mileage-per-year) alongside the raw fields and the real MMR.
- Modular design: separate price (M1), time-to-sell (M2), and decision logic (M3) for interpretability. M3 consumes M1 output plus features and business rules.
- M3 label (wholesale acquisition): dealerships buy below market value and resell. M3's label is whether a car, if bought at a typical wholesale discount below its market value (MMR, default 20%), would still resell for enough to clear the target margin. This reflects the real acquisition decision and is learnable from features. An earlier framing ("resells above its own MMR") was close to noise because MMR already predicts the sale price. M3's probabilities are calibrated and its decision threshold is tuned on a validation set to maximize F1 rather than fixed at 0.5.

### 6.3 Features
All features are available at prediction time and knowable before acquisition (no target leakage). Only fields the UI collects are used, so every input the user changes moves the prediction.

- Raw: year, make, model, body, transmission, state, color, mileage, condition.
- Real MMR: `market_value`, the vehicle's real Manheim MMR benchmark (an external, pre-sale value, not the sale price, so no leakage). The strongest single feature.
- Engineered: vehicle age (reference year 2016 minus model year) and mileage-per-year.
- Days-to-sell join: average days-to-sell by make from the days-to-turn benchmark, used to derive the M2 band label.
- Adjustable parameters (user, not learned): target profit margin, acquisition discount, risk tolerance, holding cost, holding period, repair estimate.
- The sale `price` is the only leakage-excluded column. `condition` may be missing and is left NaN (the tree models handle it natively).

### 6.4 Evaluation and Targets
- Split the source into train / validation / test (random, seeded). The test set is held out for final metrics; the validation set tunes the M3 decision threshold.
- M1 evaluated with MAE, MAPE, RMSLE, R2; M2 with accuracy and macro-F1; M3 with F1 (at the tuned threshold), ROC-AUC, AUC-PR, and calibration (Brier score). Per-state error is tracked for fairness.
- M1 baseline: quoting MMR as the resale price. M1 must beat that MAE by using condition, mileage, and other fields. Current results: MAE ~$956, MAPE ~11.4%, R2 ~0.966 vs. an MMR-baseline MAE ~$1,091.
- Reporting for M3: the profitable class is the majority (~77%), so a naive "always Buy" classifier already scores a high F1 (~0.87). M3's F1 is therefore reported alongside that baseline F1 and the threshold-independent AUC/AUC-PR, so a high F1 is not mistaken for real skill. Current results: F1 ~0.89, ROC-AUC ~0.84, AUC-PR ~0.94 (baseline F1 ~0.87).
- All models must beat their baseline by a documented margin before release.

### 6.5 Retraining and Learning Loop
- Retrain on a rolling window when new labeled sales accumulate, or sooner on significant market shifts.
- The system acts as a lightweight feedback loop: realized sale outcomes and dealer feedback on recommendations feed future training.

### 6.6 Error Costs and Fairness
- Asymmetric error cost: overestimating a vehicle's value is worse than underestimating it. Overestimation risks buying cars that will not sell for profit (capital loss); underestimation is a missed opportunity. Model selection and decision thresholds reflect this asymmetry.
- Regional fairness: the model should avoid systematically over- or under-valuing vehicles from particular regions; per-state error is evaluated and monitored.

### 6.7 Assumptions and Known Limitations
- Wholesale price basis: the source is wholesale/auction data, so "resale" is a wholesale value (a conservative proxy for a dealer's true retail margin), directly comparable to the wholesale MMR benchmark.
- Coverage of rare vehicles: exotics and low-volume models have few comparable rows, so their resale estimates are lower-confidence. Such estimates are reconciled toward MMR and flagged with low confidence.
- Recency: the source is ~1990-2015 (mostly 2014-2015), so predictions reflect that market. The out-of-coverage warning triggers beyond model year 2015; truly current prices require a live feed (see Section 12).
- Days-to-sell is available only as a make/segment benchmark average, not a per-car duration. The day-scale bands (<=60 / 61-90 / 91-120 / >120) are calibrated to the observed benchmark distribution (~40-105 days, median ~71).

### 6.8 Decision Logic (Buy/Pass and Max Purchase Price)
These are the default rules; users can adjust the parameters.

Buy/Pass rule. For the vehicle at the price under consideration, compute expected gross profit and ROI, then recommend Buy only if all three hold, otherwise Pass:
1. Expected ROI >= target profit margin (default 15%).
2. Expected gross profit >= minimum dollar profit (default $1,000).
3. Model confidence >= the user's risk-tolerance threshold (default 0.60).

Maximum purchase price. Worked backward from predicted resale value:

```
MaxPurchasePrice = PredictedResalePrice - EstimatedRepairs - TotalHoldingCost - RequiredProfit
  TotalHoldingCost = HoldingCostPerDay x PredictedDaysToSell
  RequiredProfit   = TargetProfitMargin x PredictedResalePrice   (default 15%)
```

Worked example. Predicted resale $12,000; repairs $800; holding cost $20/day x 45 days = $900; target margin 15%, so required profit $1,800.
MaxPurchasePrice = 12,000 - 800 - 900 - 1,800 = $8,500. Recommend Buy only if the vehicle can be acquired at or below $8,500.

The ROI and dollar-profit thresholds are cost-sensitive by design (Section 6.6); the defaults lean conservative to avoid overpaying.

Default purchase scenario. When the user does not supply a listing price, the system evaluates the vehicle at a typical wholesale acquisition price, a discount below market value (MMR), default 20%, reflecting that dealers buy below market. When a listing price is supplied, that price is used directly.

The max purchase price is a ceiling (a walk-away and negotiation limit), not a target. When a listing price is below it, the buyer pays the listing (or negotiates lower), never the ceiling; the UI states this explicitly.

### 6.9 Confidence and Data-Quality Guards
- Per-prediction confidence. Each output (resale, market value, days-to-sell, and buy/pass) carries its own reliability score (0-1), a level (High/Medium/Low/Very low), and a plain-language basis. Resale reliability reflects how well the vehicle matched comparable data and how far the model diverges from MMR; the buy/pass confidence is the weaker of the profit-model probability and the resale reliability, and it feeds the risk-tolerance gate.
- Reconciliation toward MMR. When the resale estimate is low-confidence (rare vehicle or large divergence), it is blended toward the MMR benchmark in proportion to confidence, a confidence-weighted blend rather than a hard cap. High-confidence vehicles keep any legitimate premium over MMR.
- Advisory data-quality flags, not verdict overrides. The Buy/Pass call is made on face-value economics. Separately, the system flags inputs and outputs that do not add up (an abnormally low price, an implausible ROI, a resale-vs-MMR divergence, or zero mileage) as prominent warnings that prompt the buyer to verify, without changing the recommendation.

---

## 7. Data Source

All models train on a single real dataset, `car_prices.csv`, cleaned by
`src/idss/data/dataset.py`. Using one coherent source (rather than an earlier
three-source blend) keeps model naming consistent, provides a real MMR benchmark,
and keeps the price basis uniformly wholesale so resale and MMR are comparable.

### 7.1 Primary source: `car_prices.csv` (wholesale/auction)
- ~558,000 real US wholesale/auction records; model years ~1990-2015, from a public vehicle wholesale-auction dataset.
- Fields: year, make, model, trim, body, transmission, vin, state, condition, odometer, color, interior, seller, mmr, sellingprice (the resale target), saledate.
- Provides real sold prices, the only condition signal, and a real MMR benchmark used both as a feature and as a make/model/year lookup.
- Cleaning: parse numeric strings; sanity-bound price/mileage/year; sanitize the contaminated `transmission` column; de-duplicate.

### 7.2 Days-to-Sell Benchmark: make/segment "Days To Turn" (`2016-10-dtt.xls`)
- Monthly average days-to-sell by manufacturer/make/segment; used to derive the M2 band. Aggregate, not per-car.

### 7.3 Preprocessing Pipeline (run before modeling)
1. Load and clean `car_prices.csv`: parse `$`/comma prices and mileage to numbers; sanity-bound price ($500-$250k), mileage (1-400k), and year (1990-2015); sanitize the contaminated `transmission` column (keep only `automatic`/`manual`); de-duplicate.
2. Split into train / validation / test (random, seeded); persist to `data/processed/`.
3. Encoding: ordinal encoding of categoricals for the tree models.
4. Target transform: log-transform the resale-price target for M1; invert on output.
5. Feature engineering: vehicle age and mileage-per-year, alongside the raw fields and the real MMR (`market_value`).

Model artifacts and their metrics/metadata are versioned in a simple registry.

### 7.4 Rejected Sources
- `car_sales_data.csv` and other synthetic files: randomized make/model (e.g., "Nissan F-150"), price uncorrelated with year/mileage, no usable signal; excluded.
- Moroccan used-cars dataset: wrong market and currency; excluded.
- `car_sales_demographics.csv`: buyer demographics only; not useful for pricing.

### 7.5 Future Sources
- MarketCheck / Auto.dev API for live current-market prices; the only path to truly current pricing (see Section 6.7 recency limitation and Section 12).

---

## 8. System Workflow

1. User enters vehicle information plus assumptions (holding cost, repair estimate).
2. System looks up the market-value benchmark (the vehicle's MMR, either user-provided, from a live feed if configured, or a make/model/year median from the training data) and the make days-to-sell benchmark.
3. Features are engineered from inputs plus the MMR benchmark.
4. Models produce resale value (M1), days-to-sell band (M2), and profitability (M3) in real time; a low-confidence resale is reconciled toward MMR.
5. Business rules compute maximum purchase price, ROI, and the face-value Buy/Pass under the user's constraints; per-prediction confidence and any data-quality flags are attached.
6. The FastAPI backend returns the result; the Next.js dashboard updates instantly and the user can adjust assumptions and re-evaluate.
7. After sale, realized outcomes feed monitoring and the retraining/feedback loop.

---

## 9. Non-Functional Requirements
| Category | Requirement |
|---|---|
| Performance | Single-vehicle prediction latency < 5 s (p95); assumption changes recompute in < 1 s (p95) using cached predictions. |
| Availability | Available during dealership business hours; document target uptime. |
| Reliability | Scheduled retraining on a rolling window; automated monitoring for model drift and data-quality anomalies, with alerting. |
| Transparency | Every recommendation exposes its key contributing factors, the price comparison, and the assumptions used. |
| Fairness | Per-state prediction error monitored to prevent systematic regional over/under-valuation. |
| Security/Privacy | Secure storage of any API keys and user data; no secrets in source control. |
| Usability | Core evaluation flow completable on a laptop or tablet without training. |

---

## 10. Success Metrics

### 10.1 Model Metrics
- M1: MAE, MAPE, RMSLE, R2 on sold price; per-state error for fairness.
- M2: accuracy, macro-F1, ROC-AUC on the sale-time band.
- M3: F1 (at the tuned threshold) reported with the trivial "always Buy" F1 baseline, plus ROC-AUC, AUC-PR, and calibration on buy/pass. AUC and AUC-PR are the primary skill indicators since F1 is inflated by class balance.
- All models must beat their baseline by a documented margin before release.

### 10.2 Business Metrics
- Average gross profit per car acquired.
- Inventory turnover rate.
- Percentage of purchased vehicles sold within the target 30-60 day window.
- Return on invested capital (ROIC).
- Reduction in losses from overpaying for vehicles.
- Increase in successful purchases meeting target profit margins.
- Dealer adoption rate and evaluations per user.

### 10.3 Evaluation Method
Offline: back-test on held-out data; evaluate decisions on realized sale price and overall profit. Online (future): compare predictions against actual outcomes after sale; significant degradation triggers retraining and a data-drift investigation. Dealer feedback is collected to improve models and user trust.

---

## 11. Risks and Mitigations

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R-1 | Days-to-sell is only a make/segment benchmark, not per-car. | Coarse time-to-sell and holding-cost estimates. | Present as a band with a benchmark caveat; let users override holding period; seek per-car listing dates as future work. |
| R-2 | Primary data is 2014-2015, not current. | Predictions reflect an older market. | Frame as training/demo data; add live data (MarketCheck) for a production version; retrain when newer data is available. |
| R-3 | Limited repair-cost information. | Distorted profit estimates. | User-editable repair input; document default assumptions; sensitivity display. |
| R-4 | Regional markets diverge; possible regional bias. | Poor local accuracy or unfair valuations. | State features plus per-state evaluation and monitoring. |
| R-5 | Data-quality issues (missing values, inconsistent casing, outliers). | Degraded model accuracy. | Documented cleaning pipeline; outlier filters; imputation. |
| R-6 | Users over-trust the model. | Bad decisions on low-confidence cases. | Show confidence, factors, and price comparison; position as decision support. |
| R-7 | Asymmetric cost: overestimation. | Buying cars that will not sell for profit; capital loss. | Cost-sensitive thresholds favoring caution (Section 6.6). |

---

## 12. Future Enhancements
- Acquire per-car listing/entry dates to train a true per-vehicle days-to-sell model (survival analysis or probability-of-sale-within-N-days).
- Integrate the MarketCheck API for live comparables and current market pricing.
- Bulk CSV upload for screening a batch of listings and ranked recommendations.
- Multi-vehicle side-by-side comparison and ranking.
- Repair-cost estimation via computer vision from vehicle photos.
- VIN decoding for automatic feature extraction.
- Demand and segmentation analysis using a retail buyer-demographics dataset.
- Negotiation assistant suggesting an opening offer.
- Expanded explainable-AI views of recommendation drivers.

---

## 13. MVP Scope

### 13.1 In Scope
- Manual single-vehicle entry, with holding-cost and repair assumptions.
- Real-time predictions: resale price (M1), days-to-sell band (M2), profitability (M3).
- Buy/Pass recommendation with calibrated confidence and top factors.
- Recommended maximum purchase price.
- Adjustable target margin, holding cost/period, and risk tolerance.
- Dashboard: Vehicle Summary card, Price Comparison view, Financial Summary, Risk Summary.

### 13.2 Out of Scope
- Dealer login/accounts and role management.
- Bulk CSV upload and multi-vehicle comparison (see Future Enhancements).
- Inventory management and CRM integration.
- Financing recommendations.
- Vehicle photo analysis and automatic VIN scanning.
- Live market data integration.

### 13.3 MVP Acceptance
The MVP is accepted when: (a) a user can evaluate a single vehicle end to end; (b) M1, M2, and M3 beat their baselines by the documented margin on the held-out data; (c) recommendations, max price, and financials update within the latency targets; (d) each recommendation displays confidence, key factors, and the price comparison; and (e) per-state error is reported for M1.

---

## 14. Open Questions
- Confirm the default Buy/Pass thresholds (15% ROI, $1,000 minimum profit, 0.60 confidence) match the dealership's real acquisition strategy.
- Sale-time bands are set to Fast (<=60 days), Moderate (61-90), Slow (91-120), Very slow (>120), derived from the observed benchmark distribution (median ~71 days) and standard dealer overage practice; confirm these thresholds with the dealership. A simpler 3-band split (Fast / Moderate / Slow >90) is available if preferred.
- How is the repair-cost estimate produced in the MVP: user-entered only, or partly modeled?
- What default holding-cost assumptions ship as defaults, and who sets them?
- What accuracy margin over baseline defines "success" for each model?
- What is the acceptable per-state error gap before it is flagged as unfair?

---

## 15. Appendix

### 15.1 Expert Consultation
Keith Fernandez, Data Engineer, Amazon Demand Forecasting (co-op mentor). Helped reframe the problem from a pure prediction task into a decision-support system focused on inventory, risk, and timing constraints. Key guidance: the value of forecasting comes from how predictions drive operational decisions, which shaped the buy/pass framework and the modular design separating price, time-to-sell, and decision logic.

### 15.2 Key Reference
Ahaggach, H., Abrouk, L., Foufou, S., & Lebon, E. (2022). Predicting Car Sale Time with Data Analytics and Machine Learning. Product Lifecycle Management (PLM in Transition Times), pp. 399-409. DOI: 10.1007/978-3-031-25182-5_39. Basis for framing days-to-sell as a classification into sale-time bands and for the finding that tree-based models (Random Forest) perform well on used-vehicle sale-time prediction.
