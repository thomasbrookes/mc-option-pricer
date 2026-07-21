# %%
import matplotlib.pyplot as plt
from var import historical_var

# %%
# Single stock VaR - how much could we lose on this stock over 1 year?
# Use mu here, not r - VaR is about real-world risk, not risk-neutral pricing
mu = 0.08 # our real-world growth assumption
var_95 = historical_var(S0=100, mu=mu, sigma=0.2, T=1, N=252, n_paths=10000, confidence=0.95)
print(f"95% 1-year VaR: {var_95:.2f}")
print(f"We're 95% confident we won't lose more than {var_95:.2f} on a 100 position over 1 year")
# %%
