# %%
import numpy as np
from market_data import get_stock_params, get_corr_matrix
from var import historical_var, portfolio_var

# %%
# Get real S0, mu, sigma for a single stock and feed straight into historical_var - unchanged
S0, mu, sigma = get_stock_params("AAPL", start="2023-01-01", end="2026-01-01")
print(f"AAPL - S0: {S0:.2f}, mu: {mu:.4f}, sigma: {sigma:.4f}")

expected_price = S0 * np.exp(mu * 1) # theoretical expected price in 1 year, given the drift mu
print(f"Expected price in 1 year: {expected_price:.2f}")

var_95, es_95 = historical_var(S0=S0, mu=mu, sigma=sigma, T=1, N=252, n_paths=10000, confidence=0.95)
print(f"95% 1-year VaR: {var_95:.2f}")
print(f"95% 1-year Expected Shortfall: {es_95:.2f}")

# %%
# Real S0/mu/sigma/correlation across a few stocks, fed into portfolio_var - also unchanged
tickers = ["AAPL", "MSFT", "XOM"]
start, end = "2023-01-01", "2026-01-01"

S0s, mus, sigmas = [], [], []
for ticker in tickers:
    s0, m, sig = get_stock_params(ticker, start=start, end=end)
    S0s.append(s0)
    mus.append(m)
    sigmas.append(sig)

corr_matrix = get_corr_matrix(tickers, start=start, end=end).values # correlation between the 3 stocks
shares = [1, 1, 1] # 1 share of each, just to demo

expected_value = sum(sh * s0 * np.exp(m * 1) for sh, s0, m in zip(shares, S0s, mus)) # expected value of each holding, summed - correlation doesn't affect this, only spread does
print(f"Expected portfolio value in 1 year: {expected_value:.2f}")

port_var_95, port_es_95 = portfolio_var(S0s, shares, mus, sigmas, corr_matrix, T=1, N=252, n_paths=10000, confidence=0.95)
print(f"95% 1-year portfolio VaR: {port_var_95:.2f}")
print(f"95% 1-year portfolio Expected Shortfall: {port_es_95:.2f}")
# %%
