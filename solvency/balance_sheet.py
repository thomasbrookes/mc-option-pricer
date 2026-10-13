"""
Balance sheet and capital.

- Own funds = assets - liabilities, at t=0 and in each simulated scenario at t=1.
- SCR = own funds at t=0 - 1-in-200 worst own funds at t=1 (discounted back).
- Solvency ratio = own funds / SCR.
- On/off switch per risk driver -> standalone SCRs -> diversification benefit.

Built in step 7.
"""
