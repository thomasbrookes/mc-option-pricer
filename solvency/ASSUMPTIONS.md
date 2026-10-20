# Assumptions log

Plain-English cheat sheet for presentation Q&A and interviews. Every parameter, its default, where it comes from, and every simplification the model makes.

## What the model is

A simplified UK annuity writer. It has promised fixed yearly payments to pensioners for life (the **liabilities**). It holds gilts, corporate bonds, equities and a reinsurance asset to pay for them (the **assets**). The difference between the two is **own funds**, the insurer's safety cushion.

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
| Reinsurance as a quota share | The reinsurance asset = a fixed fraction of the liability value | Simple; it is only written down in the AI crash stress (reinsurer default) |
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
