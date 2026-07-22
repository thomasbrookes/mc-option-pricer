import numpy as np

def sim_path(S0, mu, sigma, T, N):
    dt = T / N
    prices = [S0]

    for _ in range(N):
        Z = np.random.normal() # Random shock is drawn from normal dist 
        S_prev = prices[-1] # Most recent step as starting point
        S_next = S_prev * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z) # GBM update - apply drift and the random shock / noise
        prices.append(S_next) # Stores new price

    return np.array(prices)

def sim_paths(S0, mu, sigma, T, N, n_paths):
    dt = T / N
    Z = np.random.normal(size=(n_paths, N)) # One random shock per path and time step

    increments = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z # GBM update - apply drift and the random shock / noise

    log_paths = np.cumsum(increments, axis=1) # Cumulative sum of increments to get log prices because prices multiply and log prices add
    log_paths = np.hstack((np.zeros((n_paths, 1)), log_paths)) # Add initial price (log(1) = 0) to the beginning of each path

    prices = S0 * np.exp(log_paths) # Convert log prices back to actual prices

    return prices

def sim_correlated_paths(S0s, mu, sigma, corr_matrix, T, N, n_paths):
    """
    Sim correlated GBM paths for multiple assets.

    Parameters:
        S0s: current price of each asset
        mu: growth rate of each asset
        sigma: volatility of each asset
        corr_matrix: correlation between each pair of assets
        T: time horizon in years
        N: steps to sim within that horizon
        n_paths: how many paths to sim

    Returns:
        prices: shape (n_paths, N+1, n_assets)
    """
    n_assets = len(S0s)
    dt = T / N

    S0s = np.array(S0s)
    mu = np.array(mu)
    sigma = np.array(sigma)

    L = np.linalg.cholesky(corr_matrix) # cholesky factor - turns independent shocks into correlated ones

    Z = np.random.normal(size=(n_paths, N, n_assets)) # independent shock per path, step, and asset
    Z_corr = Z @ L.T # correlate the shocks across assets at each step

    increments = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z_corr # GBM update, per asset

    log_paths = np.cumsum(increments, axis=1) # cumulative log return over time, per asset
    log_paths = np.concatenate([np.zeros((n_paths, 1, n_assets)), log_paths], axis=1) # add t=0 row

    prices = S0s * np.exp(log_paths) # convert back to price, per asset

    return prices