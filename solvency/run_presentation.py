"""
Runs every experiment for the presentation. Use the # %% cells in VS Code.
Charts are added in step 9.
"""
# %%
from scenarios import p, modern, style_1999, concentrated, crash, n_paths, seed, run_scenario

# %%
# Run the three insurers - each gets its SCR from 10,000 simulated years, then the AI crash
runs = [
    run_scenario("1999-style (40% shares)", style_1999, p, crash, n_paths, seed),
    run_scenario("Modern, diversified credit (A)", modern, p, crash, n_paths, seed),
    run_scenario("Modern, concentrated credit (B)", concentrated, p, crash, n_paths, seed),
]

# %%
# Summary table - SCR, own funds and solvency ratio before and after the crash
print(f"{'Insurer':<34}{'Own funds':>11}{'SCR':>8}{'Ratio before':>14}{'Own funds after':>17}{'Ratio after':>13}")
for r in runs:
    print(f"{r['name']:<34}£{r['own_funds_before'] / 1e6:>8,.0f}m £{r['scr'] / 1e6:>4,.0f}m{r['ratio_before']:>14.0%}"
          f"   £{r['own_funds_after'] / 1e6:>10,.0f}m{r['ratio_after']:>13.0%}")

# %%
# Where each crash loss came from (£m, positive = money lost)
print(f"{'Insurer':<34}{'Shares':>9}{'Bonds':>9}{'Liabilities':>13}{'Total':>9}")
for r in runs:
    total = r["loss_shares"] + r["loss_bonds"] + r["loss_liabilities"]
    print(f"{r['name']:<34}{r['loss_shares'] / 1e6:>9,.0f}{r['loss_bonds'] / 1e6:>9,.0f}{r['loss_liabilities'] / 1e6:>13,.0f}{total / 1e6:>9,.0f}")
