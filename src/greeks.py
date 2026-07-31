import numpy as np
from option_pricer import mc_call_price

def delta(S0, K, r, sigma, T, N, n_paths, h=1):
    """
    Estimate Delta via bump-and-revalue - price sensitivity to the stock price.

    Parameters:
        S0, K, r, sigma, T, N, n_paths: same as mc_call_price
        h: size of the bump to S0

    Returns:
        delta: estimated price change per 1 unit change in S0
    """
    seed = 42 # fix the seed so both prices use identical random draws - isolates the effect of the bump

    np.random.seed(seed)
    price_up = mc_call_price(S0 + h, K, r, sigma, T, N, n_paths) # price with stock bumped up

    np.random.seed(seed) # reset to the same draws
    price_down = mc_call_price(S0 - h, K, r, sigma, T, N, n_paths) # price with stock bumped down

    return (price_up - price_down) / (2 * h) # central difference

def vega(S0, K, r, sigma, T, N, n_paths, h=0.01):
    """
    Estimate Vega via bump-and-revalue - price sensitivity to volatility.

    Parameters:
        S0, K, r, sigma, T, N, n_paths: same as mc_call_price
        h: size of the bump to sigma

    Returns:
        vega: estimated price change per 1 unit change in sigma
    """
    seed = 42

    np.random.seed(seed)
    price_up = mc_call_price(S0, K, r, sigma + h, T, N, n_paths) # price with vol bumped up

    np.random.seed(seed)
    price_down = mc_call_price(S0, K, r, sigma - h, T, N, n_paths) # price with vol bumped down

    return (price_up - price_down) / (2 * h)

def rho(S0, K, r, sigma, T, N, n_paths, h=0.0001):
    """
    Estimate Rho via bump-and-revalue - price sensitivity to the risk-free rate.

    Parameters:
        S0, K, r, sigma, T, N, n_paths: same as mc_call_price
        h: size of the bump to r

    Returns:
        rho: estimated price change per 1 unit change in r
    """
    seed = 42

    np.random.seed(seed)
    price_up = mc_call_price(S0, K, r + h, sigma, T, N, n_paths) # price with rate bumped up

    np.random.seed(seed)
    price_down = mc_call_price(S0, K, r - h, sigma, T, N, n_paths) # price with rate bumped down

    return (price_up - price_down) / (2 * h)

def theta(S0, K, r, sigma, T, N, n_paths, h=1/252):
    """
    Estimate Theta via bump-and-revalue - value lost as one day passes.

    Parameters:
        S0, K, r, sigma, T, N, n_paths: same as mc_call_price
        h: size of the time step removed from T, default 1 trading day

    Returns:
        theta: price change from h less time to maturity - usually negative
    """
    seed = 42

    np.random.seed(seed)
    price_now = mc_call_price(S0, K, r, sigma, T, N, n_paths) # price with full time left

    np.random.seed(seed)
    price_later = mc_call_price(S0, K, r, sigma, T - h, N, n_paths) # price with h less time left

    return price_later - price_now
