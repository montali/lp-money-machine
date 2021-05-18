import pandas as pd
import numpy as np
from nelder_mead import NelderMead


class StockOptimizator:
    def __init__(self, historical_data=None, investment_horizon_days=None, symbols=None):
        """Initializes the StockOptimizator object

        Args:
            historical_data (pd.DataFrame, optional): Historical stock data. Defaults to None.
            investment_horizon_days (int, optional): Days of investment horizon. Defaults to None.
            symbols (list[string], optional): Stock symbols to insert in the portfolio. Defaults to None.
        """
        # If the user didn't provide investment horizon and symbols, ask for 'em
        if investment_horizon_days == None or symbols == None:
            self.initialize_parameters()
        else:
            self.investment_horizon_days = investment_horizon_days
            self.symbols = symbols
        # Now, we fill up stocks_data with actual data
        self.stocks_analysis = pd.DataFrame(columns=[
            "Name", "PredictionsFromDate", "PredictionsToDate", "OpenPrice", "Risk", "Prediction"])
        historical_data = historical_data.dropna()
        self.historical_data = historical_data
        self.stocks_data = {}
        for symbol in self.symbols:
            try:
                self.stocks_data[symbol] = historical_data[historical_data.Name == symbol]
                self.stocks_data[symbol] = self.stocks_data[symbol].rename(
                    columns={'close': '4. close', 'date': 'index'})  # Renaming to keep compliance with AlphaVantage
                self.stocks_data[symbol] = self.stocks_data[symbol][[
                    'index', '4. close']]  # Only keeping the columns we need
            except IndexError:
                print(
                    f"Index {symbol} doesn't have sufficient historical data for the provided horizon, it will be skipped")

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
            self.symbols = ["AAPL", "MSFT", "GOOGL"]
        else:
            symbols_string.strip()
            self.symbols = symbols_string.split(',')

    def predict_stock_return(self, data, days_from_now):
        """Predicts the return and risk over the investment horizon.
        Should normally utilize a timeseries analysis tool, but in this numpy-pure version it just returns
        the risk and current price.

        Args:
            close_prices (Pandas DataFrame): Time series containing the closing prices
            days_from_now (int): Investment horizon

        Returns:
            tuple: Return forecast, risk forecast
        """
        risk = abs(
            np.std(data["4. close"]))
        return data["4. close"].iloc[-1].item(), risk

    def analyse_stocks(self):
        """Creates a stocks_analysis DataFrame containing the informations needed by the optimization algorithm
        """
        for symbol, data in self.stocks_data.items():
            close_date = data["index"].iloc[-1]
            try:
                open_date = data["index"].iloc[-self.investment_horizon_days]
                open_price = data["4. close"].iloc[-self.investment_horizon_days].item()
                prediction, risk = self.predict_stock_return(
                    data, self.investment_horizon_days)

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
        return -sum

    def optimize(self, reflection_parameter=1, expansion_parameter=2, contraction_parameter=0.1, shrinkage_parameter=0.5, max_iterations=15, shift_coefficient=0.05):
        print("Starting optimization...")
        self.nm = NelderMead(len(self.symbols), self.objective_function, 1, reflection_parameter, expansion_parameter,
                             contraction_parameter, shrinkage_parameter, max_iterations, shift_coefficient)
        self.nm.initialize_simplex()
        results = self.nm.fit(0.0001)  # Stop when std_dev is 0.0001
        print("Optimization completed!")
        money = 0
        for i in range(len(self.symbols)):
            print(
                f"The stock {self.symbols[i]} should be {round(results[i]*100,2)}% of your portfolio")
            money += ((1000*results[i])/(self.stocks_analysis["OpenPrice"].iloc[i])
                      * self.stocks_analysis["Prediction"].iloc[i])
        print(f"The predicted return for a 1000$ investment is {money}")


if __name__ == "__main__":
    historical_data = pd.read_csv('all_stocks_5yr.csv')
    op = StockOptimizator(historical_data=historical_data)
    op.analyse_stocks()
    op.optimize()
