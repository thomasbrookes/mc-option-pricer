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
from credit import simulate_spread, corporate_bond_price, revalue_corporate, matching_adjustment
from equities import simulate_equity_growth, simulate_all_drivers, revalue_equities
from correlation import check_corr_matrix, print_corr_matrix
from balance_sheet import initial_balance_sheet, simulate_own_funds, scr_and_ratio

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

# Credit spreads - mean-reverting like Vasicek, one process per bucket
s0_tech = 0.018 # tech/data-centre spread today - 180 bps
theta_tech = 0.020 # long-run tech spread
kappa_tech = 0.5 # speed tech spreads are pulled back - faster than rates, panics fade
sigma_tech = 0.012 # size of tech spread shocks - much jumpier than other debt
s0_other = 0.012 # other corporate spread today - 120 bps
theta_other = 0.013 # long-run other spread
kappa_other = 0.5 # speed other spreads are pulled back
sigma_other = 0.0065 # size of other spread shocks
ma_fraction = 0.5 # share of the bond spread allowed as matching adjustment

# Equities - GBM via the existing engine, volatilities and correlation from Yahoo Finance 2016-2025
mu_eq_tech = 0.085 # tech expected return - risk-free plus a 4.5% equity risk premium, not a historical average
sigma_eq_tech = 0.24 # tech volatility - XLK (US tech sector) 2016-2025 was 24.3%
mu_eq_other = 0.075 # non-tech expected return - risk-free plus 3.5% equity risk premium
sigma_eq_other = 0.16 # non-tech volatility - SPXT (S&P 500 ex-tech) 2016-2025 was 16.3%
rho_equity = 0.74 # correlation between tech and non-tech - XLK vs SPXT daily returns 2016-2025
tech_weight = 0.38 # share of equities in tech - S&P 500 tech sector weight, end June 2026

# Correlation between all five drivers - rows and columns in DRIVERS order:
# tech equity, non-tech equity, short rate, tech spread, other spread
# Positive equity-rate: shares down, rates down. Negative equity-spread: shares down, spreads wider
corr_matrix = [
    [ 1.00,  0.74,  0.50, -0.75, -0.60], # tech equity - 0.74 from Yahoo data, 0.5 and -0.75 from the standard formula
    [ 0.74,  1.00,  0.50, -0.60, -0.75], # non-tech equity
    [ 0.50,  0.50,  1.00, -0.50, -0.50], # short rate - rates fall when spreads widen, standard formula 0.5
    [-0.75, -0.60, -0.50,  1.00,  0.80], # tech spread - each bucket's equity links most to its own spread
    [-0.60, -0.75, -0.50,  0.80,  1.00], # other spread - spreads widen together
]

# Simulation
n_paths = 10_000 # number of simulated scenarios
seed = 42 # fixed so results are repeatable

# Starting capital
own_funds_ratio = 0.075 # cushion = 7.5% of liabilities - puts the modern insurer at a typical ~200% solvency ratio

# Everything above in one dict, so the balance sheet functions can take it in one go
p = dict(A=A, B=B, c=c, max_age=max_age, n_annuitants=n_annuitants, age_min=age_min, age_max=age_max,
         annual_payment=annual_payment, r0=r0, a=a, b=b, sigma_r=sigma_r,
         s0_tech=s0_tech, theta_tech=theta_tech, kappa_tech=kappa_tech, sigma_tech=sigma_tech,
         s0_other=s0_other, theta_other=theta_other, kappa_other=kappa_other, sigma_other=sigma_other,
         ma_fraction=ma_fraction, mu_eq_tech=mu_eq_tech, sigma_eq_tech=sigma_eq_tech, mu_eq_other=mu_eq_other,
         sigma_eq_other=sigma_eq_other, tech_weight=tech_weight, corr_matrix=np.array(corr_matrix),
         own_funds_ratio=own_funds_ratio)

# The two insurers - same liabilities and same cushion, different investments
modern = dict(
    gilt_weight=0.55, # share of assets in gilts
    corp_weight=0.40, # share in corporate bonds
    equity_weight=0.05, # share in shares
    gilt_maturity=9, # years - matched to the ~8.6-year liabilities
    corp_maturity=9,
    corp_tech_share=0.10, # share of corporate bonds lent to tech/data centres - roughly their index weight
)
style_1999 = dict(modern, gilt_weight=0.35, corp_weight=0.25, equity_weight=0.40) # same bonds, 40% in shares

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

# %%
# Credit 1: simulated spreads after 1 year match the known mean and spread, tech moves more
np.random.seed(seed)
s1_tech = simulate_spread(s0_tech, kappa_tech, theta_tech, sigma_tech, T=1, N=12, n_paths=n_paths)[:, -1]
s1_other = simulate_spread(s0_other, kappa_other, theta_other, sigma_other, T=1, N=12, n_paths=n_paths)[:, -1]

for name, s1, s0_, k, th, sg in [("Tech", s1_tech, s0_tech, kappa_tech, theta_tech, sigma_tech),
                                  ("Other", s1_other, s0_other, kappa_other, theta_other, sigma_other)]:
    mean_exact = th + (s0_ - th) * np.exp(-k)
    sd_exact = sg * np.sqrt((1 - np.exp(-2 * k)) / (2 * k))
    print(f"{name} spread in 1 year - mean {s1.mean():.2%} (exact {mean_exact:.2%}), sd {s1.std():.2%} (exact {sd_exact:.2%}), "
          f"1-in-200 wide {np.percentile(s1, 99.5):.2%}, floored at zero {np.mean(s1 == 0):.1%} of paths")
    assert abs(s1.mean() - mean_exact) < 0.001

assert np.percentile(s1_tech, 99.5) - s0_tech > np.percentile(s1_other, 99.5) - s0_other # tech widens more

# %%
# Credit 2: corporate yield = gilt yield + spread, so a corporate bond is cheaper than a gilt
tau = 10
gilt = zcb_price(r0, tau, a, b, sigma_r)
corp = corporate_bond_price(r0, s0_other, tau, a, b, sigma_r)
corp_yield = -np.log(corp) / tau
print(f"10-year gilt yield {zero_yield(r0, tau, a, b, sigma_r):.2%}, corporate yield {corp_yield:.2%}")
assert corp < gilt
assert np.isclose(corp_yield - zero_yield(r0, tau, a, b, sigma_r), s0_other)

# %%
# Credit 3: spreads widen 100 bps instantly - price falls by about duration x 1%
for tau in [5, 10, 15]:
    value_wide = revalue_corporate(100, tau, r0, r0, s0_other, s0_other + 0.01, a, b, sigma_r, horizon=0)
    print(f"{tau:>2}-year corporate bond: £100 -> £{value_wide:.1f} after +100 bps")
    assert abs((100 - value_wide) - tau) < 0.1 * tau # roughly duration x 1%

# %%
# Credit 4: the matching adjustment cushions a spread widening
# Insurer backs its liabilities with 60% gilts, 10% tech corporates, 30% other corporates, all 10-year
bond_mix = np.array([0.6, 0.1, 0.3]) # gilts, tech, other
bond_spreads_0 = np.array([0.0, s0_tech, s0_other])

ma_0 = matching_adjustment(bond_mix, bond_spreads_0, ma_fraction)
liab_ma_0 = value_liabilities(cash_flows, times, df_0, ma=ma_0)
assets_0 = liab_ma_0 * bond_mix # £ in each bond bucket, total equal to the liabilities
print(f"MA today: {ma_0 * 1e4:.0f} bps, liabilities £{liab_0 / 1e6:,.0f}m without MA -> £{liab_ma_0 / 1e6:,.0f}m with MA")

widen = np.array([0.0, 0.03, 0.01]) # tech +300 bps, other +100 bps, gilts unaffected
assets_wide = np.array([
    revalue_corporate(assets_0[0], 10, r0, r0, 0.0, 0.0, a, b, sigma_r, horizon=0), # gilt = corporate bond with zero spread
    revalue_corporate(assets_0[1], 10, r0, r0, s0_tech, s0_tech + widen[1], a, b, sigma_r, horizon=0),
    revalue_corporate(assets_0[2], 10, r0, r0, s0_other, s0_other + widen[2], a, b, sigma_r, horizon=0),
])
ma_wide = matching_adjustment(assets_wide, bond_spreads_0 + widen, ma_fraction)
liab_ma_wide = value_liabilities(cash_flows, times, df_0, ma=ma_wide)

asset_loss = assets_0.sum() - assets_wide.sum()
liab_fall = liab_ma_0 - liab_ma_wide
print(f"Tech +300 bps, other +100 bps: bonds -£{asset_loss / 1e6:,.0f}m, MA rises to {ma_wide * 1e4:.0f} bps, "
      f"liabilities -£{liab_fall / 1e6:,.0f}m, own funds -£{(asset_loss - liab_fall) / 1e6:,.0f}m (would be -£{asset_loss / 1e6:,.0f}m without MA)")
assert ma_wide > ma_0 # wider spreads -> bigger MA
assert 0 < liab_fall < asset_loss # the MA cushions part of the loss, not all of it

# %%
# Credit 5: corporate bonds bought today, revalued after one simulated year
# rates and spreads independent for now - linked up in step 6
tech_1 = revalue_corporate(100, 10, r0, r1, s0_tech, s1_tech, a, b, sigma_r)
other_1 = revalue_corporate(100, 10, r0, r1, s0_other, s1_other, a, b, sigma_r)
for name, v in [("Tech", tech_1), ("Other", other_1)]:
    print(f"{name} 10-year corporate: £100 today, after 1 year mean £{v.mean():.1f}, 1-in-200 low £{np.percentile(v, 0.5):.1f}")
assert np.percentile(tech_1, 0.5) < np.percentile(other_1, 0.5) # tech debt has the worse tail
print("All credit checks passed")

# %%

# %%
# Equities 1: the engine gives the right average growth, volatility and correlation
np.random.seed(seed)
growth = simulate_equity_growth(mu_eq_tech, sigma_eq_tech, mu_eq_other, sigma_eq_other, rho_equity, T=1, N=12, n_paths=n_paths)
log_ret = np.log(growth)

for i, (name, mu_, sg) in enumerate([("Tech", mu_eq_tech, sigma_eq_tech), ("Non-tech", mu_eq_other, sigma_eq_other)]):
    print(f"{name}: mean growth {growth[:, i].mean():.3f} (exact {np.exp(mu_):.3f}), volatility {log_ret[:, i].std():.3f} (input {sg}), "
          f"1-in-200 fall {1 - np.percentile(growth[:, i], 0.5):.0%}")
    assert abs(growth[:, i].mean() / np.exp(mu_) - 1) < 0.01
    assert abs(log_ret[:, i].std() / sg - 1) < 0.03

corr_sim = np.corrcoef(log_ret.T)[0, 1]
print(f"Correlation: {corr_sim:.2f} (input {rho_equity})")
assert abs(corr_sim - rho_equity) < 0.02
assert np.percentile(growth[:, 0], 0.5) < np.percentile(growth[:, 1], 0.5) # tech has the worse tail

# %%
# Equities 2: what a 1-in-200 equity year costs a modern vs a 1999-style insurer
# Same £1bn of assets, 5% vs 40% in equities, 38% of the equities in tech
for name, equity_share in [("Modern (5% equities)", 0.05), ("1999-style (40% equities)", 0.40)]:
    equity_0 = 1e9 * equity_share
    equity_1 = revalue_equities(equity_0, tech_weight, growth)
    loss = equity_0 - np.percentile(equity_1, 0.5)
    print(f"{name}: £{equity_0 / 1e6:,.0f}m in equities, 1-in-200 loss £{loss / 1e6:,.0f}m")
print("All equity checks passed")

# %%

# %%
# Correlation 1: the matrix is valid
corr = check_corr_matrix(corr_matrix)
print_corr_matrix(corr)
print(f"Smallest eigenvalue {np.linalg.eigvalsh(corr).min():.3f} - above zero, so Cholesky works")

# %%
# Correlation 2: one engine call gives correlated shares and the shocks for rates and spreads
np.random.seed(seed)
growth, dW = simulate_all_drivers(mu_eq_tech, sigma_eq_tech, mu_eq_other, sigma_eq_other, corr, T=1, N=12, n_paths=n_paths)
assert abs(dW.std() / np.sqrt(1 / 12) - 1) < 0.02 # monthly shocks have the right size

r1 = simulate_short_rate(r0, a, b, sigma_r, T=1, N=12, n_paths=n_paths, dW=dW[:, :, 0])[:, -1]
s1_tech = simulate_spread(s0_tech, kappa_tech, theta_tech, sigma_tech, T=1, N=12, n_paths=n_paths, dW=dW[:, :, 1])[:, -1]
s1_other = simulate_spread(s0_other, kappa_other, theta_other, sigma_other, T=1, N=12, n_paths=n_paths, dW=dW[:, :, 2])[:, -1]

# what each driver did over the year - share returns, and changes in rate and spreads
outcomes = np.column_stack([np.log(growth[:, 0]), np.log(growth[:, 1]), r1 - r0, s1_tech - s0_tech, s1_other - s0_other])
corr_sim = np.corrcoef(outcomes.T)
print("Correlation of one-year outcomes in the simulation:")
print_corr_matrix(corr_sim)
assert np.abs(corr_sim - corr).max() < 0.05 # close to the input - small gaps from mean reversion and the zero floor

# %%
# Correlation 3: bad things now happen together
# In the worst 1% of years for tech shares, what did rates and spreads do?
worst = outcomes[:, 0] <= np.percentile(outcomes[:, 0], 1)
print(f"Worst 1% of tech years: tech shares {np.expm1(outcomes[worst, 0].mean()):.0%}, non-tech {np.expm1(outcomes[worst, 1].mean()):.0%}, "
      f"short rate {outcomes[worst, 2].mean() * 1e4:+.0f} bps, tech spread {outcomes[worst, 3].mean() * 1e4:+.0f} bps, "
      f"other spread {outcomes[worst, 4].mean() * 1e4:+.0f} bps")
assert outcomes[worst, 2].mean() < 0 # rates fall in an equity crash
assert outcomes[worst, 3].mean() > 0 and outcomes[worst, 4].mean() > 0 # spreads widen in an equity crash
print("All correlation checks passed")

# %%
# Balance sheet 1: today's balance sheet adds up
bs_modern = initial_balance_sheet(modern, p)
for item in ["gilts", "corp_tech", "corp_other", "equities", "invested", "liabilities", "own_funds"]:
    print(f"{item:>12}: £{bs_modern[item] / 1e6:,.0f}m")
assert np.isclose(bs_modern["gilts"] + bs_modern["corp_tech"] + bs_modern["corp_other"] + bs_modern["equities"], bs_modern["invested"])
assert np.isclose(bs_modern["own_funds"], own_funds_ratio * bs_modern["liabilities"])

# %%
# Balance sheet 2: SCR and solvency ratio for both insurers
results = {}
for name, portfolio in [("Modern", modern), ("1999-style", style_1999)]:
    bs0 = initial_balance_sheet(portfolio, p)
    of1, detail = simulate_own_funds(bs0, portfolio, p, n_paths, seed)
    scr, ratio = scr_and_ratio(bs0["own_funds"], of1)
    results[name] = (bs0, of1, detail, scr, ratio)
    print(f"{name}: own funds £{bs0['own_funds'] / 1e6:,.0f}m, SCR £{scr / 1e6:,.0f}m, solvency ratio {ratio:.0%}")

assert results["1999-style"][3] > results["Modern"][3] # equity-heavy needs more capital - brief validation check
assert 1.5 < results["Modern"][4] < 3.0 # modern insurer starts at a realistic ratio

# %%
# Balance sheet 3: what goes wrong in the modern insurer's worst years?
bs0, of1, detail, scr, ratio = results["Modern"]
worst = of1 <= np.percentile(of1, 1) # worst 1% of simulated years
print(f"Modern insurer, worst 1% of years: rate {(detail['r1'][worst].mean() - r0) * 1e4:+.0f} bps, "
      f"tech spread {(detail['s1_tech'][worst].mean() - s0_tech) * 1e4:+.0f} bps, other spread {(detail['s1_other'][worst].mean() - s0_other) * 1e4:+.0f} bps, "
      f"shares {detail['equities'][worst].mean() / bs0['equities'] - 1:+.0%}")

# %%
# Balance sheet 4: with every volatility set to zero, nothing random happens, so the SCR should be close to zero
# Not exactly zero - shares and corporate bonds are expected to earn a bit more than gilts, and rates and spreads drift
p_calm = dict(p, sigma_r=0.0, sigma_tech=0.0, sigma_other=0.0, sigma_eq_tech=0.0, sigma_eq_other=0.0)
bs_calm = initial_balance_sheet(modern, p_calm)
of1_calm, _ = simulate_own_funds(bs_calm, modern, p_calm, n_paths, seed)
scr_calm, _ = scr_and_ratio(bs_calm["own_funds"], of1_calm)
print(f"No randomness: SCR £{scr_calm / 1e6:,.1f}m (vs £{results['Modern'][3] / 1e6:,.0f}m normally), every path the same: {np.ptp(of1_calm) < 1}")
assert np.ptp(of1_calm) < 1 # all paths identical
assert abs(scr_calm) < 0.2 * results["Modern"][3] # small next to the real SCR

# %%
# Balance sheet 5: results are stable - a different random seed barely moves the SCR
for s_ in [1, 7, 2026]:
    of1_s, _ = simulate_own_funds(bs_modern, modern, p, n_paths, s_)
    scr_s, ratio_s = scr_and_ratio(bs_modern["own_funds"], of1_s)
    print(f"Seed {s_}: SCR £{scr_s / 1e6:,.1f}m, ratio {ratio_s:.0%}")
    assert abs(scr_s / results["Modern"][3] - 1) < 0.1
print("All balance sheet checks passed")
