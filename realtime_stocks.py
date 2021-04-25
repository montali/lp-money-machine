import pandas as pd
import numpy as np
from prophet import Prophet
from art import *
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
        if investment_horizon_days != None and symbols != None:
            self.investment_horizon_days = investment_horizon_days
            self.symbols = symbols
        else:
            self.initialize_parameters
        # Now, we fill up stocks_data with actual data
        self.stocks_data = {}
        for symbol in self.symbols:
            self.stocks_data[symbol] = ts.get_intraday(
                symbol=symbol, interval='60min', outputsize='full')
        self.stocks_analysis = pd.DataFrame(columns=[
            "Name", "PredictionsFromDate", "PredictionsToDate", "OpenPrice", "Risk", "Prediction"])

    def initialize_parameters(self):
        """Initializes the investment horizon and symbols
        """
        self.investment_horizon_days = input(
            "Please, insert an investment horizon in days: ")
        symbols_string = input(
            "Please insert a comma-separated list of stock symbols: ")
        self.symbols = symbols_string.split(',')

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
        estimator.fit(close_prices)
        future = estimator.make_future_dataframe(periods=days_from_now)
        forecast = estimator.predict(future, )
        risk = abs(
            np.std(forecast["yhat"].iloc[-self.investment_horizon_days:]))
        return forecast["yhat"].iloc[-1], risk

    def analyse_stocks(self):
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

    def objective_function(self, portfolio):
        """The objective function to be optimized

        Args:
            portfolio (np.array): Portfolio
        """
        sum = 0
        for i in range(len(portfolio)):
            sum += self.stocks_analysis.iloc[i]["ror"] * portfolio[i]
        return 1000*portfolio[0] + 0.1*portfolio[1]

    def optimize(self, reflection_parameter=1, expansion_parameter=2, contraction_parameter=0.5, shrinkage_parameter=0.5, max_iterations=15, shift_coefficient=0.05):
        self.nm = NelderMead(len(self.symbols), self.objective_function, 1, reflection_parameter, expansion_parameter,
                             contraction_parameter, shrinkage_parameter, max_iterations, shift_coefficient)
        self.nm.initialize_simplex()
        print(self.nm.fit(0.00001))


if __name__ == "__main__":
    op = StockOptimizator("PFW4J214A8S34EZB", 20, [
                          "AAPL", "MSFT"])
    op.analyse_stocks()
    op.optimize()
""" 
[0.25582612 0.01564455 0.17119413 0.5573352 ]

[0.24297385 0.10829421 0.05900666 0.58972527]

"""
