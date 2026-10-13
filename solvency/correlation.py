"""
Correlation across all five risk drivers:
tech equity, non-tech equity, short rate, tech spread, other spread.

- Builds the 5x5 correlation matrix from the parameters set in the runnable scripts.
- Blends it towards 1 to create crisis correlations.
- Checks the matrix is valid for Cholesky.

Built in step 6.
"""
