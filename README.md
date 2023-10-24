# SPY_High_IVPercentile_Backtest_QC
Backtest of shorting puts on historically high IV environment using QuantConnect Lean Engine

This is a very simple yet cool boilerplate script for backtesting a short-put SPY strategy on a high implied volatility environment. 

Breakdown of the script:

- Initialise the lean engine by setting the dates, portfolio size, assets or asset universes, get the equity prices as well as option chains for the assets, and filter the options

- IV of the underlying, IV Rank, and IV Percentile; neither of these are provided with the QuantConnect data sources, thus we have functions to calculate the IV the underlying at a given time by checking the atm strike IVs with 30 DTE. Then we collect and keep track of these for 252 rolling business days and calculate the IV Rank and IV Percentile

- We then have our function to open positions. This function shorts X amounts of puts with a desired delta and days to expiration. I used 0.25/-0.25 delta and 45 DTE. I also implemented a hedge leg and turned the strategy to a very wide puts spread which we long 0.01/-0.01 delta put for tail events. It seems to improve the Sharpe ratio and returns at the same time

- Finally, we have the function for managing our positions. This function does either of the following three things: If we hit %50 profit before 21 DTE, we close the position. If we hit 21 DTE and in profit, we close the position. If we hit 21 DTE and are not in profit, we roll the position to 45 DTE again


Notes:

- Currently, there seem to be data problems in QuantConnect, thus, I chose to wait before creating a more complex strategy until I can test it safely.
 
- This is a very simple boilerplate script, which doesn't even pay attention to the position sizing, portfolio volatility, and parameter enhancement let alone using supportive parameters to the strategy.

- QuantConnect is a powerful platform at this price point, as it is getting harder and harder to outperform in the stock markets. Thanks to higher retail anticipation, options markets can provide alpha thanks to it's nature of volatility sensitivity and time decay

