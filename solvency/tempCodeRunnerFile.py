# %%
import numpy as np
import matplotlib.pyplot as plt
from liabilities import survival_prob, project_cash_flows, flat_discount_factors, value_liabilities, liability_duration

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