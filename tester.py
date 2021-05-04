import pandas as pd
import numpy as np
from prophet import Prophet
from art import *
from halo import Halo
import os
import time
from nelder_mead import NelderMead
from alpha_vantage.timeseries import TimeSeries


class StockOptimizator:
    def __init__(self, api_key, investment_horizon_days=None, symbols=None):
        """Initializes the StockOptimizator object

        Args:
            api_key (string): AlphaVantage API key
        """
        tprint("lp-money-machine")
        ts = TimeSeries(key=api_key, output_format='pandas',
                        indexing_type='integer')  # PFW4J214A8S34EZB
        # If the user didn't provide investment horizon and symbols, ask for 'em
        if investment_horizon_days == None or symbols == None:
            self.initialize_parameters()
        else:
            self.investment_horizon_days = investment_horizon_days
            self.symbols = symbols
        # Now, we fill up stocks_data with actual data
        spinner = Halo(
            text="Downloading stocks data from AlphaVantage...", spinner="moon")
        spinner.start()
        self.stocks_data = {}
        self.today_prices = {}
        i = 0
        for symbol in self.symbols:
            self.stocks_data[symbol] = ts.get_daily(
                symbol=symbol, outputsize='full')
            self.today_prices[symbol] = self.stocks_data[symbol][0].head(1)[
                "4. close"].item()
            self.stocks_data[symbol][0].drop(
                self.stocks_data[symbol][0].head(self.investment_horizon_days).index, inplace=True)
            i += 1
            if i % 4 == 0:
                print("Downloaded 5 stocks, sleeping for 60sec")
                time.sleep(60)
        self.stocks_analysis = pd.DataFrame(columns=[
            "Name", "PredictionsFromDate", "PredictionsToDate", "OpenPrice", "Risk", "Prediction"])
        spinner.stop()

    def initialize_parameters(self):
        """Initializes the investment horizon and symbols
        """
        self.investment_horizon_days = input(
            "Please, insert an investment horizon in days [ENTER for 30]: ")
        if self.investment_horizon_days == "":
            self.investment_horizon_days = 30
        else:
            self.investment_horizon_days = int(self.investment_horizon_days)
        symbols_string = input(
            "Please insert a comma-separated list of max. 5 stock symbols [ENTER for default one]: ")
        if symbols_string == "":
            self.symbols = ["NVDA", "GOOG"]
        else:
            symbols_string.strip()
            self.symbols = symbols_string.split(',')

    class suppress_stdout_stderr(object):
        '''
        Used to suppress the really long Prophet output, which we don't need.

        A context manager for doing a "deep suppression" of stdout and stderr in
        Python, i.e. will suppress all print, even if the print originates in a
        compiled C/Fortran sub-function.
        This will not suppress raised exceptions, since exceptions are printed
        to stderr just before a script exits, and after the context manager has
        exited (at least, I think that is why it lets exceptions through).

        '''

        def __init__(self):
            # Open a pair of null files
            self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
            # Save the actual stdout (1) and stderr (2) file descriptors.
            self.save_fds = [os.dup(1), os.dup(2)]

        def __enter__(self):
            # Assign the null pointers to stdout and stderr.
            os.dup2(self.null_fds[0], 1)
            os.dup2(self.null_fds[1], 2)

        def __exit__(self, *_):
            # Re-assign the real stdout/stderr back to (1) and (2)
            os.dup2(self.save_fds[0], 1)
            os.dup2(self.save_fds[1], 2)
            # Close the null files
            for fd in self.null_fds + self.save_fds:
                os.close(fd)

    def create_prophet_dataframe(self, data):
        """Creates a Prophet-compatible dataframe. Needed because Prophet expects data in a given shape

        Args:
            stock_data (Pandas dataframe): Historical stock data

        Returns:
            Pandas dataframe: Prophet-compatible dataframe
        """
        prophet_df = pd.DataFrame()
        prophet_df["ds"] = data["index"]
        prophet_df["y"] = data["4. close"]
        return prophet_df

    def predict_stock_return(self, close_prices, days_from_now):
        """Predicts the return and risk over the investment horizon

        Args:
            close_prices (Pandas DataFrame): Time series containing the closing prices
            days_from_now (int): Investment horizon

        Returns:
            tuple: Return forecast, risk forecast
        """
        estimator = Prophet()
        with self.suppress_stdout_stderr():
            estimator.fit(close_prices)
        future = estimator.make_future_dataframe(periods=days_from_now)
        forecast = estimator.predict(future, )
        risk = abs(
            np.std(forecast["yhat"].iloc[-self.investment_horizon_days:]))
        return forecast["yhat"].iloc[-1], risk

    def analyse_stocks(self):
        spinner = Halo(
            text="Analysing the timeseries through Profet", spinner="moon")
        spinner.start()
        for symbol, result in self.stocks_data.items():
            data, info = result
            open_date = data["index"].iloc[0]
            try:
                close_date = data["index"].iloc[-1]
                # We take the closing price of yesterday as buying price
                open_price = data["4. close"].iloc[-1]
                prediction, risk = self.predict_stock_return(self.create_prophet_dataframe(
                    data[["index", "4. close"]]), self.investment_horizon_days)
                self.stocks_analysis = self.stocks_analysis.append({
                    "Name": symbol,
                    "PredictionsFromDate": open_date,
                    "PredictionsToDate": close_date,
                    "OpenPrice": open_price,
                    "Risk": risk,
                    "Prediction": prediction
                }, ignore_index=True)
            except IndexError:
                print(
                    f"Index {symbol} doesn't have sufficient historical data for the provided horizon, it will be skipped")
        # We now add the ror column, containing predicted return over risk
        self.stocks_analysis["ror"] = (self.stocks_analysis["Prediction"] -
                                       self.stocks_analysis["OpenPrice"])/self.stocks_analysis["Risk"]
        self.stocks_analysis.sort_values("ror", ascending=False)
        spinner.stop()

    def objective_function(self, portfolio):
        """The objective function to be optimized

        Args:
            portfolio (np.array): Portfolio
        """
        sum = 0
        for i in range(len(portfolio)):
            sum += self.stocks_analysis.iloc[i]["ror"] * portfolio[i]
        return -sum

    def optimize(self, reflection_parameter=1, expansion_parameter=2, contraction_parameter=0.1, shrinkage_parameter=0.5, max_iterations=15, shift_coefficient=0.05):
        print("Starting optimization...")
        self.nm = NelderMead(len(self.symbols), self.objective_function, 1, reflection_parameter, expansion_parameter,
                             contraction_parameter, shrinkage_parameter, max_iterations, shift_coefficient)
        self.nm.initialize_simplex()
        results = self.nm.fit(0.0001)  # Stop when std_dev is 0.0001
        print("Optimization completed!")
        money = 0
        money_if_stupid = 0
        for i in range(len(self.symbols)):
            symbol = self.symbols[i]
            open_price = self.stocks_data[symbol][0].head(1)[
                "4. close"].item()
            from_date = self.stocks_analysis.loc[i, "PredictionsFromDate"]
            print(
                f"The stock {symbol} should be {round(results[i]*100,2)}% of your portfolio, costed {open_price} and now costs {self.today_prices[symbol]}.")
            money += ((1000*results[i])/(open_price)*self.today_prices[symbol])
            money_if_stupid += ((1000*(1/len(self.symbols))) /
                                (open_price)*self.today_prices[symbol])
        print(
            f"This means that if you had invested 1000$ on the {from_date} you would now have {round(money, 2)}$\nIf all the stocks were equally bought, you would have {money_if_stupid}")


if __name__ == "__main__":
    op = StockOptimizator("PFW4J214A8S34EZB", 20, )
    op.analyse_stocks()
    op.optimize()
