"""
Equities: two buckets (tech/AI and non-tech), simulated with the existing GBM engine.

Wraps sim_correlated_paths from src/gbm.py - the option pricer itself is not changed.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src")) # let us import the option pricer's engine from src/
from gbm import sim_correlated_paths


def simulate_equity_growth(mu_tech, sigma_tech, mu_other, sigma_other, rho, T, N, n_paths):
    """
    Simulate how much £1 in tech and £1 in non-tech shares grows to, using the existing GBM engine.

    Parameters:
        mu_tech, sigma_tech: real-world growth rate and volatility of tech shares
        mu_other, sigma_other: same for non-tech shares
        rho: correlation between tech and non-tech share returns
        T: time horizon in years
        N: steps to sim within that horizon
        n_paths: how many paths to sim

    Returns:
        growth: value at T of £1 invested today, shape (n_paths, 2) - column 0 tech, column 1 non-tech
    """
    corr_matrix = np.array([[1.0, rho], [rho, 1.0]]) # tech and non-tech move together, but not in lockstep

    paths = sim_correlated_paths([1.0, 1.0], [mu_tech, mu_other], [sigma_tech, sigma_other], corr_matrix, T, N, n_paths) # start both at £1

    return paths[:, -1, :] # only the value at the end of the horizon matters for the SCR


def simulate_all_drivers(mu_tech, sigma_tech, mu_other, sigma_other, corr_matrix, T, N, n_paths):
    """
    One call to the existing GBM engine that moves all five risk drivers together.

    Columns 0-1 are the real tech and non-tech share prices. Columns 2-4 (rate, tech spread,
    other spread) are given S0=1, mu=0.5, sigma=1 - the drift (mu - 0.5*sigma^2) is then zero,
    so log price is just a correlated random walk, and its monthly changes are the shocks dW
    that drive the Vasicek rate and the two spreads.

    Parameters:
        mu_tech, sigma_tech, mu_other, sigma_other: share growth rates and volatilities
        corr_matrix: correlation between all five drivers, shape (5, 5) in correlation.DRIVERS order
        T: time horizon in years
        N: steps to sim within that horizon
        n_paths: how many paths to sim

    Returns:
        growth: value at T of £1 in tech and non-tech shares, shape (n_paths, 2)
        dW: correlated shocks for rate, tech spread, other spread, shape (n_paths, N, 3)
    """
    S0s = [1.0, 1.0, 1.0, 1.0, 1.0]
    mus = [mu_tech, mu_other, 0.5, 0.5, 0.5] # 0.5 cancels the -0.5*sigma^2 term for the last three
    sigmas = [sigma_tech, sigma_other, 1.0, 1.0, 1.0] # unit volatility = plain random walk

    paths = sim_correlated_paths(S0s, mus, sigmas, corr_matrix, T, N, n_paths) # shape (n_paths, N+1, 5)

    growth = paths[:, -1, :2] # share prices at the end of the horizon
    dW = np.diff(np.log(paths[:, :, 2:]), axis=1) # monthly change in each random walk = the shock that month

    return growth, dW


def revalue_equities(equity_value_0, tech_weight, growth):
    """
    Value of the insurer's equity holding after the simulated growth.

    Parameters:
        equity_value_0: £ in equities today
        tech_weight: share of the equities in tech, e.g. 0.38
        growth: output of simulate_equity_growth, shape (n_paths, 2)

    Returns:
        value: £ value of the equities, one per path
    """
    weights = np.array([tech_weight, 1 - tech_weight]) # split between tech and non-tech

    return equity_value_0 * (growth @ weights) # each bucket grows at its own rate, then add them up
