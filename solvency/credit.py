"""
Credit: corporate bonds = gilt price x an extra discount for the credit spread.

- Two spread buckets (tech/data-centre and other), each mean-reverting.
- Tech debt has a higher spread level and volatility.
- Simplified matching adjustment: a fraction of the bond portfolio's average spread.

Defaults and downgrades are out of scope - bonds only lose value through spreads widening.
"""
import numpy as np
from rates import simulate_short_rate, zcb_price


def simulate_spread(s0, kappa, theta, sigma, T, N, n_paths, dW=None):
    """
    Simulate credit spread paths - same maths as the Vasicek short rate, floored at zero.

    Parameters:
        s0: spread today, e.g. 0.012 for 1.2% (120 bps)
        kappa: speed the spread is pulled back to theta
        theta: long-run level the spread is pulled towards
        sigma: size of the random shocks to the spread
        T: time horizon in years
        N: steps to sim within that horizon
        n_paths: how many paths to sim
        dW: optional Brownian increments, shape (n_paths, N) - for correlation later

    Returns:
        spreads: shape (n_paths, N+1), first column is s0
    """
    spreads = simulate_short_rate(s0, kappa, theta, sigma, T, N, n_paths, dW) # same pull-back-plus-shocks process

    return np.maximum(spreads, 0.0) # a negative spread makes no sense, so stop it at zero


def corporate_bond_price(r, spread, tau, a, b, sigma_r, shift=0.0):
    """
    Value today of £1 paid by a company in tau years - gilt price with extra discounting for the spread.

    Parameters:
        r: short rate now - a number, or one per path
        spread: credit spread now - a number, or one per path (same shape as r)
        tau: years until payment
        a, b, sigma_r: Vasicek parameters
        shift: optional parallel shift to gilt yields

    Returns:
        price: same shape as zcb_price would give
    """
    spread = np.asarray(spread, dtype=float)
    tau = np.asarray(tau, dtype=float)

    spread = spread[..., None] if spread.ndim > 0 and tau.ndim > 0 else spread # one row per path, like zcb_price

    return zcb_price(r, tau, a, b, sigma_r, shift) * np.exp(-spread * tau) # corporate yield = gilt yield + spread


def revalue_corporate(market_value_0, maturity, r0, r1, s0, s1, a, b, sigma_r, horizon=1.0, shift=0.0):
    """
    Value at the horizon of a zero-coupon corporate bond bought today.

    Parameters:
        market_value_0: £ invested in the bond today
        maturity: years until the bond pays out, from today - must be at least the horizon
        r0, r1: short rate today and at the horizon (r1 can be one per path)
        s0, s1: spread today and at the horizon (s1 can be one per path)
        a, b, sigma_r: Vasicek parameters
        horizon: years until revaluation, 1 for the SCR
        shift: optional parallel shift to gilt yields at the horizon

    Returns:
        value: £ value of the bond at the horizon - a number, or one per path
    """
    assert maturity >= horizon, "bond must not mature before the horizon"

    face = market_value_0 / corporate_bond_price(r0, s0, maturity, a, b, sigma_r) # £ paid out at maturity

    return face * corporate_bond_price(r1, s1, maturity - horizon, a, b, sigma_r, shift) # less time left, new rates and spread


def matching_adjustment(bond_values, bond_spreads, ma_fraction):
    """
    Simplified matching adjustment - extra discount rate for the liabilities.
    A fraction of the bond portfolio's average spread, with gilts counting as zero spread.

    Parameters:
        bond_values: £ value of each bond bucket, e.g. [gilts, tech corporates, other corporates],
            shape (n_buckets,) or (n_paths, n_buckets)
        bond_spreads: spread of each bucket, same shape - gilts are 0
        ma_fraction: share of the spread allowed as MA - stands in for spread minus fundamental spread

    Returns:
        ma: extra discount rate - a number, or one per path
    """
    bond_values = np.asarray(bond_values, dtype=float)
    bond_spreads = np.asarray(bond_spreads, dtype=float)

    avg_spread = (bond_values * bond_spreads).sum(axis=-1) / bond_values.sum(axis=-1) # value-weighted average spread

    return ma_fraction * avg_spread
