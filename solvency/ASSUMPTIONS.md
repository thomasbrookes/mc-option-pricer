# Assumptions log

Plain-English cheat sheet for presentation Q&A and interviews. Every parameter, its default, where it comes from, and every simplification the model makes.

## What the model is

A simplified UK annuity writer. It has promised fixed yearly payments to pensioners for life (the **liabilities**). It holds gilts, corporate bonds and equities to pay for them (the **assets**). The difference between the two is **own funds**, the insurer's safety cushion.

- **SCR** (Solvency Capital Requirement): how much own funds would shrink in a 1-in-200 bad year. Found by simulating 10,000 possible years and taking the 0.5th-worst-percentile outcome.
- **Solvency ratio** = own funds ÷ SCR. Above 100% means the insurer survives a 1-in-200 year.
- **AI crash stress**: a single deterministic shock (no randomness) applied to today's balance sheet. The resulting fall in own funds is compared against the SCR.

## Simplifications

| Simplification | What it means | Why it's acceptable |
|---|---|---|
| One-year horizon | We only look one year ahead | This is the Solvency II definition of the SCR |
| 1-in-200 (99.5%) | SCR = loss at the 0.5th percentile of own funds | Solvency II calibration standard |
| Deterministic mortality | We use expected deaths; there is no longevity risk | Longevity risk doesn't help show either of our two points (bonds vs equities, diversification) |
| Gompertz-Makeham mortality law | A simple formula for the chance of dying at each age, instead of real mortality tables | No external data needed; it captures the key shape (death rates rising exponentially with age) |
| Level annuities, paid annually in arrears | Fixed £ amount, no inflation link, paid at the end of each year | Keeps cash flows simple; the year-1 payment comes out of assets at t=1 |
| No risk margin | Liabilities = best-estimate value only | Simplification; the risk margin doesn't change the story |
| Simplified matching adjustment | Liabilities are discounted at the gilt rate plus a fixed fraction of the corporate bond spread | The real matching adjustment has strict eligibility rules and a fundamental-spread deduction; this captures the idea that holding bonds to maturity lets you ignore some spread moves |
| Bonds as zero-coupon bonds | Each bond bucket is one zero-coupon bond whose maturity equals the input duration | A zero-coupon bond's duration is its maturity, so "duration" stays an input and is easy to explain |
| No defaults or downgrades | Corporate bonds only lose value through spread widening | Out of scope for now; extension point left in credit.py |
| Same rate parameters for simulating and pricing | Vasicek is simulated with real-world parameters and the same parameters are used in the bond price formula (zero market price of rate risk) | Avoids a second set of parameters that would be hard to justify |
| Credit spreads floored at zero | A mean-reverting process could go negative; we stop it at 0 | Negative spreads make no economic sense |
| No reinsurance or counterparty risk | The insurer keeps all its liabilities; no reinsurer can default on it | Keeps the model focused on shares and credit. Adding a reinsurer default would make the AI crash worse: an easy improvement to mention |
| No randomness check | With every volatility set to zero, the SCR should come out close to zero | Not exactly zero, because equities and corporate bonds are expected to earn slightly more than gilts |
| Discounting back | Own funds at t=1 are brought back to today using today's one-year gilt price | Simple and consistent |
| AI crash is instantaneous | Shocks are applied to today's balance sheet all at once | Standard way to present a stress test |
| SCR held fixed after the crash | Post-crash solvency ratio = post-crash own funds ÷ pre-crash SCR | In reality the SCR would be recalculated; holding it fixed gives a cleaner before/after comparison |
| Rate shock is a parallel shift | Every interest rate falls by the same amount in the AI crash | Easiest to explain; real curves twist as well as shift |

## Parameters

Added as each component is built.

### Mortality (Gompertz-Makeham)

Chance of dying at age x is driven by `A + B × c^x`: a flat background part plus a part that grows exponentially with age.

| Parameter | Default | What it means | Source / rationale |
|---|---|---|---|
| `A` | 0.00022 | Background death rate that doesn't depend on age (accidents etc.) | Standard Ultimate Survival Model, Dickson, Hardy & Waters, *Actuarial Mathematics for Life Contingent Risks* |
| `B` | 0.0000027 | Size of the age-related part | Same source |
| `c` | 1.124 | Death rates rise about 12.4% per year of age | Same source |
| `max_age` | 120 | Nobody lives past this | Common actuarial convention |

Gives a life expectancy at 65 of about 22.7 years. That's a bit above the ONS general population (roughly 18.5 for men and 21 for women), which is realistic: people who buy annuities tend to be healthier and wealthier than average.

### Liabilities (the annuity block)

| Parameter | Default | What it means | Source / rationale |
|---|---|---|---|
| `n_annuitants` | 10,000 | Number of pensioners | Round number giving a ~£1bn book, a small but realistic UK annuity writer |
| `age_min`, `age_max` | 60, 90 | Pensioners are spread evenly across these ages | Covers the typical range of annuities in payment |
| `annual_payment` | £10,000 | Fixed yearly payment per pensioner, paid at year end | Roughly a typical UK annuity income |

Resulting book: about £97m paid in year 1, worth about £1bn at a 4% interest rate, with a **duration of about 9 years**. That means the promises behave roughly like a 9-year bond, which is why the insurer needs long bonds to match them.

### Interest rates (Vasicek)

The short-term interest rate follows `dr = a(b − r)dt + σ dW`: each month it gets pulled part of the way back towards a long-run level `b`, plus a random shock of size `σ`. A closed-form formula then turns the short rate into the price of a bond of any maturity, which gives the whole yield curve.

| Parameter | Default | What it means | Source / rationale |
|---|---|---|---|
| `r0` | 3.75% | Short rate today | Roughly in line with recent Bank of England base rate. **Check the current figure before presenting** |
| `a` | 0.15 | Speed of pull back to `b`: about 15% of the gap closes each year | Chosen so long yields move about half as much as the short rate, which is realistic |
| `b` | 5% | Long-run level the short rate is pulled towards | Gives long gilt yields of about 4.5%, in the range UK gilts have traded at in recent years |
| `sigma_r` | 1% | Size of yearly random shocks to the short rate | Gives a 1-in-200 fall in the 10-year yield of about 1.2 points, similar to the Solvency II standard formula's interest-rate-down stress |
| `n_paths` | 10,000 | Number of simulated one-year scenarios | Brief requirement; enough for a stable 1-in-200 percentile |
| `seed` | 42 | Random number seed | Makes every run give identical results |

Resulting yield curve today: 1-year 3.84%, 10-year 4.29%, 30-year 4.58%. On this curve the liabilities are worth **£965m** with a duration of **8.6 years**.

**Rate simplifications:**
- **Vasicek allows negative rates.** That's realistic (UK and European rates were negative or near zero in the 2010s), but with these settings it essentially never happens within one year: the 1-in-200 low short rate is about 1.6%.
- **Monthly steps, simple update rule.** Each month the rate moves by `a(b − r) × 1/12 + σ × shock`. The checks confirm the simulated mean and spread after one year match the exact Vasicek values.
- **One factor.** Every yield is driven by the single short rate, so the curve can shift and tilt but not twist in more complicated ways.

**How accurate is Vasicek?** Good enough for our purpose, but not production grade.
- *Gets right:* rates move randomly but get pulled back to a normal level. Most real yield-curve movement is the whole curve shifting up or down together, which is what Vasicek captures, and what hurts annuity writers. Its 1-in-200 shock is close to the standard formula's.
- *Falls short:*
  - One factor, so the curve can't twist (short rates up, long rates down).
  - Bell-curve shocks understate extreme moves, e.g. the 2022 mini-budget gilt crisis.
  - Volatility is constant.
  - Its smooth curve doesn't exactly match today's real gilt curve.
- *What insurers actually use:* economic scenario generators with multi-factor models (e.g. multi-factor Hull-White, which is Vasicek adjusted to fit today's curve exactly).
- *Q&A line:* "Vasicek captures the main risk, rates moving as a whole, with a standard-formula-sized shock. A production model would add more factors and fatter tails."
- *Bank Rate vs gilt yields:* Bank Rate moves in 0.25-point steps, but we value with gilt yields, which move continuously because they price in expectations of all future rate decisions.

### Credit spreads and corporate bonds

A corporate bond yields the gilt rate plus a **credit spread**, the extra interest for lending to a company rather than the government. Each spread follows the same "pulled back to normal, plus random shocks" process as the Vasicek short rate. A corporate bond is valued as the gilt price × `exp(−spread × years to maturity)`.

| Parameter | Default | What it means | Source / rationale |
|---|---|---|---|
| `s0_tech` | 1.80% (180 bps) | Tech/data-centre spread today | Judgement: above general corporate spreads, reflecting heavy borrowing to build data centres |
| `theta_tech` | 2.00% | Long-run tech spread | Judgement |
| `kappa_tech` | 0.5 | Speed tech spreads are pulled back to normal (about 40% of the gap closes each year) | Spread panics fade faster than rate cycles |
| `sigma_tech` | 1.20% | Size of yearly tech spread shocks | Gives a 1-in-200 widening of about 270 bps, in the spirit of telecom debt in 2001–02 |
| `s0_other` | 1.20% (120 bps) | Other corporate spread today | Approximately typical for UK investment-grade (A/BBB) corporate bonds; **check against a current index before presenting** |
| `theta_other` | 1.30% | Long-run other spread | Judgement |
| `kappa_other` | 0.5 | Speed other spreads are pulled back | As tech |
| `sigma_other` | 0.65% | Size of yearly other spread shocks | Gives a 1-in-200 widening of about 135 bps, roughly the Solvency II standard formula's spread stress for 10-year A/BBB bonds |
| `ma_fraction` | 50% | Share of the bond portfolio's average spread allowed as matching adjustment | Stands in for "spread minus fundamental spread": roughly half of investment-grade spread is commonly attributed to expected defaults and downgrades |

**Matching adjustment as built:** MA = `ma_fraction` × the value-weighted average spread across all bonds (gilts count as zero spread; equities are not eligible). Example: 60% gilts, 10% tech and 30% other corporates gives an MA of 27 bps, cutting the liabilities from £965m to £943m.

**Credit simplifications:**
- **No defaults or downgrades.** Bonds lose value only when spreads widen. In reality downgrades also raise the fundamental spread, which shrinks the MA. Our MA never erodes, the same blind spot as the real rule in a bubble.
- **One flat spread per bucket**, the same for every maturity. Real spread curves vary by maturity.
- **Bell-curve shocks, floored at zero.** Real spreads jump up sharply in crises and rarely fall far, so their moves are lopsided. Ours are symmetric, and a small share of paths (about 1–3%) get floored at zero spread. That only affects the benign side, not the 1-in-200 tail we care about.
- **MA weighting by value, not by duration.** A real MA is calculated from the matched asset cash flows.

### Equities

Two buckets, tech/AI and non-tech, each following Geometric Brownian Motion and linked by a correlation. Simulated with `sim_correlated_paths` from the existing option-pricer engine (`src/gbm.py`), unchanged. The model starts both at £1 and reads off what each has grown to after one year.

| Parameter | Default | What it means | Source / rationale |
|---|---|---|---|
| `mu_eq_tech` | 8.5% | Expected yearly return on tech shares | Risk-free rate (~4%) + 4.5% equity risk premium. **Not** a historical average: those are too noisy (see the README) |
| `mu_eq_other` | 7.5% | Expected yearly return on non-tech shares | Risk-free rate (~4%) + 3.5% equity risk premium |
| `sigma_eq_tech` | 24% | Volatility of tech shares | Yahoo Finance: XLK (US tech sector fund), daily returns 2016–2025: 24.3% |
| `sigma_eq_other` | 16% | Volatility of non-tech shares | Yahoo Finance: SPXT (S&P 500 excluding tech), 2016–2025: 16.3% |
| `rho_equity` | 0.74 | Correlation between tech and non-tech returns | Yahoo Finance: XLK vs SPXT daily returns, 2016–2025 |
| `tech_weight` | 38% | Share of the insurer's equities in tech | S&P 500 Information Technology sector weight, end June 2026 (from the brief) |

Resulting 1-in-200 one-year falls: **tech −44%, non-tech −29%**. Example: an insurer with £1bn of assets loses £16m in a 1-in-200 equity year with 5% in equities, or £131m with 40% in equities.

**Equity simplifications:**
- **US data as a proxy.** A UK insurer holds UK and global shares, but the tech sector is overwhelmingly US-listed, and these are the cleanest long series for tech vs non-tech.
- **GBM has thin tails.** The non-tech 1-in-200 fall of 29% is milder than the Solvency II standard formula's 39% equity stress, because GBM's bell-curve returns understate crashes. This makes our equity SCR, if anything, an underestimate, which strengthens the conclusion that equities are risky.
- **Constant volatility.** Tech volatility was 45% during the dot-com crash (XLK, March 2000 to October 2002), almost double its recent level. A single volatility can't capture that, which is one reason the AI crash is run as a separate deterministic stress.
- **No dividends.** Total return is folded into `mu`.

### Correlation between all five risks

All five risk drivers move together through one correlation matrix, applied with Cholesky inside the existing `sim_correlated_paths` engine. The trick: the rate and the two spreads are fed into the engine as "assets" with zero drift and unit volatility, so their log prices are just correlated random walks. Their monthly changes become the shocks that drive Vasicek and the spread processes.

| | Tech equity | Non-tech equity | Short rate | Tech spread | Other spread |
|---|---|---|---|---|---|
| **Tech equity** | 1 | 0.74 | 0.50 | −0.75 | −0.60 |
| **Non-tech equity** | 0.74 | 1 | 0.50 | −0.60 | −0.75 |
| **Short rate** | 0.50 | 0.50 | 1 | −0.50 | −0.50 |
| **Tech spread** | −0.75 | −0.60 | −0.50 | 1 | 0.80 |
| **Other spread** | −0.60 | −0.75 | −0.50 | 0.80 | 1 |

**Reading the signs:**
- **Positive equity–rate (0.50):** when shares fall, rates tend to fall too, as central banks cut and investors flee to gilts. That's bad for an annuity writer, since both its equities and its rate position lose at once.
- **Negative equity–spread:** when shares fall, spreads widen.
- **Negative rate–spread:** when rates fall, spreads tend to widen (a flight to safety).

**Sources:**
- **Equity–equity 0.74:** Yahoo Finance, XLK vs SPXT daily returns, 2016–2025.
- **Equity–rate 0.50, rate–spread 0.50 and equity–spread 0.75 (in size):** the Solvency II standard formula's market-risk correlations, applying when the insurer is exposed to falling rates. Each equity bucket links most strongly (0.75) to its own sector's spread and less (0.60) to the other.
- **Tech spread–other spread 0.80:** judgement. Credit markets widen together, but sector shocks differ.

**Effect:** in the worst 1% of years for tech shares, the simulation also has non-tech shares −24%, the short rate −118 bps, tech spreads +206 bps and other spreads +91 bps. Bad things happen together, as in a real crisis.

**Simplifications:**
- **One fixed matrix.** Real correlations rise in a crisis. Crisis correlations are out of scope; the deterministic AI crash stress hits everything at once instead.
- **Standard formula correlations are between capital charges, not between the risk drivers themselves.** Using them as driver correlations is a common simplification.
- **Bell-curve dependence** (a Gaussian copula). Real markets show stronger links in the extreme tail than this allows.

### Balance sheet, SCR and solvency ratio

**Today:**
```
Assets (gilts + corporate bonds + shares)   £1,014m
Liabilities (pension promises, with MA)    −  £943m
Own funds (the cushion)                        £71m
```

**After each of the 10,000 simulated years:**
1. Every asset is revalued on that year's rates, spreads and share prices.
2. The year-1 pension payment is paid out of assets.
3. The remaining promises are revalued on that year's curve, with that year's MA.
4. Own funds = assets − liabilities, discounted back to today with the 1-year gilt price.

**SCR** = own funds today − the 1-in-200 worst own funds after a year. **Solvency ratio** = own funds ÷ SCR.

| Parameter | Default | What it means | Source / rationale |
|---|---|---|---|
| `own_funds_ratio` | 7.5% | Starting cushion as a share of the liabilities (£71m) | Chosen so the modern insurer starts at about 200%, typical for UK annuity writers. Our SCR only covers market risk, so less cushion is needed than in reality to reach that ratio |
| Modern portfolio | 55% gilts, 40% corporate bonds, 5% shares | A typical modern UK annuity writer | Brief: ~5% equities, rest mainly bonds |
| 1999-style portfolio | 35% gilts, 25% corporate bonds, 40% shares | Pre-dot-com style, heavy in shares | Brief: ~40% equities |
| `gilt_maturity`, `corp_maturity` | 9 years | Every bond matures in 9 years | Matched to the liabilities' 8.6-year duration. A scan of 7–11 years confirmed this is close to where interest-rate risk is smallest |
| `corp_tech_share` | 10% | Share of corporate bonds lent to tech/data centres | Roughly tech's weight in a broad corporate bond index (approximate) |

**Results:**

| Insurer | Own funds | SCR | Solvency ratio |
|---|---|---|---|
| Modern | £71m | £33m | 215% |
| 1999-style | £71m | £162m | 44% |

**Same cushion for both: why that's fair.** Before Solvency II, capital rules for life insurers were based mainly on the size of the liabilities (roughly 4% of reserves under Solvency I, from memory; **check before quoting**), not on investment risk. So a 1999 insurer could hold 40% in shares without a bigger cushion. Measured by today's 1-in-200 test, it covers only 44% of its requirement. That is exactly why the rules changed.

**What drives the modern insurer's SCR:** in its worst 1% of years, credit spreads widen sharply (tech +164 bps, other +108 bps) and shares fall 23%. Interest rates barely matter, because the bonds are matched. Its main risk is credit, not shares or rates: it has swapped share risk for credit risk (slide 15).

**Checks:**
- With every volatility set to zero, the SCR is −£4m: a small gain, because shares and corporate bonds are expected to earn slightly more than gilts.
- The SCR moves by less than 1% across random seeds.

**Simplifications:**
- **Same cushion for both insurers.** A real 1999 with-profits insurer often had extra buffers.
- **The SCR covers market risk only:** no longevity, default, operational or counterparty risk.
- **Bonds are not reinvested.** Each bucket is one bond held for the year, and the year-1 payment is simply deducted from assets.

### The AI crash (deterministic stress)

Applied instantly to today's balance sheet. No randomness: every shock hits at once. The SCR is held at its pre-crash value, so ratio after = own funds after ÷ SCR before.

| Shock | Default | Rationale |
|---|---|---|
| `tech_shock` | −50% | Brief. Tech fell about 80% in the dot-com bust (Nasdaq, 2000–02), so −50% is a moderate AI crash |
| `other_shock` | −20% | Brief |
| `rate_shock` | −0.75 points (−75 bps) | Brief (range −50 to −100 bps); a parallel shift of the whole gilt curve as investors flee to safety |
| `tech_spread_shock` | +3 points (+300 bps) | Judgement: the telecom-debt story; slightly beyond the model's own 1-in-200 tech widening (about +270 bps) |
| `other_spread_shock` | +1 point (+100 bps) | Judgement: roughly the widening in broad investment-grade spreads during the dot-com bust (approximate, from memory) |
| Reinsurer default | Not modelled | Left out to keep the focus on shares and credit |

**Portfolios:** the modern insurer (A) and the 1999-style insurer as in the balance sheet section, plus **concentrated (B)**: the modern insurer with 50% of its corporate bonds in tech/data-centre debt instead of 10%. B represents an insurer that has leaned into AI lending: still all investment grade, but one sector.

**Results:**

| Insurer | Own funds | SCR | Ratio before | Own funds after | Ratio after |
|---|---|---|---|---|---|
| 1999-style (40% shares) | £71m | £162m | 44% | −£86m | **−53%** |
| Modern, diversified credit (A) | £71m | £33m | 215% | £34m | **103%** |
| Modern, concentrated credit (B) | £70m | £38m | 185% | £17m | **45%** |

**Where the losses came from (£m, positive = lost):**

| Insurer | Shares | Bonds | Liabilities | Total |
|---|---|---|---|---|
| 1999-style | 127 | −15 (gain) | 45 | 157 |
| Modern A | 16 | −23 (gain) | 44 | 37 |
| Modern B | 16 | 3 | 35 | 53 |

The liabilities rise because rates fall 75 bps, partly offset by the MA rising from 27 to 48 bps. The bonds gain from lower rates but lose from wider spreads; for B the spread loss on tech debt wins.

**Sensitivity (ratio after: 1999-style | A | B):**

| Spread widening (tech / other) | Rates −50 bps | Rates −75 bps | Rates −100 bps |
|---|---|---|---|
| +200 / +50 bps | −46% / 135% / 83% | −50% / 138% / 85% | −55% / 140% / 87% |
| +250 / +75 bps | −47% / 117% / 63% | −52% / 120% / 65% | −56% / 122% / 66% |
| **+300 / +100 bps (default)** | −49% / 100% / 43% | **−53% / 103% / 45%** | −58% / 105% / 46% |
| +400 / +150 bps | −51% / 67% / 6% | −56% / 69% / 7% | −60% / 71% / 8% |

**What's robust:**
- The 1999-style insurer fails under every setting.
- Concentration costs the modern insurer 50–60 percentage points under every setting.
- The rate shock barely matters, because the bonds are matched.
- Whether the diversified modern insurer stays above 100% depends on how far credit spreads widen.
