import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from pytrends.request import TrendReq

# Replace 'YOUR_API_KEY' with your actual API key from WeatherAPI
API_KEY = os.environ["WEATHER_API_KEY"]
CHUNK_SIZE = 35


# Sinusoid parameters
TEMP_MAX = 15.4  # Maximum value (peak)
TEMP_MIN = -3  # Minimum value (trough)

AVG_TMP = (TEMP_MAX + TEMP_MIN) / 2  # Average temperature
AMP = (TEMP_MAX - TEMP_MIN) / 2  # Curve amplitude

T = 365  # Period of the sinusoid


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
    trends_data["date"] = trends_data.index
    trends_data.reset_index(drop=True, inplace=True)
    return trends_data


def temperature_on_day(current_date) -> int:
    """
    Returns the temperature for a given day.
    Can be uses to generate training and inference data.
    """
    peak_day = datetime(current_date.year, 7, 15)  # Hottest day
    temperature = AMP * np.sin(2 * np.pi / T * ((current_date - peak_day).days + T / 4)) + AVG_TMP
    return temperature


def temperature_trend(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Generates the temperature trend for the given time interval.
    This is used for training purposes.
    """
    delta_days = (end_date - start_date).days  # How many days from start_date to the peak

    # Generate the list of dates
    date_list = []
    current_date = start_date
    for _ in range(delta_days):
        temperature = temperature_on_day(current_date)
        date_list.append({"date": current_date, "temperature": temperature})
        current_date += timedelta(days=1)

    date_list = pd.DataFrame(date_list)

    return date_list


if __name__ == "__main__":
    # Define the start and end dates
    start_date = datetime(2023, 4, 1)
    end_date = datetime(2025, 4, 1)

    trend = temperature_trend(start_date, end_date)
