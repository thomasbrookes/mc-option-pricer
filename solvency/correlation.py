"""
Correlation across all five risk drivers:
tech equity, non-tech equity, short rate, tech spread, other spread.

- Labels the drivers so the matrix is easy to read.
- Checks the matrix is valid for Cholesky.
"""
import numpy as np

DRIVERS = ["tech equity", "non-tech equity", "short rate", "tech spread", "other spread"] # order of rows and columns


def check_corr_matrix(corr_matrix):
    """
    Check a correlation matrix is usable - symmetric, ones on the diagonal, and consistent (positive definite).

    Parameters:
        corr_matrix: correlation between each pair of drivers, shape (5, 5) in DRIVERS order

    Returns:
        corr_matrix: the same matrix as a numpy array, if it passes
    """
    corr_matrix = np.array(corr_matrix, dtype=float)

    assert corr_matrix.shape == (len(DRIVERS), len(DRIVERS)), "need one row and column per driver"
    assert np.allclose(corr_matrix, corr_matrix.T), "correlation between A and B must equal B and A"
    assert np.allclose(np.diag(corr_matrix), 1.0), "each driver has correlation 1 with itself"
    assert np.all(np.abs(corr_matrix) <= 1.0), "correlations must be between -1 and 1"

    smallest = np.linalg.eigvalsh(corr_matrix).min() # negative means the correlations contradict each other
    assert smallest > 0, f"correlations are inconsistent - Cholesky would fail (smallest eigenvalue {smallest:.3f})"

    return corr_matrix


def print_corr_matrix(corr_matrix):
    """
    Print the correlation matrix with driver labels.

    Parameters:
        corr_matrix: shape (5, 5) in DRIVERS order

    Returns:
        None
    """
    print(" " * 16 + "".join(f"{d:>16}" for d in DRIVERS)) # column headers
    for name, row in zip(DRIVERS, corr_matrix):
        print(f"{name:>16}" + "".join(f"{x:>16.2f}" for x in row))
