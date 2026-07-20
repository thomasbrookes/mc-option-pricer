# %%
import matplotlib.pyplot as plt
from gbm import simulate_path

# %%
path = simulate_path(S0=100, mu=0.05, sigma=0.2, T=1, N=252)

# %%

plt.plot(path)
plt.xlabel('Time')
plt.ylabel('Price')
plt.title('GBM Path Sim')
plt.show()
# %%
