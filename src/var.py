import numpy as np
from gbm import sim_paths

def historical_var(S0, mu, sigma, T, N, n_paths, confidence=0.95):
    """
    Estimate VaR for a single stock using mc sim

    Parameters:
        S0: Current price
        mu: Real-world growth rate, not risk-neutral
        sigma: Volatility
        T: Time horizon in years
        N: Steps to sim within that horizon
        n_paths: How many paths to sim
        confidence: Confidence level, e.g. 0.95 for 95% VaR

    Returns:
        var: Loss we don't expect to exceed, e.g. 95% of time at 0.95 confidence
    """
    paths = sim_paths(S0, mu, sigma, T, N, n_paths) # sim many future price paths

    S_T = paths[:, -1] # final price of each path
    pnl = S_T - S0 # profit/loss per path, negative = loss

    losses = -pnl # flip sign so positive = loss

    var = np.percentile(losses, confidence * 100) # loss at the cutoff percentile

    return var
