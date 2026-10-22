"""
Every model input, plus the experiments for the presentation:
1. Modern insurer (~5% equities) and 1999-style (~40% equities) - SCR and solvency ratio
2. The AI crash applied instantly to both - solvency ratio before and after (slide 14)
3. Modern insurer under the same crash, corporate bonds diversified (A) vs concentrated
   in tech/data-centre debt (B) (slide 16)

The parameters live here as plain variables so every script uses the same numbers -
validation.py and run_presentation.py both import them.
"""
import numpy as np
from rates import zcb_price, revalue_zcb
from credit import revalue_corporate, matching_adjustment
from liabilities import value_liabilities
from balance_sheet import initial_balance_sheet, simulate_own_funds, scr_and_ratio

# Parameters - defaults and sources are in ASSUMPTIONS.md

# Gompertz-Makeham mortality, death rate at age x = A + B * c**x
A = 0.00022 # age-independent part - accidents, illness that hit any age equally
B = 2.7e-6 # size of the age-related part
c = 1.124 # how fast death rates grow with age - roughly 12% higher each year older
max_age = 120 # nobody is assumed to live past this age

# The annuity block
n_annuitants = 10_000 # number of pensioners
age_min = 60 # youngest pensioner
age_max = 90 # oldest pensioner - spread evenly across ages age_min..age_max
annual_payment = 10_000 # £ paid to each pensioner per year, at the end of each year they're alive

# Vasicek interest rates, dr = a(b - r)dt + sigma dW
r0 = 0.0375 # short rate today - roughly the Bank of England base rate
a = 0.15 # speed the rate is pulled back to b - about 15% of the gap closes each year
b = 0.05 # long-run level the short rate is pulled towards
sigma_r = 0.01 # size of the random shocks - about 1 percentage point a year

# Credit spreads - mean-reverting like Vasicek, one process per bucket
s0_tech = 0.018 # tech/data-centre spread today - 180 bps
theta_tech = 0.020 # long-run tech spread
kappa_tech = 0.5 # speed tech spreads are pulled back - faster than rates, panics fade
sigma_tech = 0.012 # size of tech spread shocks - much jumpier than other debt
s0_other = 0.012 # other corporate spread today - 120 bps
theta_other = 0.013 # long-run other spread
kappa_other = 0.5 # speed other spreads are pulled back
sigma_other = 0.0065 # size of other spread shocks
ma_fraction = 0.5 # share of the bond spread allowed as matching adjustment

# Equities - GBM via the existing engine, volatilities and correlation from Yahoo Finance 2016-2025
mu_eq_tech = 0.085 # tech expected return - risk-free plus a 4.5% equity risk premium, not a historical average
sigma_eq_tech = 0.24 # tech volatility - XLK (US tech sector) 2016-2025 was 24.3%
mu_eq_other = 0.075 # non-tech expected return - risk-free plus 3.5% equity risk premium
sigma_eq_other = 0.16 # non-tech volatility - SPXT (S&P 500 ex-tech) 2016-2025 was 16.3%
rho_equity = 0.74 # correlation between tech and non-tech - XLK vs SPXT daily returns 2016-2025
tech_weight = 0.38 # share of equities in tech - S&P 500 tech sector weight, end June 2026

# Correlation between all five drivers - rows and columns in DRIVERS order:
# tech equity, non-tech equity, short rate, tech spread, other spread
# Positive equity-rate: shares down, rates down. Negative equity-spread: shares down, spreads wider
corr_matrix = [
    [ 1.00,  0.74,  0.50, -0.75, -0.60], # tech equity - 0.74 from Yahoo data, 0.5 and -0.75 from the standard formula
    [ 0.74,  1.00,  0.50, -0.60, -0.75], # non-tech equity
    [ 0.50,  0.50,  1.00, -0.50, -0.50], # short rate - rates fall when spreads widen, standard formula 0.5
    [-0.75, -0.60, -0.50,  1.00,  0.80], # tech spread - each bucket's equity links most to its own spread
    [-0.60, -0.75, -0.50,  0.80,  1.00], # other spread - spreads widen together
]

# Simulation
n_paths = 10_000 # number of simulated scenarios
seed = 42 # fixed so results are repeatable

# Starting capital
own_funds_ratio = 0.075 # cushion = 7.5% of liabilities - puts the modern insurer at a typical ~200% solvency ratio

# Everything above in one dict, so the balance sheet functions can take it in one go
p = dict(A=A, B=B, c=c, max_age=max_age, n_annuitants=n_annuitants, age_min=age_min, age_max=age_max,
         annual_payment=annual_payment, r0=r0, a=a, b=b, sigma_r=sigma_r,
         s0_tech=s0_tech, theta_tech=theta_tech, kappa_tech=kappa_tech, sigma_tech=sigma_tech,
         s0_other=s0_other, theta_other=theta_other, kappa_other=kappa_other, sigma_other=sigma_other,
         ma_fraction=ma_fraction, mu_eq_tech=mu_eq_tech, sigma_eq_tech=sigma_eq_tech, mu_eq_other=mu_eq_other,
         sigma_eq_other=sigma_eq_other, tech_weight=tech_weight, corr_matrix=np.array(corr_matrix),
         own_funds_ratio=own_funds_ratio)

# The two insurers - same liabilities and same cushion, different investments
modern = dict(
    gilt_weight=0.55, # share of assets in gilts
    corp_weight=0.40, # share in corporate bonds
    equity_weight=0.05, # share in shares
    gilt_maturity=9, # years - matched to the ~8.6-year liabilities
    corp_maturity=9,
    corp_tech_share=0.10, # share of corporate bonds lent to tech/data centres - roughly their index weight
)
style_1999 = dict(modern, gilt_weight=0.35, corp_weight=0.25, equity_weight=0.40) # same bonds, 40% in shares


# Slide 16 - same modern insurer, half its corporate bonds lent to tech/data centres
concentrated = dict(modern, corp_tech_share=0.50)

# The AI crash - applied instantly to today's balance sheet, no randomness
crash = dict(
    tech_shock=-0.50, # tech shares fall 50%
    other_shock=-0.20, # all other shares fall 20%
    rate_shock=-0.0075, # every gilt yield falls 0.75 points (75 bps) as investors flee to safety
    tech_spread_shock=0.03, # tech/data-centre spreads widen 3 points (300 bps) - the telecom story again
    other_spread_shock=0.01, # other corporate spreads widen 1 point (100 bps)
)


def apply_crash(bs0, portfolio, p, crash):
    """
    Own funds straight after an instant AI crash - every shock hits today's balance sheet at once.

    Parameters:
        bs0: today's balance sheet, from initial_balance_sheet
        portfolio: same dict used to build bs0
        p: dict of model parameters
        crash: dict of shocks - tech_shock, other_shock, rate_shock, tech_spread_shock, other_spread_shock

    Returns:
        after: dict of £ values after the crash - gilts, corp_tech, corp_other, equities, liabilities,
            own_funds - plus the new MA
    """
    vasicek = (p["a"], p["b"], p["sigma_r"])
    r0, shift = p["r0"], crash["rate_shock"]
    s1_tech = p["s0_tech"] + crash["tech_spread_shock"]
    s1_other = p["s0_other"] + crash["other_spread_shock"]

    # revalue each bond instantly (horizon 0) on the lower curve and wider spreads
    gilts = revalue_zcb(bs0["gilts"], portfolio["gilt_maturity"], r0, r0, *vasicek, horizon=0, shift=shift)
    corp_tech = revalue_corporate(bs0["corp_tech"], portfolio["corp_maturity"], r0, r0, p["s0_tech"], s1_tech, *vasicek, horizon=0, shift=shift)
    corp_other = revalue_corporate(bs0["corp_other"], portfolio["corp_maturity"], r0, r0, p["s0_other"], s1_other, *vasicek, horizon=0, shift=shift)

    # shares - the tech part and the rest fall by different amounts
    equities = bs0["equities"] * (p["tech_weight"] * (1 + crash["tech_shock"]) + (1 - p["tech_weight"]) * (1 + crash["other_shock"]))

    # liabilities on the lower curve, with the MA recalculated from the wider spreads
    ma = matching_adjustment([gilts, corp_tech, corp_other], [0.0, s1_tech, s1_other], p["ma_fraction"])
    df = zcb_price(r0, bs0["times"], *vasicek, shift=shift)
    liabilities = value_liabilities(bs0["cash_flows"], bs0["times"], df, ma)

    after = {"gilts": gilts, "corp_tech": corp_tech, "corp_other": corp_other, "equities": equities,
             "liabilities": liabilities, "ma": ma}
    after["own_funds"] = gilts + corp_tech + corp_other + equities - liabilities

    return after


def run_scenario(name, portfolio, p, crash, n_paths, seed):
    """
    Everything for one insurer - balance sheet, SCR, solvency ratio, then the AI crash.
    The SCR is held at its pre-crash value, so the ratio after = own funds after / SCR before.

    Parameters:
        name: label for the results table
        portfolio: dict of investment weights and bond details
        p: dict of model parameters
        crash: dict of crash shocks
        n_paths: number of simulated years for the SCR
        seed: random seed

    Returns:
        result: dict - name, own funds before and after, SCR, solvency ratio before and after,
            and where the crash loss came from (shares, bonds, liabilities)
    """
    bs0 = initial_balance_sheet(portfolio, p)
    of1, _ = simulate_own_funds(bs0, portfolio, p, n_paths, seed)
    scr, ratio_before = scr_and_ratio(bs0["own_funds"], of1)

    after = apply_crash(bs0, portfolio, p, crash)

    bonds_0 = bs0["gilts"] + bs0["corp_tech"] + bs0["corp_other"]
    bonds_1 = after["gilts"] + after["corp_tech"] + after["corp_other"]

    return {
        "name": name,
        "own_funds_before": bs0["own_funds"],
        "scr": scr,
        "ratio_before": ratio_before,
        "own_funds_after": after["own_funds"],
        "ratio_after": after["own_funds"] / scr, # SCR held fixed
        "loss_shares": bs0["equities"] - after["equities"], # positive = money lost
        "loss_bonds": bonds_0 - bonds_1,
        "loss_liabilities": after["liabilities"] - bs0["liabilities"], # liabilities going up is a loss
    }
