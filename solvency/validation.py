"""
Sanity checks, run as # %% cells:
- Vasicek bond prices match the closed-form formula
- All risks switched off -> SCR approximately zero
- Falling rates increase liabilities; long bonds offset this better than short bonds
- Equity-heavy SCR > bond-heavy SCR
- Combined SCR < sum of standalone SCRs, gap narrows as correlations -> 1

Each check is added alongside the step that makes it possible.
"""
