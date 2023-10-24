#region imports
from AlgorithmImports import *
#endregion


# Your New Python File
from AlgorithmImports import *
from datetime import timedelta

#IN THIS SCRIPT WE ARE NOT USING "OnData" FUNCTION BECAUSE WE WANT TO PROPERLY CALL THE "FetchIV" FUNCTION AND FILL THE "RollingWindow" BY ADDING A DATA PER DAY.

class ImpliedVolatilityAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2012, 1, 1)
        self.SetEndDate(2023, 10, 1)
        self.SetCash(1000000)

        # Symbols
        symbols = ["SPY"]
        
        # Dictionaries to store option objects and rolling windows
        self.options = {}
        self.iv_history = {symbol: RollingWindow[float](252) for symbol in symbols}
        self.paired_positions = {} # Store the short option contracts and hedges
        
        for symbol in symbols:
            equity = self.AddEquity(symbol, resolution=Resolution.Hour)
            option = self.AddOption(symbol, resolution=Resolution.Hour)
            
            option.SetFilter(lambda universe: universe.IncludeWeeklys()
                                            .Strikes(-100, 2)  # Get tge number of stikes you want, +- from the atm strike
                                            .Expiration(timedelta(28), timedelta(50)))
            
            self.options[symbol] = option
        # Schedule daily fetch of IV and position management
        self.Schedule.On(self.DateRules.EveryDay("SPY"), self.TimeRules.At(15, 00), self.FetchIV)
        self.Schedule.On(self.DateRules.EveryDay("SPY"), self.TimeRules.At(15, 00), self.ManagePosition)

    def FetchIV(self):
        for symbol, option in self.options.items():
            option_chain = self.CurrentSlice.OptionChains.GetValue(option.Symbol)

            if option_chain:
                # First, filter options with DTE closest to 45 days
                options_near_30_dte = sorted(option_chain, key=lambda x: abs((x.Expiry - self.Time).days - 30))
                closest_dte = (options_near_30_dte[0].Expiry - self.Time).days

                # Now, filter options with the closest DTE (there might be multiple options with the same DTE)
                options_with_closest_dte = [x for x in options_near_30_dte if (x.Expiry - self.Time).days == closest_dte]
                
                # From the options with the closest DTE, find the ATM option
                atm_option = sorted(options_with_closest_dte, key=lambda x: abs(x.Strike - self.Securities[symbol].Price))[0]
                
                iv = atm_option.ImpliedVolatility
                self.iv_history[symbol].Add(iv)
                #self.Debug(f"Collected IV for {symbol} on {self.Time}: {iv}")

                if self.iv_history[symbol].IsReady:
                    self.CalculateIVMetrics(symbol)

    def CalculateIVMetrics(self, symbol):
        current_iv = self.iv_history[symbol][0]
        iv_max = max(self.iv_history[symbol])
        iv_min = min(self.iv_history[symbol])
        iv_rank = (current_iv - iv_min) / (iv_max - iv_min) if iv_max != iv_min else 0
        iv_percentile = sum(1 for iv in self.iv_history[symbol] if iv < current_iv) / 252
        #self.Debug(f"Symbol: {symbol}, IV Rank: {iv_rank}, IV Percentile: {iv_percentile}")

        # Check IV Rank condition and open a position if not already opened
        if iv_rank >= 0.4: #and symbol not in self.option_contracts:
            self.OpenPosition()

    def OpenPosition(self, target_strike=None):
        for symbol, option in self.options.items():
            option_chain = self.CurrentSlice.OptionChains.GetValue(option.Symbol)
        puts = [x for x in option_chain if x.Right == OptionRight.Put]
        #self.Debug(f"Number of puts available: {len(puts)}")
        if not option_chain:
            return

        # First, find options with DTE closest to 45 days
        puts_near_45_dte = sorted(puts, key=lambda x: abs((x.Expiry - self.Time).days - 45))
        closest_dte = (puts_near_45_dte[0].Expiry - self.Time).days

        # Now, filter puts with the closest DTE (there might be multiple options with the same DTE)
        puts_with_closest_dte = [x for x in puts_near_45_dte if (x.Expiry - self.Time).days == closest_dte]
        
        if target_strike:
            # Find the put with the strike closest to the target_strike
            target_put = sorted(puts_with_closest_dte, key=lambda x: abs(x.Strike - target_strike))[0]
        else:
            # From the puts with the closest DTE, find the one with delta closest to 0.25
            target_put = sorted(puts_with_closest_dte, key=lambda x: abs(x.Greeks.Delta + 0.25))[0]

        # Print option details
        self.Debug(f"Attempting to short {target_put.Symbol} with Delta: {target_put.Greeks.Delta}, DTE: {(target_put.Expiry - self.Time).days}, AskPrice: {target_put.AskPrice}, BidPrice: {target_put.BidPrice}")
        
        # Short the target put option
        ticket = self.Sell(target_put.Symbol, 10)

        # Buy the hedge put with delta closest to -1
        hedge_put = sorted(puts_with_closest_dte, key=lambda x: abs(x.Greeks.Delta + 0.01))[0]
        self.Buy(hedge_put.Symbol, 10)
        self.Debug(f"Attempting to long hedge {hedge_put.Symbol} with Delta: {hedge_put.Greeks.Delta}, DTE: {(hedge_put.Expiry - self.Time).days}, AskPrice: {hedge_put.AskPrice}, BidPrice: {hedge_put.BidPrice}")

        # Store the paired contracts
        self.paired_positions[target_put.Symbol] = (target_put, hedge_put)

    def ManagePosition(self):
        #self.Debug(length)
        for main_symbol, (main_contract, hedge_contract) in self.paired_positions.items():
            holding = self.Portfolio[main_contract.Symbol]


            # 1. Close the position if it reaches 50% of the max profit.
            #self.Debug(holding.UnrealizedProfitPercent)
            if holding.UnrealizedProfitPercent >= 0.50:  # Close at 50% max profit
                self.Buy(main_contract.Symbol, 10)
                self.Sell(hedge_contract.Symbol, 10)
                self.Debug(f"Closed position for {main_symbol} at 50% max profit. Hedge: {hedge_contract.Symbol}")
                del self.paired_positions[main_symbol]
                return

            # Check for DTE
            days_to_expiry = (main_contract.Expiry - self.Time).days

            # 2. If the option has 21 DTE left and is in profit, close the position.
            if days_to_expiry <= 21 and holding.UnrealizedProfit >= 0:
                self.Buy(main_contract.Symbol, 10)
                self.Sell(hedge_contract.Symbol, 10)
                self.Debug(f"Closed position for {main_symbol} with 21 DTE left and in profit.")
                del self.paired_positions[main_symbol]
                return

            # If the option has 21 DTE or less and is not in profit, roll the position.
            if days_to_expiry <= 21 and holding.UnrealizedProfit < 0:
                self.Buy(main_contract.Symbol, 10)
                self.Sell(hedge_contract.Symbol, 10)
                del self.paired_positions[main_symbol]
                self.OpenPosition(target_strike=main_contract.Strike)
                self.Debug(f"Rolled position for {main_symbol} with 21 DTE left and not in profit. Hedge: {hedge_contract.Symbol}")
                return
    
    def OnData(self, data):
        pass
