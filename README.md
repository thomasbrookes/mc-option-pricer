# mc-option-pricer

A Monte Carlo engine for option pricing and risk measurement, built from scratch in Python, extended into a simplified Solvency II capital model for a UK annuity writer.

## Part 1: Option pricing and risk (`src/`)

Everything is built on one tool: simulating thousands of possible stock price paths with **Geometric Brownian Motion**, vectorised in NumPy. For several assets, **Cholesky decomposition** turns independent random shocks into correlated ones.

| Module | What it does |
|---|---|
| `gbm.py` | Simulates single and correlated GBM price paths |
| `option_pricer.py` | Black-Scholes price and Greeks (closed form), and a Monte Carlo call price |
| `var.py` | Value at Risk and Expected Shortfall for one stock or a correlated portfolio |
| `greeks.py` | Delta, vega, rho and theta by bump-and-revalue, using common random numbers |
| `market_data.py` | Estimates volatility and correlation from real prices (yfinance) |

**Validation** (S0 = K = 100, r = 5%, σ = 20%, T = 1):

| | Monte Carlo (100,000 paths) | Black-Scholes |
|---|---|---|
| Call price | 10.477 | 10.451 |
| Delta | 0.638 | 0.637 |
| Rho | 53.6 | 53.2 |

**Key ideas:**
- **Option pricing uses the risk-free rate as drift** (risk-neutral valuation).
- **VaR uses the real-world drift.**
- **Diversification shows up in the numbers:** a 4-stock portfolio's VaR was 58, against 84 if each stock's VaR were simply added up.

## Part 2: Solvency II stress test (`solvency/`)

A simplified UK annuity writer, built for a presentation on whether insurers are ready for an AI bubble. It reuses the GBM/Cholesky engine above unchanged.

**How it works:**
- **Liabilities:** lifetime pensions, with Gompertz-Makeham mortality.
- **Assets:** gilts, valued with the Vasicek interest-rate model; corporate bonds with mean-reverting credit spreads, split into tech/data-centre and other; and tech and non-tech shares.
- **Correlation:** all five risks move together through one correlation matrix.
- **Matching adjustment:** a simplified version of the rule, applied to the liabilities.
- **SCR:** the 1-in-200 loss in own funds over 10,000 simulated years. Solvency ratio = own funds ÷ SCR.
- **AI crash:** tech shares −50%, other shares −20%, gilt yields −75 bps, tech spreads +300 bps, other spreads +100 bps, all applied instantly.

**Results:**

| Insurer | Solvency ratio | After AI crash |
|---|---|---|
| 1999-style (40% shares) | 44% | −53% |
| Modern (5% shares, matched bonds) | 215% | 103% |
| Modern, bonds concentrated in tech/AI | 185% | 45% |

The lessons from dot-com worked for shares, but the risk has moved into credit. Concentrating lending in AI and data centres turns a survivable crash into a breach.

Every input, source and simplification is listed in [`solvency/ASSUMPTIONS.md`](solvency/ASSUMPTIONS.md).

| Module | What it does |
|---|---|
| `scenarios.py` | All inputs, the portfolios, the AI crash |
| `liabilities.py` | Mortality, cash flows, valuation |
| `rates.py` | Vasicek simulation and closed-form bond prices |
| `credit.py` | Spread simulation, corporate bonds, matching adjustment |
| `equities.py` | Tech and non-tech shares via the existing engine |
| `correlation.py` | Correlation matrix checks |
| `balance_sheet.py` | Own funds, SCR and solvency ratio |
| `validation.py` | Sanity checks for every component |
| `run_presentation.py` | Runs the experiments and prints the results |

## Limitations

- **GBM and Vasicek use bell-curve shocks,** so they understate crashes.
- **Correlations are fixed,** though in reality they rise in a crisis.
- **The solvency model leaves out defaults, longevity risk and reinsurance,** so real losses would be larger.

## Running it

```
pip install -r requirements.txt
```

The scripts use VS Code `# %%` cells. Run `src/explore.py`, `solvency/validation.py` or `solvency/run_presentation.py` cell by cell.
