#Integrating milli-Second Spot Data (/1000 - to less the burden) and classyifying them in Candle components

import requests
import pandas as pd
import numpy as np
import pytz

class SpotPrice:
    def __init__(self, identifier="NIFTY 50", name="NIFTY 50", timeout=5):
        self.url = "https://www.nseindia.com/api/chart-databyindex?index=NIFTY%2050&indices=true"
        self._session = requests.Session()
        self._session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5"
        }
        self._timeout = timeout
        self._session.get("https://www.nseindia.com/", timeout=5)

    def fetch_data(self):
        try:
            response = self._session.get(url=self.url, timeout=5)  # Increased timeout
            data = response.json()
            graph_data = data.get("grapthData", [])

            timestamps = [entry[0] / 1000 for entry in graph_data]  # Convert milliseconds to seconds
            date_timings = pd.to_datetime(timestamps, unit='s')  # Convert timestamps to datetime objects

            values = [entry[1] for entry in graph_data]
            df = pd.DataFrame({"Timestamp": date_timings, "Value": values})
            return df

        except Exception as ex:
            print("Error: {}".format(ex))
            self._session.get("https://www.nseindia.com/", timeout=self._timeout)  # to renew the session
            return pd.DataFrame()

    def create_candles(self, spot_data, interval_minutes=15):
        try:
            # Set 'Timestamp' as the index
            spot_data.set_index('Timestamp', inplace=True)

            # Resample data to create candles
            candles = spot_data.resample(f'{interval_minutes}T').agg({
                'Value': 'ohlc'
            })
            candles.columns = ['Open', 'High', 'Low', 'Close']
            candles.dropna(inplace=True)

            # Reset index to make 'Timestamp' a column again
            candles.reset_index(inplace=True)

            return candles

        except Exception as ex:
            print("Error creating candles: {}".format(ex))
            return pd.DataFrame()

# Testing the data
if __name__ == "__main__":
    obj = SpotPrice(identifier="NIFTY 50")
    spot_mtd = obj.fetch_data()
    candles = obj.create_candles(spot_mtd, interval_minutes=15)
    candles['Time'] = candles['Timestamp'].dt.time  # Extract time component
    candles['Date'] = candles['Timestamp'].dt.date  # Extract date component
 #   print("Classified Candle Components:-")
 #   print(candles.head())





#Importing Plotly and making candles
import plotly.graph_objects as go
# Extract day from the 'Time' column
day = candles.loc[0, 'Date'].strftime('%d-%m-%Y')

# Create candlestick trace
trace = go.Candlestick(x=candles.index,
                       open=candles['Open'],
                       high=candles['High'],
                       low=candles['Low'],
                       close=candles['Close'])

# Create figure and add trace
fig = go.Figure(data=[trace])

# Update layout with the day in the title
fig.update_layout(title=f'NIFTY 50 Candlestick Chart - {day}',
                  xaxis_title='Time',
                  yaxis_title='Price',
                  yaxis=dict(tickformat=",d"),  # Use comma as thousands separator and display full number
                  xaxis=dict(
                      tickvals=list(range(len(candles))),
                      ticktext=candles['Time'].apply(lambda x: x.strftime('%H:%M:%S'))
                  ))

# Add horizontal lines for support and resistance
fig.add_shape(type="line",
              x0=candles.index[1], y0=candles['High'][1],
              x1=candles.index[-1], y1=candles['High'][1],
              line=dict(color="Purple", width=2, dash="dash"),
              name="Resistance")
fig.add_shape(type="line",
              x0=candles.index[1], y0=candles['Low'][1],
              x1=candles.index[-1], y1=candles['Low'][1],
              line=dict(color="Black", width=2, dash="dash"),
              name="Support")


# Add annotations for labels
fig.update_layout(annotations=[
    dict(
        x=candles.index[-1],
        y=candles['High'][1],
        xref="x",
        yref="y",
        text="Resistance",
        showarrow=True,
        font=dict(
            color="Purple",
            size=12
        ),
        ax=-30,
        ay=-20
    ),
    dict(
        x=candles.index[-1],
        y=candles['Low'][1],
        xref="x",
        yref="y",
        text="Support",
        showarrow=True,
        font=dict(
            color="Black",
            size=12
        ),
        ax=-30,
        ay=20
    )
])

# Show the plot
#fig.show()



market_open = candles[candles['Time'].astype(str) == "09:15:00"]['Open'].iloc[0]
resistance = candles[candles['Time'].astype(str) == "09:15:00"]['High'].iloc[0]
support = candles[candles['Time'].astype(str) == "09:15:00"]['Low'].iloc[0]
current_spot = spot_mtd.iloc[-1, -1]
it_money = (market_open // 50) * 50
print(f'Current spot price: {current_spot}; '
      f'Market open: {market_open}; '
      f'Resistance bar: {resistance}; '
      f'Support bar: {support}; '
      f'Strike price for trade: {it_money}')


import pandas as pd

def Buy_Call(candles, resistance, support, it_money):
    buy_calls_data = []  # List to store buy call data
    buy_puts_data = []  # List to store buy put data
    prev_row = None  # Variable to store previous row data
    prev1_row = None 

    for index, row in candles.iterrows():
        if prev_row is not None and (prev_row['Open'] <= resistance):
            if row['Close'] > resistance:
                buy_calls_data.append([row['Time'], it_money, support])
        prev_row = row  # Update previous row data

    for index, row in candles.iterrows():
        if prev1_row is not None and (prev1_row['Open'] >= support):
            if row['Close'] < support:
                buy_puts_data.append([row['Time'], it_money, resistance])
        prev1_row = row  # Update previous row data

    buy_calls_df = pd.DataFrame(buy_calls_data, columns=['Time', 'Strike Price', 'Stoploss'])
    buy_puts_df = pd.DataFrame(buy_puts_data, columns=['Time', 'Strike Price', 'Stoploss'])

    return buy_calls_df, buy_puts_df

# Example usage:
# Assuming candles, resistance, support, and it_money are defined
buy_calls_df, buy_puts_df = Buy_Call(candles, resistance, support, it_money)
print(buy_calls_df)
print(buy_puts_df)







