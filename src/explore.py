# %%
from var import historical_var

# %%
# Single stock VaR and Expected Shortfall
var_95, es_95 = historical_var(S0=100, mu=0.08, sigma=0.2, T=1, N=252, n_paths=10000, confidence=0.95)
print(f"95% 1-year VaR: {var_95:.2f}")
print(f"95% 1-year Expected Shortfall: {es_95:.2f}")
print(f"We're 95% confident we won't lose more than {var_95:.2f}, but if we do, we'd expect to lose {es_95:.2f} on average")
# %%
