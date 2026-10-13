"""
Interest rates: Vasicek short-rate model, dr = a(b - r)dt + sigma dW.

- Simulates the short rate over one year.
- Closed-form zero-coupon bond price used to value gilts and discount liabilities.
"""
import numpy as np


def simulate_short_rate(r0, a, b, sigma, T, N, n_paths, dW=None):
    """
    Simulate Vasicek short rate paths - the rate gets pulled towards b, plus random shocks.

    Parameters:
        r0: short rate today, e.g. 0.0375 for 3.75%
        a: speed the rate is pulled back to b - higher = faster
        b: long-run level the rate is pulled towards
        sigma: size of the random shocks to the rate
        T: time horizon in years
        N: steps to sim within that horizon
        n_paths: how many paths to sim
        dW: optional Brownian increments, shape (n_paths, N) - lets the shocks be
            correlated with equities and spreads later. Drawn fresh if not given

    Returns:
        rates: shape (n_paths, N+1), first column is r0
    """
    dt = T / N

    if dW is None:
        dW = np.random.normal(size=(n_paths, N)) * np.sqrt(dt) # one random shock per path and time step

    rates = np.empty((n_paths, N + 1))
    rates[:, 0] = r0

    for i in range(N): # loop over time steps only, all paths at once
        r = rates[:, i]
        rates[:, i + 1] = r + a * (b - r) * dt + sigma * dW[:, i] # pull towards b, plus a random shock

    return rates


def zcb_price(r, tau, a, b, sigma, shift=0.0):
    """
    Closed-form Vasicek price of a zero-coupon bond - value today of £1 paid in tau years.

    Parameters:
        r: short rate now - a number, or one per path, shape (n_paths,)
        tau: years until payment - a number, or shape (n_times,)
        a, b, sigma: Vasicek parameters
        shift: optional parallel shift to every yield, e.g. -0.0075 for a 0.75 point fall

    Returns:
        price: shape (n_paths, n_times) if r and tau are both arrays, otherwise follows whichever is an array
    """
    r = np.asarray(r, dtype=float)
    tau = np.asarray(tau, dtype=float)

    B = (1 - np.exp(-a * tau)) / a # how much the bond price reacts to the short rate
    A = (b - sigma**2 / (2 * a**2)) * (B - tau) - sigma**2 * B**2 / (4 * a) # the rest of the formula, doesn't depend on r

    r = r[..., None] if r.ndim > 0 and tau.ndim > 0 else r # one row per path, one column per payment time

    return np.exp(A - B * r - shift * tau)


def zero_yield(r, tau, a, b, sigma, shift=0.0):
    """
    Interest rate earned on a zero-coupon bond held to maturity - the yield curve.

    Parameters:
        r, tau, a, b, sigma, shift: same as zcb_price

    Returns:
        yields: continuously compounded yield for each maturity
    """
    return -np.log(zcb_price(r, tau, a, b, sigma, shift)) / np.asarray(tau, dtype=float)


def revalue_zcb(market_value_0, maturity, r0, r1, a, b, sigma, horizon=1.0, shift=0.0):
    """
    Value at the horizon of a zero-coupon bond bought today - used for gilts.

    Parameters:
        market_value_0: £ invested in the bond today
        maturity: years until the bond pays out, from today - must be at least the horizon
        r0: short rate today
        r1: short rate at the horizon - a number, or one per path
        a, b, sigma: Vasicek parameters
        horizon: years until revaluation, 1 for the SCR
        shift: optional parallel shift to yields at the horizon

    Returns:
        value: £ value of the bond at the horizon - a number, or one per path
    """
    assert maturity >= horizon, "bond must not mature before the horizon"

    face = market_value_0 / zcb_price(r0, maturity, a, b, sigma) # £ paid out at maturity

    return face * zcb_price(r1, maturity - horizon, a, b, sigma, shift) # same bond, now with less time left on a new curve
