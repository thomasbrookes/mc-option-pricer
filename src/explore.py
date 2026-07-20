# %%
import matplotlib.pyplot as plt
from gbm import sim_path, sim_paths

# %%
paths = sim_paths(S0=100, mu=0.05, sigma=0.2, T=1, N=252, n_paths=10000)
print(paths.shape) 

# %%
# Plot a sample of 50 paths (plotting all 10,000 would be unreadable)
for i in range(50):
    plt.plot(paths[i], linewidth=0.7, alpha=0.6)
plt.xlabel("Day")
plt.ylabel("Simulated Price")
plt.title("50 of 10,000 Simulated GBM Paths")
plt.show()
# %%
