import numpy as np
from scipy.stats import norm
from gbm import sim_paths

def black_scholes_call(S0, K, r, sigma, T):
    #  Calculate the Black-Scholes price of a European call option.
    
    d1 = (np.log(S0 / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))  # standardised "moneyness" adjusted for drift and time
    d2 = d1 - sigma * np.sqrt(T)  # same as d1, shifted to account for volatility over the full period

    price = S0 * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)  # weighted difference between expected stock value and discounted strike
    
    return price


def mc_call_price(S0, K, r, sigma, T, N, n_paths):
    # Estimate the price of a European call option using Monte Carlo simulation.

    paths = sim_paths(S0, r, sigma, T, N, n_paths)

    S_T = paths[:, -1] # Get the final prices at maturity
    payoffs = np.maximum(S_T - K, 0) # Calculate the payoffs for call option
    price = np.exp(-r * T) * payoffs.mean() # Discount the average payoff back to present value

    return price

