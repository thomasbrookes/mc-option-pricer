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