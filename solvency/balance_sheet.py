"""
Balance sheet and capital.

- Own funds = assets - liabilities, at t=0 and in each simulated scenario at t=1.
- SCR = own funds at t=0 - 1-in-200 worst own funds at t=1 (discounted back).
- Solvency ratio = own funds / SCR.

Parameters are passed around as two plain dicts:
- p: the model parameters (mortality, rates, spreads, equities, correlation, simulation)
- portfolio: how the insurer invests - weights, bond maturities, tech share of corporate bonds
"""
import numpy as np
from liabilities import project_cash_flows, value_liabilities
from rates import simulate_short_rate, zcb_price, revalue_zcb
from credit import simulate_spread, revalue_corporate, matching_adjustment
from equities import simulate_all_drivers, revalue_equities


def initial_balance_sheet(portfolio, p):
    """
    The insurer's balance sheet today.

    Parameters:
        portfolio: dict with gilt_weight, corp_weight, equity_weight (sum to 1), gilt_maturity,
            corp_maturity, corp_tech_share (share of corporate bonds lent to tech/data centres)
        p: dict of model parameters

    Returns:
        bs: dict of £ values - liabilities, gilts, corp_tech, corp_other, equities, invested,
            own_funds - plus the cash flows and MA used
    """
    weights = portfolio["gilt_weight"] + portfolio["corp_weight"] + portfolio["equity_weight"]
    assert np.isclose(weights, 1.0), "gilt, corporate and equity weights must add up to 1"

    times, cash_flows = project_cash_flows(p["n_annuitants"], p["age_min"], p["age_max"], p["annual_payment"],
                                           p["A"], p["B"], p["c"], p["max_age"])

    # MA only depends on the bond mix, not the £ amount, so work it out from the weights
    corp = portfolio["corp_weight"]
    bond_mix = [portfolio["gilt_weight"], corp * portfolio["corp_tech_share"], corp * (1 - portfolio["corp_tech_share"])]
    ma = matching_adjustment(bond_mix, [0.0, p["s0_tech"], p["s0_other"]], p["ma_fraction"])

    df = zcb_price(p["r0"], times, p["a"], p["b"], p["sigma_r"]) # today's gilt curve
    liabilities = value_liabilities(cash_flows, times, df, ma)

    invested = liabilities * (1 + p["own_funds_ratio"]) # enough to pay every pension, plus a cushion

    bs = {
        "times": times,
        "cash_flows": cash_flows,
        "ma": ma,
        "liabilities": liabilities,
        "gilts": invested * portfolio["gilt_weight"],
        "corp_tech": invested * bond_mix[1],
        "corp_other": invested * bond_mix[2],
        "equities": invested * portfolio["equity_weight"],
        "invested": invested,
    }
    bs["own_funds"] = invested - liabilities

    return bs


def simulate_own_funds(bs0, portfolio, p, n_paths, seed):
    """
    Own funds after one simulated year, in each scenario, discounted back to today.

    Parameters:
        bs0: today's balance sheet, from initial_balance_sheet
        portfolio: same dict used to build bs0
        p: dict of model parameters
        n_paths: number of simulated years
        seed: random seed, so results are repeatable

    Returns:
        own_funds_1: £ own funds at t=1 discounted to today, one per path
        detail: dict of £ values at t=1 per path - gilts, corp_tech, corp_other, equities,
            liabilities - plus r1, s1_tech, s1_other, for checking what drove each result
    """
    N = 12 # monthly steps over the year
    np.random.seed(seed)

    # one engine call moves every risk together, then rates and spreads are built from its shocks
    growth, dW = simulate_all_drivers(p["mu_eq_tech"], p["sigma_eq_tech"], p["mu_eq_other"], p["sigma_eq_other"],
                                      p["corr_matrix"], 1, N, n_paths)
    r1 = simulate_short_rate(p["r0"], p["a"], p["b"], p["sigma_r"], 1, N, n_paths, dW[:, :, 0])[:, -1]
    s1_tech = simulate_spread(p["s0_tech"], p["kappa_tech"], p["theta_tech"], p["sigma_tech"], 1, N, n_paths, dW[:, :, 1])[:, -1]
    s1_other = simulate_spread(p["s0_other"], p["kappa_other"], p["theta_other"], p["sigma_other"], 1, N, n_paths, dW[:, :, 2])[:, -1]

    # revalue every asset on that year's rates, spreads and share prices
    vasicek = (p["a"], p["b"], p["sigma_r"])
    gilts = revalue_zcb(bs0["gilts"], portfolio["gilt_maturity"], p["r0"], r1, *vasicek)
    corp_tech = revalue_corporate(bs0["corp_tech"], portfolio["corp_maturity"], p["r0"], r1, p["s0_tech"], s1_tech, *vasicek)
    corp_other = revalue_corporate(bs0["corp_other"], portfolio["corp_maturity"], p["r0"], r1, p["s0_other"], s1_other, *vasicek)
    equities = revalue_equities(bs0["equities"], p["tech_weight"], growth)

    # the year-1 pension payment comes out of assets
    invested = gilts + corp_tech + corp_other + equities - bs0["cash_flows"][0]

    # remaining promises, one year closer, on each scenario's new curve and new MA
    times_left = bs0["times"][1:] - 1
    df1 = zcb_price(r1, times_left, *vasicek) # shape (n_paths, n_times)
    ma1 = matching_adjustment(np.column_stack([gilts, corp_tech, corp_other]),
                              np.column_stack([np.zeros(n_paths), s1_tech, s1_other]), p["ma_fraction"])
    liabilities = value_liabilities(bs0["cash_flows"][1:], times_left, df1, ma1)

    own_funds_1 = invested - liabilities
    own_funds_1 = own_funds_1 * zcb_price(p["r0"], 1, *vasicek) # discount back to today with the 1-year gilt price

    detail = {"gilts": gilts, "corp_tech": corp_tech, "corp_other": corp_other, "equities": equities,
              "liabilities": liabilities, "r1": r1, "s1_tech": s1_tech, "s1_other": s1_other}

    return own_funds_1, detail


def scr_and_ratio(own_funds_0, own_funds_1, percentile=0.5):
    """
    SCR and solvency ratio from the simulated own funds.

    Parameters:
        own_funds_0: £ own funds today
        own_funds_1: £ own funds after one year, discounted back, one per path
        percentile: 0.5 for the 1-in-200 Solvency II standard

    Returns:
        scr: £ loss of own funds in the 1-in-200 worst year
        ratio: own funds / SCR, e.g. 1.8 for 180%
    """
    scr = own_funds_0 - np.percentile(own_funds_1, percentile) # how far own funds fall in the 1-in-200 year

    return scr, own_funds_0 / scr
