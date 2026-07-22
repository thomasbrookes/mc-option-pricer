# %%
import matplotlib.pyplot as plt
from var import portfolio_var, historical_var

# %%
# Portfolio VaR - four correlated stocks
S0s = [100, 50, 80, 30]           # current price of each stock
shares = [1, 2, 1.25, 3.33]       # roughly 100 worth of each stock to start
mu = [0.08, 0.06, 0.07, 0.05]     # growth rate of each stock
sigma = [0.2, 0.15, 0.25, 0.1]    # volatility of each stock
corr_matrix = [
    [1,   0.6, 0.3, 0.1],
    [0.6, 1,   0.4, 0.2],
    [0.3, 0.4, 1,   0.5],
    [0.1, 0.2, 0.5, 1  ],
] # correlation between each pair of stocks

port_var_95 = portfolio_var(S0s, shares, mu, sigma, corr_matrix, T=1, N=252, n_paths=10000, confidence=0.95)
print(f"95% 1-year portfolio VaR: {port_var_95:.2f}")
print(f"We're 95% confident we won't lose more than {port_var_95:.2f} on a 400 position over 1 year")

# %%
# Compare to treating all four stocks as if uncorrelated risk just adds up
individual_vars = [
    historical_var(S0=S0, mu=m, sigma=s, T=1, N=252, n_paths=10000, confidence=0.95) * sh
    for S0, sh, m, s in zip(S0s, shares, mu, sigma)
]
print(f"Sum of individual VaRs: {sum(individual_vars):.2f}")
print(f"Portfolio VaR (correlated): {port_var_95:.2f}")
# %%
