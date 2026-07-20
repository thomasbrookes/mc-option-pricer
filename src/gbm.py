import numpy as np

def simulate_path(S0, mu, sigma, T, N):
    dt = T / N
    prices = [S0]

    for _ in range(N):
        Z = np.random.normal() # Random shock is drawn from normal dist 
        S_prev = prices[-1] # Most recent step as starting point
        S_next = S_prev * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z) # GBM update - apply drift and the random shock / noise
        prices.append(S_next) # Stores new price

    return np.array(prices)