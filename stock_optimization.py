import pandas as pd
import numpy as np
from prophet import Prophet
from art import *
import NelderMead


# We first import the historical data from CSV
historical_data = pd.read_csv('all_stocks_5yr.csv')
historical_data = historical_data.dropna()

# Then, we can make the user choose an investment horizon
tprint("lp-money-machine")
investment_horizon_days = input(
    "Welcome. Please, insert an investment horizon in days: ")


def create_prophet_dataframe(stock_data):
    """Creates a Prophet-compatible dataframe. Needed because Prophet expects data in a given shape

    Args:
        stock_data (Pandas dataframe): Historical stock data

    Returns:
        Pandas dataframe: Prophet-compatible dataframe
    """
    prophet_df = pd.DataFrame()
    prophet_df["ds"] = stock_data["date"]
    prophet_df["y"] = stock_data["close"]
    return prophet_df


def predict_stock_return(close_prices, days_from_now):
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
    forecast = estimator.predict(future)
    risk = abs(np.std(forecast["yhat"].iloc[-investment_horizon_days:]))
    return forecast["yhat"].iloc[-1], risk


# We can now create a Pandas dataframe that will contain our results
stocks_analysis = pd.DataFrame(columns=[
                               "Name", "PredictionsFromDate", "PredictionsToDate", "OpenPrice", "Risk", "Prediction"])
symbols = historical_data["Name"].unique()

for symbol in tqdm(symbols):
    open_date = historical_data[historical_data.Name == symbol]["date"].iloc[0]
    try:
        close_date = historical_data[historical_data.Name ==
                                     symbol]["date"].iloc[-1]
        # We take the closing price of yesterday as buying price
        open_price = historical_data[historical_data.Name ==
                                     symbol]["close"].iloc[-1]
        prediction, risk = predict_stock_return(create_prophet_dataframe(
            historical_data[historical_data.Name == symbol]), investment_horizon_days)
        stocks_analysis = stocks_analysis.append({
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
stocks_analysis["ror"] = (stocks_analysis["Prediction"] -
                          stocks_analysis["OpenPrice"])/stocks_analysis["Risk"]
stocks_analysis.sort_values("ror", ascending=False)


def objective_function(portfolio):
    """The objective function to be optimized

    Args:
        portfolio (np.array): Portfolio
    """
    sum = 0
    for i in range(portfolio):
        sum += stocks_analysis.iloc[i]["ror"] * portfolio[i]
    return sum


if __name__ == "__main__":
    nm = NelderMead(6, objective_function, 1, reflection_parameter=4, expansion_parameter=4,
                    contraction_parameter=0.05, shrinkage_parameter=0.05)
    nm.initialize_simplex()
    print(nm.fit(0.00001))
