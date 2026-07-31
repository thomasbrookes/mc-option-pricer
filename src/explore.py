# %%
from greeks import delta, vega, rho, theta

# %%
# Greeks for a European call, via bump-and-revalue
S0, K, r, sigma, T, N, n_paths = 100, 100, 0.05, 0.2, 1, 252, 10000

print(f"Delta: {delta(S0, K, r, sigma, T, N, n_paths):.4f}")
print(f"Vega: {vega(S0, K, r, sigma, T, N, n_paths):.4f}")
print(f"Rho: {rho(S0, K, r, sigma, T, N, n_paths):.4f}")
print(f"Theta: {theta(S0, K, r, sigma, T, N, n_paths):.4f}")
# %%
