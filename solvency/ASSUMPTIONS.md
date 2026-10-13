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
| "Risk switched off" means no randomness | A switched-off driver follows its expected path | Lets us compute standalone SCRs. With everything off, SCR is close to but not exactly zero, because equities and corporate bonds are expected to earn slightly more than gilts |
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
