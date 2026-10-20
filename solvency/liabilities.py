"""
Liabilities: the annuity promises the insurer has made.

- Mortality: Gompertz-Makeham law gives the chance of surviving each future year.
- Cash flows: expected annual payments = annual amount x expected number still alive.
- Valuation: discount each expected payment back to today and add them up.
"""
import numpy as np


def survival_prob(ages, t, A, B, c):
    """
    Chance that someone aged x is still alive t years from now, under Gompertz-Makeham.

    Parameters:
        ages: current age of each group of pensioners, shape (n_ages,)
        t: years from now, shape (n_times,)
        A, B, c: Gompertz-Makeham parameters, death rate at age x is A + B * c**x

    Returns:
        tpx: survival probabilities, shape (n_ages, n_times)
    """
    ages = np.array(ages, dtype=float)[:, None] # column - one row per age
    t = np.array(t, dtype=float)[None, :] # row - one column per future year

    # add up the death rate between age x and x+t, then survival = exp(-that total)
    total_death_rate = A * t + B * c**ages * (c**t - 1) / np.log(c)

    return np.exp(-total_death_rate)


def project_cash_flows(n_annuitants, age_min, age_max, annual_payment, A, B, c, max_age):
    """
    Expected annuity payments in each future year, for the whole block.

    Parameters:
        n_annuitants: number of pensioners
        age_min, age_max: pensioners are spread evenly across these ages
        annual_payment: £ paid to each pensioner per year, at the end of the year
        A, B, c: Gompertz-Makeham parameters
        max_age: nobody lives past this age

    Returns:
        times: payment times in years, 1, 2, ..., up to max_age - age_min
        cash_flows: expected £ paid at each time, same shape as times
    """
    ages = np.arange(age_min, age_max + 1) # one group per whole age
    counts = np.full(len(ages), n_annuitants / len(ages)) # same number of pensioners at each age

    times = np.arange(1, max_age - age_min + 1) # yearly payments until the youngest hits max_age

    tpx = survival_prob(ages, times, A, B, c) # chance each age group is alive at each payment time
    tpx[ages[:, None] + times[None, :] > max_age] = 0.0 # nobody alive past max_age

    expected_alive = counts @ tpx # expected number of pensioners alive at each time
    cash_flows = annual_payment * expected_alive # expected £ paid at each time

    return times, cash_flows


def flat_discount_factors(rate, times):
    """
    Discount factors for a flat interest rate - placeholder until the Vasicek curve in step 3.

    Parameters:
        rate: continuously compounded interest rate, e.g. 0.04 for 4%
        times: payment times in years

    Returns:
        discount_factors: value today of £1 paid at each time
    """
    return np.exp(-rate * np.array(times, dtype=float))


def value_liabilities(cash_flows, times, discount_factors, ma=0.0):
    """
    Value today of all expected annuity payments.

    Parameters:
        cash_flows: expected £ paid at each time
        times: payment times in years
        discount_factors: value today of £1 paid at each time, shape (n_times,)
            or (n_paths, n_times) to value many simulated curves at once
        ma: matching adjustment - extra discount rate added on top of the curve,
            a number or one per path (from credit.matching_adjustment)

    Returns:
        value: £ value of the liabilities - a number, or one per path
    """
    ma = np.asarray(ma, dtype=float)[..., None] # one row per path if ma varies by path
    ma_factors = np.exp(-ma * np.array(times, dtype=float)) # extra discounting from the matching adjustment

    return (discount_factors * ma_factors) @ cash_flows # discount each payment and add them up


def liability_duration(cash_flows, times, discount_factors):
    """
    Duration of the liabilities - the average time until payment, weighted by value today.
    Tells us how long the bonds backing the liabilities should be.

    Parameters:
        cash_flows: expected £ paid at each time
        times: payment times in years
        discount_factors: value today of £1 paid at each time

    Returns:
        duration: in years
    """
    pv = discount_factors * cash_flows # value today of each payment

    return (pv @ times) / pv.sum() # value-weighted average payment time
