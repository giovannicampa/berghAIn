from src.utils.metadata_utils import (
    get_google_trends_data,
    get_weather_data,
)
from src.utils.bh_data_parser import BHParser
from src.utils.telegram_data_parser import queue_estimates
import pandas as pd
import matplotlib.pyplot as plt

HOUR = 23


def get_features_historical():
    # Follower data from saved files
    parser = BHParser()
    followers_by_date = parser.gather_artist_data()

    # Weather data for Berlin for the last year (365 days)
    city = "Berlin"
    end_date = pd.Timestamp("2023-08-06")  # Replace with the current date or desired end date
    start_date = end_date - pd.DateOffset(years=1)  # Exactly one year before the end date

    weather_data = get_weather_data(city, start_date, end_date)
    weather_data_by_date = [
        {
            "date": pd.Timestamp(day["date"]),
            "precipitation": day["hour"][HOUR]["precip_mm"],
            "temperature": day["hour"][HOUR]["temp_c"],
        }
        for day in weather_data
        if len(day["hour"]) > 0
    ]
    weather_data_by_date = pd.DataFrame(weather_data_by_date)

    # Google Trends data
    search_term = "Berghain"
    trends_data = get_google_trends_data(
        search_term,
        #  timeframe=['2022-09-04 2022-09-10', '2022-09-18 2022-09-24'],
        geo="DE",
    )

    return followers_by_date, weather_data_by_date, trends_data

def get_targets():

    path = "data/berghain/telegram/data.csv"
    messages_time = queue_estimates(path)
    return messages_time

def plot_data(followers_by_date, weather_data_by_date, trends_data, messages_time):
    plt.style.use("ggplot")
    plt.rc("font", size=18)
    fig, (ax1, ax2) = plt.subplots(2, figsize=(10, 6))

    ax1.plot(trends_data.index, trends_data.Berghain, c="k")
    ax1.set_ylabel("Google searches", color="k")
    ax11 = ax1.twinx()
    ax11.plot(followers_by_date.date, followers_by_date.followers, c="g")
    ax11.set_ylabel("Soundcloud followers", color="g")

    ax2.plot(weather_data_by_date.date, weather_data_by_date.precipitation, label=HOUR)
    ax2.set_ylabel("Precipitation @10pm [mm]", color="r")
    ax22 = ax2.twinx()
    ax22.plot(
        weather_data_by_date.date,
        weather_data_by_date.temperature,
        label=f"Hour: {HOUR}",
        c="b",
    )
    ax22.set_ylabel("Temperature @10pm [C]", c="b")
    plt.show()


if __name__ == "__main__":
    followers_by_date, weather_data_by_date, trends_data = get_features_historical()
    messages_time = get_targets()
    plot_data(followers_by_date, weather_data_by_date, trends_data, messages_time)
