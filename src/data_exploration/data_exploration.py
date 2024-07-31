from datetime import datetime

from src.utils.metadata_utils import (
    get_google_trends_data,
    get_weather_data,
    temperature_trend,
    HOUR,
)
from src.utils.bh_data_parser import BHParser
from src.utils.telegram_data_parser import queue_estimates
import pandas as pd
import matplotlib.pyplot as plt

important_dates_csd = ["2021-7-24", "2022-7-23", "2023-7-22"]
important_dates_easter = [
    "2021-4-2",
    "2021-4-3",
    "2021-4-4",
    "2021-4-5",
    "2022-4-15",
    "2022-4-16",
    "2022-4-17",
    "2022-4-18",
    "2023-4-7",
    "2023-4-8",
    "2023-4-9",
    "2023-4-10",
]

important_dates = important_dates_csd + important_dates_easter
important_dates = [datetime.strptime(date, "%Y-%m-%d") for date in important_dates]


def get_features_historical(start_date=None, end_date=None, weather=False, followers=True, trends=False):
    # Follower data from saved files
    if followers:
        parser = BHParser()
        followers_by_date = parser.gather_artist_data(path_to_data=None)

        # Weather data for Berlin for the last year (365 days)
        city = "Berlin"
        if end_date is None:
            end_date = followers_by_date.date.max()
        if start_date is None:
            start_date = followers_by_date.date.min()

    temperature = temperature_trend(start_date=start_date, end_date=end_date)
    weather_data_by_date = pd.DataFrame()

    if weather:
        weather_data_by_date = get_weather_data(city, start_date, end_date)

    # Google Trends data
    search_term = "Berghain"
    trends_data = pd.DataFrame()
    if trends:
        trends_data = get_google_trends_data(
            search_term,
            #  timeframe=['2022-09-04 2022-09-10', '2022-09-18 2022-09-24'],
            geo="DE",
        )

    return followers_by_date, weather_data_by_date, trends_data, temperature


def get_targets():
    path = "data/berghain/telegram/data.csv"
    messages_time = queue_estimates(path)
    return messages_time


def plot_data(followers_by_date, weather_data_by_date, trends_data, temperature, messages_time):
    # Add christmas and NYE
    years_list = range(followers_by_date.date.min().year - 1, followers_by_date.date.max().year + 1)
    nye = [datetime.strptime(f"{year}-12-31", "%Y-%m-%d") for year in years_list]
    christmas = [datetime.strptime(f"{year}-12-24", "%Y-%m-%d") for year in years_list]

    important_dates += nye
    important_dates += christmas

    plt.style.use("ggplot")
    plt.rc("font", size=18)
    fig, (ax1, ax2) = plt.subplots(2, figsize=(10, 6))

    if not trends_data.empty:
        ax1.plot(trends_data.index, trends_data.Berghain, c="k")
    ax1.set_ylabel("Google searches", color="k")
    ax11 = ax1.twinx()
    ax11.plot(followers_by_date.date, followers_by_date.followers, c="g")
    ax11.set_ylabel("Soundcloud followers", color="g")

    ax1.scatter(messages_time.timestamp, messages_time.prediction, c="b")
    ax1.set_ylabel("Estimate [h]", c="b")

    for date in important_dates:
        ax1.axvline(x=date, color="blue", linestyle="--", linewidth=1)

    if not weather_data_by_date.empty:
        ax2.plot(weather_data_by_date.date, weather_data_by_date.precipitation, label=HOUR)
        ax2.set_ylabel("Precipitation @10pm [mm]", color="r")
    ax22 = ax2.twinx()
    ax22.plot(
        temperature.date,
        temperature.temperature,
        label=f"Hour: {HOUR}",
        c="b",
    )
    ax22.set_ylabel("Temperature @10pm [C]", c="b")
    plt.show()


if __name__ == "__main__":
    messages_time = get_targets()
    start_date = messages_time.timestamp.min().date()
    end_date = messages_time.timestamp.max().date()
    followers_by_date, weather_data_by_date, trends_data, temperature = get_features_historical(
        start_date=start_date, end_date=end_date, weather=True
    )
    plot_data(followers_by_date, weather_data_by_date, trends_data, temperature, messages_time)
