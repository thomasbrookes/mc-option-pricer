"""
Equities: two buckets (tech/AI and non-tech), simulated with the existing GBM engine.

Wraps sim_correlated_paths from src/gbm.py - the option pricer itself is not changed.
Also uses the same engine call to produce the correlated shocks for rates and spreads.

Built in step 5.
"""
