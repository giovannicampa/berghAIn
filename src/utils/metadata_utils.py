import os

import pandas as pd
import requests
from pytrends.request import TrendReq

# Replace 'YOUR_API_KEY' with your actual API key from WeatherAPI
API_KEY = os.environ["WEATHER_API_KEY"]
CHUNK_SIZE = 35


def get_weather_data(city="Berlin", start_date="", end_date=""):
    base_url = "http://api.weatherapi.com/v1/history.json"
    weather_data = []

    while start_date <= end_date:
        # Calculate the end date for the current chunk
        chunk_end_date = min(end_date, start_date + pd.Timedelta(days=CHUNK_SIZE - 1))

        params = {
            "key": API_KEY,
            "q": city,
            "dt": start_date.strftime("%Y-%m-%d"),
            "end_dt": chunk_end_date.strftime("%Y-%m-%d"),
        }

        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            weather_data.extend(data["forecast"]["forecastday"])

        start_date += pd.Timedelta(days=CHUNK_SIZE)

    return weather_data


def get_google_trends_data(keyword, timeframe="today 12-m", geo="", gprop=""):
    pytrends = TrendReq(hl="en-US", tz=360)
    pytrends.build_payload([keyword], timeframe=timeframe, geo=geo, gprop=gprop)
    trends_data = pytrends.interest_over_time()
    return trends_data
