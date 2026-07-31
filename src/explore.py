# %%
from greeks import delta, vega, rho, theta
from option_pricer import bs_delta, bs_vega, bs_rho, bs_theta

# %%
# Greeks for a European call - MC bump-and-revalue vs closed-form Black-Scholes
S0, K, r, sigma, T, N, n_paths = 100, 100, 0.05, 0.2, 1, 252, 10000

mc_vals = {
    "Delta": delta(S0, K, r, sigma, T, N, n_paths),
    "Vega": vega(S0, K, r, sigma, T, N, n_paths),
    "Rho": rho(S0, K, r, sigma, T, N, n_paths),
    "Theta": theta(S0, K, r, sigma, T, N, n_paths),
}
bs_vals = {
    "Delta": bs_delta(S0, K, r, sigma, T),
    "Vega": bs_vega(S0, K, r, sigma, T),
    "Rho": bs_rho(S0, K, r, sigma, T),
    "Theta": bs_theta(S0, K, r, sigma, T, N),
}

for name in mc_vals:
    print(f"{name}: MC = {mc_vals[name]:.4f}, Black-Scholes = {bs_vals[name]:.4f}")
# %%
