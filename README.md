# mc-option-pricer

A Monte Carlo simulation engine for pricing options and measuring portfolio risk, built from scratch in Python. 

## 1. What this project actually does

At its core, this project answers three related questions using the same underlying tool — simulating thousands of possible future paths a stock price could take:

1. **What should an option cost?** (option pricing)
2. **How much could I realistically lose on a stock or portfolio?** (risk measurement — VaR and Expected Shortfall)
3. **How sensitive is an option's price to changes in the market?** (the Greeks)

All three questions are answered the same way: simulate a large number of plausible futures for a stock price, then look at what happens across those simulated futures (the average payoff, the worst outcomes, how the price shifts, etc.). Everything downstream — pricing, risk, sensitivities — is built on top of one foundational tool: simulating a stock price path.

Later, real historical stock data (via `yfinance`) was plugged into this same machinery, so the whole pipeline can run on actual companies (AAPL, MSFT, etc.) instead of made-up numbers.

## 2. The foundation: simulating a stock price (`gbm.py`)

### The model: Geometric Brownian Motion (GBM)

Every piece of this project rests on one assumption: a stock's price evolves according to **Geometric Brownian Motion**. This is the standard simplified model of how a stock price moves over time, and it says a stock's price is driven by two things happening continuously:

- A **drift** — a steady, predictable trend (the stock's average growth rate).
- **Random noise** — unpredictable day-to-day wobble, proportional to how volatile the stock is.

The formula used to step the price forward by a small time increment `dt` is:

```
S_next = S_prev * exp((mu - 0.5 * sigma^2) * dt + sigma * sqrt(dt) * Z)
```

Where:
- **`S0`** — the stock's current price.
- **`mu`** — the drift: the average rate of return we assume the stock grows at (e.g. `0.08` means 8% a year, on average).
- **`sigma`** — volatility: how much the stock's returns bounce around that average. A higher sigma means bigger swings, up and down.
- **`Z`** — a random number drawn from a standard normal distribution (a bell curve centred at 0) — this is what injects randomness into each step, representing the unpredictable part of daily price moves.
- **`dt`** — the size of each time step (e.g. one trading day, if we're stepping through a year in 252 steps).

The `- 0.5 * sigma^2` term is a mathematical correction (it comes from converting between "the average of the returns" and "the return of the average" when working in log-space — without it, the simulation would systematically drift upward more than intended, purely as an artefact of the maths).

**Why simulate at all, instead of just using the formula for where the price will end up?** Because we don't just want *one* possible outcome — we want a realistic *spread* of outcomes, so that later we can ask questions like "what's the worst 5% of outcomes look like?" One simulated path tells you nothing about risk; thousands of them build up a full distribution of possible futures.

### Two versions: `sim_path` and `sim_paths`

- **`sim_path(S0, mu, sigma, T, N)`** — the first version built, using a plain Python loop: step forward one day at a time, `N` times, appending each new price. Simple, but slow for many paths, since Python loops don't scale well.
- **`sim_paths(S0, mu, sigma, T, N, n_paths)`** — the version actually used everywhere else in the project. Instead of looping day-by-day, it generates *all* the random shocks for *all* paths and *all* days in one go (`np.random.normal(size=(n_paths, N))`), then uses `np.cumsum` to add them up.

**Why cumulative sum works here, and why it has to be in log-space:** stock prices don't add up over time, they *multiply* (a 5% gain, then another 5% gain, isn't a 10% gain — it compounds). But if you take the *logarithm* of the price, the compounding turns into simple addition: `log(price_after_two_days) = log(price_today) + return_day1 + return_day2`. This is why `sim_paths` works entirely in log-space (`log_paths = np.cumsum(increments)`) and only converts back to real prices at the very end (`np.exp(log_paths)`). This one trick is what makes it possible to generate thousands of full paths in one fast, vectorised numpy operation instead of a slow loop.

**Verification done:** plotted 50 of 10,000 simulated paths and confirmed they fanned out in a shape consistent with the drift/volatility assumptions, and checked the average simulated final price roughly matched the theoretical expected price, `S0 * e^(mu*T)` (the closed-form expected value of GBM).

### The multi-asset version: `sim_correlated_paths`

Added later (Milestone 4) to support portfolios of more than one stock — covered in detail in the VaR section below, since the reason it exists is entirely about risk measurement.

## 3. Pricing a European call option (`option_pricer.py`)

A **European call option** gives the holder the right (not the obligation) to buy a stock at a fixed price (the **strike price, `K`**) at a fixed future date (**maturity, `T`**). If the stock ends up above the strike, the option is worth `stock price - strike`; if it ends up below, the option is worthless (you wouldn't pay `K` for something worth less). So the payoff at maturity is `max(S_T - K, 0)`.

### Two ways to get the same answer

**`black_scholes_call(S0, K, r, sigma, T)`** — the famous closed-form formula (Black & Scholes, 1973) that gives the exact theoretical price of a European call directly from a formula, no simulation needed:

```
price = S0 * N(d1) - K * e^(-r*T) * N(d2)
```

Where `N(x)` is the cumulative distribution function of the standard normal distribution (i.e. "what fraction of a bell curve lies below x"), and `d1`, `d2` are standardised measures of "how far in the money the option is expected to be," adjusted for time and volatility. The formula is essentially: *(probability-weighted value of receiving the stock) − (probability-weighted, discounted cost of paying the strike)*.

**`mc_call_price(S0, K, r, sigma, T, N, n_paths)`** — prices the same option by brute force: simulate thousands of possible price paths, work out the payoff `max(S_T - K, 0)` for each one, average all the payoffs, then discount that average back to today's money using `e^(-r*T)`.

### The critical detail: `r`, not `mu`

Notice `mc_call_price` calls `sim_paths` using `r` (the risk-free interest rate) as the drift — **not** `mu`, the real-world growth rate used everywhere in the GBM section above. This is one of the most important ideas in the whole project, and it's easy to miss.

**Why:** option pricing isn't about predicting what you personally think the stock will do — it's about finding the one price that prevents an arbitrage (a risk-free profit opportunity) between the option and the stock. The mathematics of no-arbitrage pricing works out so that, for this purpose, every asset must be simulated as if it grows at the **risk-free rate**, regardless of what anyone actually believes about the stock. This is called **risk-neutral valuation**. It's a deliberately artificial assumption used purely to arrive at a fair, arbitrage-free price — it is not a prediction, and it's a completely different question from "what do I think this stock will actually do" (which is where `mu` belongs instead, later, in the VaR section).

**Verification done:** compared `mc_call_price` against `black_scholes_call` at increasing path counts, and confirmed the gap between them shrank as expected:

| n_paths | MC price | Gap vs Black-Scholes |
|---|---|---|
| 1,000 | 11.3673 | 0.9167 |
| 10,000 | 10.6613 | 0.2107 |
| 100,000 | 10.4773 | 0.0267 |

(Black-Scholes price: 10.4506, for `S0=K=100, r=0.05, sigma=0.2, T=1`.) This shrinking gap is exactly what you'd expect from Monte Carlo: more simulated paths means less random noise in the average, converging toward the true theoretical price.

## 4. Measuring risk: VaR and Expected Shortfall (`var.py`)

Pricing answers "what should this cost." Risk measurement answers a different question: **"if I actually hold this stock (or portfolio), how much could I realistically lose?"**

### Value at Risk (VaR)

**VaR** is a threshold loss, defined by a confidence level. A **95% VaR** of £24 means: *there's only a 5% chance of losing more than £24 over the given time horizon.* It's a percentile of the distribution of possible losses.

**How `historical_var` computes it:** simulate thousands of possible future prices for the stock, work out the profit/loss for each simulated outcome, sort them, and read off the value at the chosen percentile (`np.percentile(losses, 95)` for a 95% VaR). No formula is needed — the simulation directly builds the empirical distribution of outcomes, and the percentile is read straight off it.

**Crucially, this uses `mu`, not `r`.** VaR is the opposite kind of question from option pricing — it's not about finding an arbitrage-free price, it's about honestly describing what you actually believe could happen to your wealth. That requires the real-world growth assumption, `mu`, which is exactly why `historical_var` calls `sim_paths` (real-world drift) rather than the risk-neutral machinery used for pricing.

### Expected Shortfall (ES / CVaR)

VaR has a real weakness: it only tells you *where the cutoff is*, not *how bad things get beyond it*. Two portfolios can have an identical VaR while one has a mild tail and the other has a catastrophic one — VaR alone can't tell them apart.

**Expected Shortfall** fixes this by averaging every simulated loss that falls *beyond* the VaR cutoff, rather than just marking the boundary. In `historical_var`, this reuses the exact same `losses` array already computed for VaR — no extra simulation needed, just `losses[losses >= var].mean()`.

**Verification done (single AAPL-like stock, `mu=0.08, sigma=0.2`):** 95% VaR of 23.91, Expected Shortfall of 29.78 — confirming ES sits meaningfully above VaR, i.e. the losses beyond the cutoff really are worse on average than the cutoff itself.

### Extending to a portfolio: correlation and Cholesky decomposition

A single stock's VaR isn't enough for a real portfolio, because a portfolio's risk depends not just on each stock's individual volatility, but on **how the stocks move together.**

**Correlation** is a number between -1 and +1 describing how much two things tend to move together (+1 = perfect lockstep, 0 = unrelated, -1 = perfect opposites). Real stocks are rarely independent — and critically, if you simulated a group of stocks independently, you'd be implicitly assuming zero correlation, which understates real risk (in reality, bad days tend to hit a whole portfolio at once, not one stock in isolation).

A **covariance matrix** (or correlation matrix, `corr_matrix`) is the table describing every pairwise relationship between the assets in a portfolio at once. The problem: `np.random.normal` only produces *independent* random numbers by construction — some way is needed to turn independent randomness into randomness that matches a target correlation structure.

That's exactly what **Cholesky decomposition** does. `np.linalg.cholesky(corr_matrix)` factors the correlation matrix into a matrix `L` such that, if you take independent random draws and multiply them through `L`, what comes out has exactly the correlation structure you specified. Concretely, for two assets with correlation `rho`:

```
correlated_shock_1 = Z1
correlated_shock_2 = rho * Z1 + sqrt(1 - rho^2) * Z2
```

Stock 2's shock is built from a *shared* component (borrowed from stock 1) plus its *own* independent component — the higher `rho`, the more its randomness is dominated by the shared piece. `sim_correlated_paths` in `gbm.py` implements exactly this: it draws independent shocks for every asset, every path, and every time step (`Z`, shape `(n_paths, N, n_assets)`), correlates them in one step (`Z @ L.T`), then runs the same GBM update formula as `sim_paths`, just with an extra "which asset" dimension.

`portfolio_var` in `var.py` then works exactly like `historical_var`, but on the *sum* of all the correlated simulated stock values (`S_T @ shares`) instead of a single stock's value.

**Two things worth noting about correlation matrices:**
- They must be symmetric (correlation between A and B is the same fact as between B and A) *and* positive semi-definite — the chosen correlations must be mutually consistent (you can't pick contradictory pairwise relationships and expect Cholesky to succeed).
- **Correlation is not stable in reality** — a well-documented phenomenon is that correlations spike upward during market crashes ("correlations go to 1 in a crisis"), while calmer periods show more independent, company-specific behaviour. A single fixed correlation number (as used throughout this project) is a simplification that misses this — a real limitation, not just a footnote (see Section 7).

**Verification done (4-stock portfolio, correlations ranging 0.1–0.6):** portfolio VaR came out at 58.02, versus 84.34 if you'd naively summed each stock's individual VaR — a 26.32 gap representing the genuine diversification benefit of holding stocks that don't move in lockstep. This is the direct mathematical justification behind "don't put all your eggs in one basket" — more precisely, don't put your eggs in baskets that all move the same way.

## 5. The Greeks (`greeks.py` + closed-form additions to `option_pricer.py`)

The **Greeks** measure how sensitive an option's price is to small changes in each of its inputs — used in practice to manage the risk of holding or trading options.

- **Delta** — sensitivity to the stock price. Also doubles as an approximate hedge ratio (how many shares you'd hold to offset the option's risk).
- **Vega** — sensitivity to volatility.
- **Rho** — sensitivity to the risk-free rate.
- **Theta** — the option's rate of value decay as time passes (time to expiry shrinking, all else equal).

### Method: bump-and-revalue

Rather than deriving a new formula for each Greek, each one is estimated numerically: **price the option, nudge ("bump") exactly one input slightly, re-price, and see how much the price moved relative to the size of the bump.** This ratio is the sensitivity.

- `delta`: bumps `S0` up and down by `h=1`, central difference: `(price_up - price_down) / (2h)`.
- `vega`: bumps `sigma` by `h=0.01`.
- `rho`: bumps `r` by `h=0.0001`.
- `theta`: shrinks `T` by one trading day (`h=1/252`) and compares to the base price directly (not a central difference — this one asks "what happens as time passes," which is inherently one-directional).

### The noise problem, and the fix: common random numbers

Since Monte Carlo pricing uses fresh random draws every call, naively bumping an input and re-running with brand-new randomness would mix genuine sensitivity with pure simulation noise. The fix used throughout `greeks.py`: **reset `np.random.seed(42)` immediately before each of the two price calls being compared**, so both use *identical* underlying random paths. When the two prices are subtracted, the shared randomness cancels out almost entirely, leaving mostly the real effect of the bump. This technique is called **common random numbers**, and it makes each Greek estimate far more stable for the same number of simulated paths.

### Validating against the closed-form Black-Scholes Greeks

European calls also have exact closed-form Greek formulas (just like the price itself does), added as `bs_delta`, `bs_vega`, `bs_rho`, `bs_theta` in `option_pricer.py`. To avoid repeating the `d1`/`d2` formula five times, `black_scholes_call` was changed to return `(d1, d2, price)`, and every closed-form Greek function calls it and discards whichever parts it doesn't need.

**Verification done (`S0=K=100, r=0.05, sigma=0.2, T=1`):**

| Greek | MC (bump-and-revalue) | Black-Scholes (closed-form) |
|---|---|---|
| Delta | 0.6377 | 0.6368 |
| Vega | 36.0522 | 37.5240 |
| Rho | 53.6040 | 53.2325 |
| Theta | -0.0250 | -0.0255 |

Close agreement across the board — confirming bump-and-revalue correctly recovers the same sensitivities as the exact formulas. This matters because bump-and-revalue is the *only* option once you move beyond European options with known formulas (e.g. American options, discussed in Section 7) — proving it works here, where an answer exists to check against, is what justifies trusting it elsewhere.

**One unit-of-measurement quirk worth remembering:** the raw MC/Black-Scholes Vega and Rho above are both expressed "per 1.0 (full unit) change" in volatility/rate — e.g. Vega of 36 means "per volatility rising by 100 percentage points," which never happens in practice. The conventional real-world quoting divides by 100, giving "per 1 percentage point" — e.g. a Vega of ~0.36 (the price moves about 36p if implied volatility ticks up by 1 percentage point). Delta and Theta didn't need this adjustment, since they were already bumped in intuitively-sized steps (£1, 1 day).

## 6. Real market data (`market_data.py`)

Every example above used made-up numbers for `S0`, `mu`, `sigma`, and correlation. `market_data.py` uses `yfinance` to estimate all of these from real historical stock prices instead, and — importantly — **feeds them into the exact same functions above with no changes needed anywhere else.** This was the key design goal: `historical_var`, `portfolio_var`, etc. don't know or care whether their inputs came from a made-up example or real data.

- **`get_stock_params(ticker, start, end)`** — downloads daily closing prices, computes daily log returns, and returns:
  - `S0` — the most recent closing price.
  - `mu` — the historical average daily return, annualised (`mean * 252`).
  - `sigma` — the historical daily volatility, annualised (`std * sqrt(252)`).
- **`get_corr_matrix(tickers, start, end)`** — downloads multiple tickers at once and calls `.corr()` on their daily returns to get a real correlation matrix directly.

**Verification done:** ran real AAPL data (2023–2026 window) through `historical_var` unchanged — `S0=271.36, mu=0.2656, sigma=0.2545`, giving expected 1-year price of 353.89 (via `S0 * e^(mu*T)`), 95% VaR of 45.65, and ES of 67.44. Also ran a real 3-stock portfolio (AAPL, MSFT, XOM) through `portfolio_var` with a real correlation matrix, giving an expected portfolio value of 1096.25, VaR of 78.52, and ES of 136.23.

### An important, real limitation this surfaced

That AAPL `mu` of 26.6% annualised is a **genuinely unreliable number**, and it's worth understanding exactly why, since it's a real, well-known problem in finance rather than a mistake in this project. `mu` here is nothing more than "whatever the stock's average return happened to be over the specific 3-year window chosen" — it's backward-looking, not a forecast. The deeper issue: `sigma` (25.45%) came out *larger* than `mu` (26.56%) — meaning the year-to-year noise in the stock's returns is roughly as large as the average return itself. Estimating a stable, trustworthy average return from historical data generally requires many decades of data, not a few years — short windows are dominated by whatever happened to occur during that specific stretch. `sigma`, by contrast, is estimated far more reliably even from a short window, since volatility is a more stable, persistent property of a stock than its average return.

In practice, a more defensible `mu` might come from a longer historical window, or from a theory-grounded estimate (e.g. risk-free rate + a typical equity risk premium) rather than a raw historical average — but this project intentionally kept the raw estimate to make the limitation visible rather than hiding it.

## 7. Known limitations and simplifications

Worth being explicit about these, since understanding a model's blind spots is as important as understanding how it works:

- **VaR/ES are only as good as the `mu`/`sigma` fed in.** If those assumptions are wrong, the "95% confidence" is confidently wrong too — this is a real, known category of risk called **model risk**.
- **A single fixed correlation number doesn't capture changing correlation.** Real correlations tend to spike during market stress — exactly when accurate risk estimates matter most — and this project's covariance-matrix approach can't represent that. More advanced approaches (e.g. copula models, regime-switching correlation) exist specifically to address this, at the cost of significant added complexity.
- **Historical `mu` is a weak, noisy estimator**, demonstrated directly in Section 6.
- **GBM itself is a simplification of real stock behaviour** — it assumes constant volatility and continuously-varying (never jumping) prices, with normally-distributed returns. Real markets exhibit "fat tails" (extreme moves happen more often than a normal distribution predicts) and sudden jumps (e.g. earnings surprises), neither of which this model captures.

## 8. Future work: what's not built, and why

Stretch goals were prioritised (highest value/lowest effort first) as: American options → dividends → jump-diffusion → real market data. The real-data piece (Section 6) was actually done first, since it was assessed as low effort and high value — it needed no new financial theory, just plumbing real numbers into code that already existed. The remaining three are documented here rather than built, since polishing this README and the existing five milestones was judged better use of remaining time for the project's purpose (a CV artefact for bank/insurer quant-risk-flavoured roles) than adding a less-directly-relevant, higher-risk feature.

### American options, and the Longstaff-Schwartz method

A **European option** can only be exercised at maturity — everything built so far assumes this. An **American option** can be exercised at *any* point up to and including maturity, which is how most real single-stock exchange-traded options actually work.

**Why this breaks the current approach entirely:** the current Monte Carlo pricer works by simulating a path all the way to maturity, then computing one payoff at the end. But an American option holder faces a decision *at every point in time before maturity*: "should I exercise now and take the payoff immediately, or hold and keep the possibility of a better payoff later?" The catch is that making that decision optimally requires knowing the **continuation value** — the expected value of *not* exercising and continuing to hold the option — which depends on everything that could still happen in the future. A simulated path only tells you what happened, not what your best future option was at each intermediate point, so you can't answer "should I have exercised here" just by looking forward along one path.

**How Longstaff-Schwartz (2001) solves this — the "Least Squares Monte Carlo" method:**

1. Simulate a large number of price paths forward to maturity as normal (nothing new here — this reuses `sim_paths`/`sim_correlated_paths` directly).
2. Start at the final time step and work **backward** in time, one step at a time.
3. At each time step, for only the paths where the option is currently "in the money" (exercising now would be profitable), take the payoffs that would result from continuing to hold (i.e. what happens later on that path, already computed from the previous, later step), and run a regression: predict that continuation value from a handful of simple functions of the current stock price (e.g. `1, S, S^2`).
4. Use that regression's fitted values as an estimate of "the expected value of continuing to hold," for every in-the-money path at this time step.
5. Compare, path by path: is immediate exercise worth more than the estimated continuation value? Whichever is larger is used as that path's value at this time step, and the process moves one step further backward.
6. Repeat all the way back to today — the average of the final step's values (discounted appropriately) is the American option's price.

**Why regression specifically:** it's the tool that turns "a scattering of simulated future outcomes" into "a smooth estimate of expected value as a function of today's stock price" — without it, there'd be no way to estimate what continuing to hold is worth at each point using only the paths already simulated.

**Why this wasn't built:** it's a genuinely different algorithm, not an extension of the existing pricer — it requires backward iteration through the simulated paths (rather than one forward pass to a single terminal payoff) and a regression step at every time step, both new pieces of machinery. It's also easy to get subtly wrong (e.g. **look-ahead bias** — accidentally using information from a later time step that wouldn't actually have been known yet — is a classic, easy-to-miss error in Longstaff-Schwartz implementations), which made it a lower priority than a smaller, more certain finishing touch like the README itself.

### Dividends

Real dividend-paying stocks grow more slowly in *price* terms than a non-dividend payer with the same total return, because part of the return is paid out as cash along the way rather than reinvested into the share price. This would require adjusting the drift term in the GBM formula (subtracting a continuous dividend yield, `q`, from `mu` or `r` depending on context) and correspondingly adjusting the Black-Scholes formula. A comparatively contained change relative to American options.

### Jump-diffusion

GBM assumes prices move smoothly and continuously — no sudden gaps. Real prices can jump sharply on events like earnings announcements or unexpected news. Jump-diffusion models (e.g. Merton's model) add an extra random "jump" component on top of ordinary GBM, occurring at random times with random sizes, to better capture this. A moderate addition — new, but bounded in scope, unlike the structural change American options require.

## 9. Project structure

```
src/
├── gbm.py           # Core simulation: sim_path, sim_paths, sim_correlated_paths
├── option_pricer.py # black_scholes_call, mc_call_price, bs_delta/bs_vega/bs_rho/bs_theta
├── var.py           # historical_var, portfolio_var (both return (VaR, Expected Shortfall))
├── greeks.py         # delta, vega, rho, theta (bump-and-revalue Monte Carlo)
├── market_data.py    # get_stock_params, get_corr_matrix (real data via yfinance)
└── explore.py        # scratch space for testing/exploring - not permanent, cleared between explorations
```

## 10. Running this project

```
pip install -r requirements.txt
```

Everything is explored interactively via `src/explore.py`, using VS Code's `# %%` cell blocks (run a cell, see its output, no Jupyter/notebook file needed). Each function in `src/` is self-contained and can also be imported and used directly.