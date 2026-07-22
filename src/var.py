import numpy as np
from gbm import sim_paths, sim_correlated_paths

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

def portfolio_var(S0s, shares, mu, sigma, corr_matrix, T, N, n_paths, confidence=0.95):
    """
    Estimate VaR for a portfolio of correlated stocks using mc sim.

    Parameters:
        S0s: current price of each stock
        shares: how many shares held of each stock
        mu: growth rate of each stock
        sigma: volatility of each stock
        corr_matrix: correlation between each pair of stocks
        T: time horizon in years
        N: steps to sim within that horizon
        n_paths: how many paths to sim
        confidence: confidence level, e.g. 0.95 for 95% VaR

    Returns:
        var: loss we don't expect the portfolio to exceed, e.g. 95% of time at 0.95 confidence
    """
    paths = sim_correlated_paths(S0s, mu, sigma, corr_matrix, T, N, n_paths) # shape (n_paths, N+1, n_assets)

    S_T = paths[:, -1, :] # final price of each stock, per path
    portfolio_value = S_T @ np.array(shares) # total portfolio value per path

    V0 = np.array(S0s) @ np.array(shares) # starting portfolio value
    pnl = portfolio_value - V0 # profit/loss per path, negative = loss

    losses = -pnl # flip sign so positive = loss

    var = np.percentile(losses, confidence * 100) # loss at the cutoff percentile

    return var
