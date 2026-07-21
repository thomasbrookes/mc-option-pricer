# %%
import matplotlib.pyplot as plt
from option_pricer import black_scholes_call, mc_call_price

# %%
# Option and market parameters used for both pricing methods
S0 = 100    # Current stock price
K = 100     # Strike price
r = 0.05    # Risk-free rate - used as the MC drift for risk-neutral pricing
sigma = 0.2 # Volatility
T = 1       # Time to maturity in years
N = 252     # Trading days simulated per path

bs_price = black_scholes_call(S0, K, r, sigma, T)
print(f"Black-Scholes price: {bs_price:.4f}")

# %%
# Check that the MC price converges towards the Black-Scholes price as n_paths grows
for n_paths in [1000, 10000, 100000]:
    mc_price = mc_call_price(S0, K, r, sigma, T, N, n_paths)  # Re-simulate at each path count
    gap = abs(mc_price - bs_price)  # Absolute pricing error vs closed-form
    print(f"n_paths={n_paths:>7,}: MC price = {mc_price:.4f}, gap = {gap:.4f}")
# %%
