import numpy as np
from scipy.stats import norm
from gbm import sim_paths

def black_scholes_call(S0, K, r, sigma, T):
    #  Calculate the Black-Scholes price of a European call option.

    d1 = (np.log(S0 / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))  # standardised "moneyness" adjusted for drift and time
    d2 = d1 - sigma * np.sqrt(T)  # same as d1, shifted to account for volatility over the full period

    price = S0 * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)  # weighted difference between expected stock value and discounted strike

    return d1, d2, price


def bs_delta(S0, K, r, sigma, T):
    # closed-form delta for a call - price change per 1 unit change in S0

    d1, _, _ = black_scholes_call(S0, K, r, sigma, T)

    return norm.cdf(d1)


def bs_vega(S0, K, r, sigma, T):
    # closed-form vega - price change per 1 unit change in sigma

    d1, _, _ = black_scholes_call(S0, K, r, sigma, T)

    return S0 * np.sqrt(T) * norm.pdf(d1)


def bs_rho(S0, K, r, sigma, T):
    # closed-form rho for a call - price change per 1 unit change in r

    _, d2, _ = black_scholes_call(S0, K, r, sigma, T)

    return K * T * np.exp(-r * T) * norm.cdf(d2)


def bs_theta(S0, K, r, sigma, T, N):
    # closed-form theta for a call - value lost per day, to match mc theta's convention

    d1, d2, _ = black_scholes_call(S0, K, r, sigma, T)

    theta_per_year = -(S0 * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)

    return theta_per_year / N # convert to per day


def mc_call_price(S0, K, r, sigma, T, N, n_paths):
    # Estimate the price of a European call option using Monte Carlo simulation.

    paths = sim_paths(S0, r, sigma, T, N, n_paths)

    S_T = paths[:, -1] # Get the final prices at maturity
    payoffs = np.maximum(S_T - K, 0) # Calculate the payoffs for call option
    price = np.exp(-r * T) * payoffs.mean() # Discount the average payoff back to present value

    return price

