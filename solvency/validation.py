"""
Sanity checks, run as # %% cells:
- Vasicek bond prices match the closed-form formula
- All volatilities set to zero -> SCR approximately zero
- Falling rates increase liabilities; long bonds offset this better than short bonds
- Equity-heavy SCR > bond-heavy SCR

Each check is added alongside the step that makes it possible.
"""
# %%
import numpy as np
import matplotlib.pyplot as plt
from liabilities import survival_prob, project_cash_flows, flat_discount_factors, value_liabilities, liability_duration
from rates import simulate_short_rate, zcb_price, zero_yield, revalue_zcb

# %%
# Parameters - defaults and sources are in ASSUMPTIONS.md

# Gompertz-Makeham mortality, death rate at age x = A + B * c**x
A = 0.00022 # age-independent part - accidents, illness that hit any age equally
B = 2.7e-6 # size of the age-related part
c = 1.124 # how fast death rates grow with age - roughly 12% higher each year older
max_age = 120 # nobody is assumed to live past this age

# The annuity block
n_annuitants = 10_000 # number of pensioners
age_min = 60 # youngest pensioner
age_max = 90 # oldest pensioner - spread evenly across ages age_min..age_max
annual_payment = 10_000 # £ paid to each pensioner per year, at the end of each year they're alive

# Vasicek interest rates, dr = a(b - r)dt + sigma dW
r0 = 0.0375 # short rate today - roughly the Bank of England base rate
a = 0.15 # speed the rate is pulled back to b - about 15% of the gap closes each year
b = 0.05 # long-run level the short rate is pulled towards
sigma_r = 0.01 # size of the random shocks - about 1 percentage point a year

# Simulation
n_paths = 10_000 # number of simulated scenarios
seed = 42 # fixed so results are repeatable

# %%
# Liabilities 1: life expectancy should look realistic
# ONS period life expectancy at 65 is roughly 18.5 (men) to 21 (women) years
times = np.arange(1, max_age - 65 + 1)
life_exp_65 = survival_prob([65], times, A, B, c).sum() + 0.5 # curtate expectation + half a year
print(f"Life expectancy at 65: {life_exp_65:.1f} years")
assert 17 < life_exp_65 < 25

# %%
# Liabilities 2: survival should only go down over time, and older people should survive less
tpx = survival_prob([60, 75, 90], np.arange(1, 31), A, B, c)
assert np.all(np.diff(tpx, axis=1) < 0) # each age group shrinks every year
assert np.all(tpx[0] > tpx[1]) and np.all(tpx[1] > tpx[2]) # 60 year olds outlive 75s, who outlive 90s
print("Survival probabilities behave sensibly")

# %%
# Liabilities 3: expected cash flows - start near n_annuitants x payment, then shrink as people die
times, cash_flows = project_cash_flows(n_annuitants, age_min, age_max, annual_payment, A, B, c, max_age)
print(f"Year 1 payments: £{cash_flows[0] / 1e6:.1f}m (max possible £{n_annuitants * annual_payment / 1e6:.1f}m)")
assert cash_flows[0] < n_annuitants * annual_payment
assert np.all(np.diff(cash_flows) <= 0)

plt.figure(figsize=(8, 4))
plt.bar(times, cash_flows / 1e6)
plt.xlabel("Years from now")
plt.ylabel("Expected payment (£m)")
plt.title("Expected annuity payments")
plt.show()

# %%
# Liabilities 4: falling rates make the liabilities more expensive
for rate in [0.05, 0.04, 0.03]:
    df = flat_discount_factors(rate, times)
    value = value_liabilities(cash_flows, times, df)
    duration = liability_duration(cash_flows, times, df)
    print(f"Rate {rate:.0%}: liabilities £{value / 1e6:,.0f}m, duration {duration:.1f} years")

values = [value_liabilities(cash_flows, times, flat_discount_factors(r, times)) for r in [0.05, 0.04, 0.03]]
assert values[0] < values[1] < values[2]

# %%
# Liabilities 5: a matching adjustment discounts at a higher rate, so it lowers the value
df = flat_discount_factors(0.04, times)
no_ma = value_liabilities(cash_flows, times, df)
with_ma = value_liabilities(cash_flows, times, df, ma=0.01)
print(f"No MA: £{no_ma / 1e6:,.0f}m, with 1% MA: £{with_ma / 1e6:,.0f}m")
assert with_ma < no_ma

# %%
# Liabilities 6: valuing many curves at once gives the same answer as one at a time
df_many = np.vstack([flat_discount_factors(r, times) for r in [0.05, 0.04, 0.03]]) # shape (3, n_times)
assert np.allclose(value_liabilities(cash_flows, times, df_many), values)
print("All liability checks passed")

# %%
# Rates 1: yield curve today - should slope gently upwards from r0
maturities = np.array([1, 2, 5, 10, 15, 20, 30])
yields = zero_yield(r0, maturities, a, b, sigma_r)
for mat, y in zip(maturities, yields):
    print(f"{mat:>2}-year gilt yield: {y:.2%}")
assert np.all(np.diff(yields) > 0)

curve_t = np.linspace(0.5, 40, 80)
plt.figure(figsize=(8, 4))
plt.plot(curve_t, zero_yield(r0, curve_t, a, b, sigma_r) * 100)
plt.xlabel("Maturity (years)")
plt.ylabel("Yield (%)")
plt.title("Vasicek yield curve today")
plt.show()

# %%
# Rates 2: simulated short rate after 1 year should match the known mean and spread
np.random.seed(seed)
rates = simulate_short_rate(r0, a, b, sigma_r, T=1, N=12, n_paths=n_paths) # monthly steps over one year
r1 = rates[:, -1]

mean_exact = b + (r0 - b) * np.exp(-a) # pulled part of the way from r0 towards b
sd_exact = sigma_r * np.sqrt((1 - np.exp(-2 * a)) / (2 * a)) # shocks partly cancelled by the pull back to b
print(f"Short rate in 1 year - mean: {r1.mean():.4f} (exact {mean_exact:.4f}), sd: {r1.std():.4f} (exact {sd_exact:.4f})")
print(f"1-in-200 low short rate: {np.percentile(r1, 0.5):.2%}")
assert abs(r1.mean() - mean_exact) < 0.0005
assert abs(r1.std() / sd_exact - 1) < 0.05

# %%
# Rates 3: closed-form bond price matches Monte Carlo - like Black-Scholes vs mc_call_price
# MC price of £1 in T years = average of exp(-sum of rates along the path)
for T in [1, 5, 10]:
    np.random.seed(seed)
    N = 12 * T # monthly steps
    paths = simulate_short_rate(r0, a, b, sigma_r, T, N, n_paths)
    integral = (paths[:, :-1] + paths[:, 1:]).sum(axis=1) * 0.5 * (T / N) # area under each rate path
    mc_price = np.exp(-integral).mean()
    exact = zcb_price(r0, T, a, b, sigma_r)
    print(f"{T:>2}-year bond: MC {mc_price:.5f}, closed form {exact:.5f}, gap {abs(mc_price - exact):.5f}")
    assert abs(mc_price / exact - 1) < 0.002

# %%
# Rates 4: liabilities on the Vasicek curve instead of a flat rate
df_0 = zcb_price(r0, times, a, b, sigma_r)
liab_0 = value_liabilities(cash_flows, times, df_0)
liab_dur = liability_duration(cash_flows, times, df_0)
print(f"Liabilities on Vasicek curve: £{liab_0 / 1e6:,.0f}m, duration {liab_dur:.1f} years")

# %%
# Rates 5: falling rates - long gilts offset the rise in liabilities, short gilts don't
# Back the liabilities with the same £ in gilts, then shift every yield down 1 point
shift = -0.01
liab_down = value_liabilities(cash_flows, times, zcb_price(r0, times, a, b, sigma_r, shift))

print(f"Liabilities: £{liab_0 / 1e6:,.0f}m -> £{liab_down / 1e6:,.0f}m (+£{(liab_down - liab_0) / 1e6:,.0f}m)")
gains = {}
for maturity in [1, 5, round(liab_dur), 20]:
    face = liab_0 / zcb_price(r0, maturity, a, b, sigma_r) # £ the gilt pays at maturity
    gilt_down = face * zcb_price(r0, maturity, a, b, sigma_r, shift)
    gains[maturity] = gilt_down - liab_0
    surplus_change = gains[maturity] - (liab_down - liab_0)
    print(f"{maturity:>2}-year gilts: +£{gains[maturity] / 1e6:,.0f}m, own funds change £{surplus_change / 1e6:+,.0f}m")

matched = round(liab_dur)
assert liab_down > liab_0 # falling rates make liabilities more expensive
assert gains[matched] > gains[5] > gains[1] # longer gilts gain more
assert abs(gains[matched] - (liab_down - liab_0)) < abs(gains[1] - (liab_down - liab_0)) # matched beats short

# %%
# Rates 6: a gilt bought today, revalued after one simulated year
maturity = matched
gilt_1 = revalue_zcb(liab_0, maturity, r0, r1, a, b, sigma_r) # one value per simulated path
print(f"{maturity}-year gilt: £{liab_0 / 1e6:,.0f}m today, after 1 year mean £{gilt_1.mean() / 1e6:,.0f}m, "
      f"1-in-200 low £{np.percentile(gilt_1, 0.5) / 1e6:,.0f}m, 1-in-200 high £{np.percentile(gilt_1, 99.5) / 1e6:,.0f}m")
assert np.corrcoef(r1, gilt_1)[0, 1] < -0.99 # gilt value moves opposite to rates
assert np.isclose(revalue_zcb(100, 1, r0, r1, a, b, sigma_r), 100 / zcb_price(r0, 1, a, b, sigma_r)).all() # 1-year gilt just pays out
print("All rate checks passed")
