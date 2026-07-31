import numpy as np
import yfinance as yf

def get_stock_params(ticker, start, end):
    """
    Get S0, mu, and sigma for a stock from real historical price data.

    Parameters:
        ticker: stock ticker, e.g. "AAPL"
        start: start date for the historical window, e.g. "2023-01-01"
        end: end date for the historical window, e.g. "2026-01-01"

    Returns:
        S0: most recent closing price
        mu: annualised average return, estimated from history
        sigma: annualised volatility, estimated from history
    """
    prices = yf.download(ticker, start=start, end=end)["Close"].squeeze() # daily closing prices - squeeze in case yfinance returns a 1-column frame

    log_returns = np.log(prices / prices.shift(1)).dropna() # daily log returns

    S0 = float(prices.iloc[-1]) # most recent price
    mu = float(log_returns.mean() * 252) # annualise the average daily return
    sigma = float(log_returns.std() * np.sqrt(252)) # annualise the daily volatility

    return S0, mu, sigma

def get_corr_matrix(tickers, start, end):
    """
    Get the correlation matrix between a group of stocks from real historical price data.

    Parameters:
        tickers: list of stock tickers, e.g. ["AAPL", "MSFT"]
        start: start date for the historical window
        end: end date for the historical window

    Returns:
        corr_matrix: correlation between each pair of stocks, based on daily returns
    """
    prices = yf.download(tickers, start=start, end=end)["Close"] # daily closing prices, one column per stock

    log_returns = np.log(prices / prices.shift(1)).dropna() # daily log returns, one column per stock

    corr_matrix = log_returns.corr() # correlation between each pair of stocks

    return corr_matrix
