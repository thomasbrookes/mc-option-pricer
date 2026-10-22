# Assumptions

Every input the model uses, where it comes from, and what the model leaves out. All inputs are set in `scenarios.py`.

## The model in brief

A simplified UK annuity writer. It owes pensions for life (the **liabilities**) and holds gilts, corporate bonds and shares (the **assets**). Assets minus liabilities is **own funds**, its cushion.

- **SCR** (Solvency Capital Requirement): the loss in a 1-in-200 bad year, found from 10,000 simulated years.
- **Solvency ratio** = own funds ÷ SCR. Below 100% means the insurer breaches the requirement.
- **AI crash:** a fixed set of shocks applied instantly to today's balance sheet.

## Results

| Insurer | Own funds | SCR | Ratio before | Ratio after crash |
|---|---|---|---|---|
| 1999-style (40% shares) | £71m | £162m | 44% | −53% |
| Modern, diversified credit (A) | £71m | £33m | 215% | 103% |
| Modern, concentrated credit (B) | £70m | £38m | 185% | 45% |

How sensitive these are to the crash's spread widening (ratio after crash):

| Spread widening (tech / other) | 1999-style | Modern A | Modern B |
|---|---|---|---|
| +250 / +75 bps | −52% | 120% | 65% |
| **+300 / +100 bps (used)** | **−53%** | **103%** | **45%** |
| +400 / +150 bps | −56% | 69% | 7% |

The 1999-style insurer fails, and concentration costs the modern insurer 50–60 points, under every setting.

## Inputs

**Liabilities**

| Input | Value | Source |
|---|---|---|
| Pensioners | 10,000, aged 60–90 | Round numbers for a ~£1bn annuity book |
| Annual payment | £10,000, level, paid at year end | Roughly a typical UK annuity |
| Mortality | Gompertz-Makeham: A = 0.00022, B = 2.7×10⁻⁶, c = 1.124 | Standard Ultimate Survival Model (Dickson, Hardy & Waters). Life expectancy at 65 is 22.7 years |

Liabilities are worth £943m, with a duration of 8.6 years.

**Interest rates (Vasicek)**

| Input | Value | Source |
|---|---|---|
| Short rate today `r0` | 3.75% | Bank of England Bank Rate, October 2026 |
| Long-run level `b` | 5% | Gives long gilt yields of ~4.5%, as in recent years |
| Pull-back speed `a` | 0.15 | Long yields move about half as much as the short rate |
| Volatility `sigma_r` | 1% | 1-in-200 fall in the 10-year yield of ~1.2 points, close to the Solvency II standard formula |

**Credit spreads**

| Input | Tech / data centres | Other corporates | Source |
|---|---|---|---|
| Spread today | 180 bps | 120 bps | Judgement; 120 bps is roughly typical for UK investment-grade bonds (**check against a current index**) |
| Long-run spread | 200 bps | 130 bps | Judgement |
| Pull-back speed | 0.5 | 0.5 | Spread panics fade faster than rate cycles |
| Volatility | 1.2% | 0.65% | 1-in-200 widening of ~270 and ~135 bps |
| Matching adjustment | 50% of the bond portfolio's average spread | | Stands in for spread minus fundamental spread |

**Shares (GBM, using `src/gbm.py`)**

| Input | Tech | Non-tech | Source |
|---|---|---|---|
| Expected return | 8.5% | 7.5% | Risk-free rate + equity risk premium |
| Volatility | 24% | 16% | Yahoo Finance 2016–2025: XLK and SPXT |
| Share of equities | 38% | 62% | S&P 500 tech weight, June 2026 |

**Correlations**

| | Tech eq | Non-tech eq | Rate | Tech spread | Other spread |
|---|---|---|---|---|---|
| **Tech equity** | 1 | 0.74 | 0.50 | −0.75 | −0.60 |
| **Non-tech equity** | | 1 | 0.50 | −0.60 | −0.75 |
| **Rate** | | | 1 | −0.50 | −0.50 |
| **Tech spread** | | | | 1 | 0.80 |

Sources: 0.74 is from Yahoo data (XLK vs SPXT). The ±0.50 and ±0.75 values follow the Solvency II standard formula. 0.80 is judgement.

**Portfolios** (all bonds 9 years, matched to the liabilities)

| Insurer | Gilts | Corporate bonds | Shares | Tech share of corporate bonds |
|---|---|---|---|---|
| Modern (A) | 55% | 40% | 5% | 10% |
| Concentrated (B) | 55% | 40% | 5% | 50% |
| 1999-style | 35% | 25% | 40% | 10% |

Starting cushion: own funds = 7.5% of liabilities (£71m), chosen so the modern insurer starts near the ~200% typical of UK annuity writers.

**AI crash**

| Shock | Value |
|---|---|
| Tech shares | −50% |
| Other shares | −20% |
| Gilt yields | −75 bps (parallel shift) |
| Tech spreads | +300 bps |
| Other spreads | +100 bps |

**Simulation:** 10,000 one-year paths, monthly steps, seed 42.

## What the model leaves out

- **Defaults and downgrades:** bonds only lose value when spreads widen, so real losses would be larger.
- **Longevity risk:** deaths follow expectations exactly.
- **Reinsurance and counterparty risk.**
- **Crisis correlations:** one fixed correlation matrix.
- **The real matching adjustment rules:** eligibility tests and the fundamental spread.
- **The risk margin:** liabilities are best estimate only.
- **Fat tails:** all shocks are bell-curve shaped, which understates crashes.
- **Recalculating the SCR after the crash:** it is held at its pre-crash value.
- **Other simplifications:**
  - each bond bucket is a single zero-coupon bond,
  - the rate model has one factor,
  - the US share data is used as a proxy for UK insurers' holdings,
  - both insurers get the same starting cushion.

## Check before presenting

- The 120 bps starting spread, against a current UK investment-grade index.
- Solvency I's ~4% of reserves capital requirement.
- The UK resilience test details (2001–02).
- The six-month SCR recovery period.
- The MCR range of ~25–45% of the SCR.
