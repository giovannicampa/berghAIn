import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import glob
import pandas as pd
import os
import re
import numpy as np
from datetime import timedelta, datetime

from src.utils.reddit_data_parser import DataDownloaderReddit

# List of number words
words_hours = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "half": 0.5,
}

words_minutes = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
}

# Mapping of locations to queue duration time
LOCATION_TIME = {"kiosk": 1.5, "hellweg": 4.5, "karree": 3, "wriezener": 3, "metro": 6}

DISTANCE_TIME_FACTOR = 2 / 60  # where 2 is [min/meter]

MAX_WAITING_TIME = 10

weekday_names = {4: "Friday", 5: "Saturday", 6: "Sunday"}

KEYWORDS_HOURS = ["hour", "hrs", "h", "stunden"]
KEYWORDS_MINUTES = ["minutes", "mins", "minuten"]
KEYWORDS_CLUBS = ["rso", "kitkat", "sisyphos", "sisy", "renate", "about blank", "tresor"]

# Normalized waiting time.
# Keys are the hours since friday morning, values are the scaled waiting time.
relative_queue_friday = {
    22: 0.82,
    23: 1.0,
    24: 0.79,
    25: 0.61,
    26: 0.43,
    27: 0.3,
    28: 0.24,
    29: 0.17,
    35: 0.65,
    36: 0.55,
    37: 0.46,
    38: 0.35,
    39: 0.29,
    40: 0.25,
    41: 0.23,
    42: 0.22,
    43: 0.23,
    44: 0.22,
    45: 0.22,
    46: 0.22,
    47: 0.23,
    48: 0.27,
    49: 0.31,
    50: 0.35,
    51: 0.41,
    52: 0.48,
    53: 0.53,
    54: 0.57,
    55: 0.59,
    56: 0.61,
    57: 0.67,
    58: 0.74,
    59: 0.77,
    60: 0.68,
    61: 0.54,
    62: 0.40,
    63: 0.31,
    64: 0.14,
    65: 0.14,
}


def parse_telegram_chat_export(file_path: str) -> pd.DataFrame:
    """Parses telegram messages and returns them as a dataframe"""
    date_format = "%d.%m.%Y %H:%M:%S"
    messages_list = []

    with open(file_path, "r", encoding="utf-8") as file:
        chat_html = file.read()

        soup = BeautifulSoup(chat_html, "html.parser")

        messages = soup.find_all("div", class_="message")
        for message in messages:
            sender = message.find("div", class_="from_name")
            text = message.find("div", class_="text")
            timestamp = message.find("div", class_="date")

            if sender and text and timestamp:
                sender = sender.text
                sender = sender.replace("\n", "")
                text = text.text
                text = text.replace("\n", "")
                text = text.replace("       ", "")
                timestamp = pd.to_datetime(timestamp["title"][0:19], format=date_format)
                messages_list.append({"sender": sender, "text": text, "timestamp": timestamp})

    return pd.DataFrame(messages_list)


def read_all_msgs_reddit() -> pd.DataFrame:
    """Reads and returns the messages from the subreddit.
    If the data is not already stored in the database, it is downloaded"""

    subreddit = "Berghain_Community"
    downloader = DataDownloaderReddit([subreddit])
    data = downloader.get_saved_data_reddit()
    oldest = datetime.now() - timedelta(365 * 4)
    if data.empty:
        data = downloader.get_reddit_data(oldest)

    # Make data compatible with telegram one
    data.rename(columns={"date": "timestamp"}, inplace=True)
    return data


def read_all_msgs_telegram() -> pd.DataFrame:
    """Reads formats and returns the downloaded data from the telegram group."""

    messages = []

    paths = glob.glob("data/berghain/telegram/*.html")
    paths.sort()
    for path in paths:
        msg = parse_telegram_chat_export(path)
        messages.append(msg)

    messages = pd.concat(messages)
    messages.sort_values("timestamp", inplace=True)
    messages.reset_index(inplace=True, drop=True)
    return messages


def infer_duration_from_location(location: str, text: str) -> float:
    """Returns the estimate of the duration in hours.
    The length of the queue is often reported in reference to specific landmarks.
    These are mapped in LOCATION_TIME.
    Further, the length beyond said landmark is sometimes reported.
    This is calculated in terms of time and added to the original estimate.
    """

    queue_duration = LOCATION_TIME[location]

    match_meters = re.search(r"(\d+)\s*meters", text)
    match_m = re.search(r"(\d+)\s*m", text)
    if match_m or match_meters:
        distance = np.average([int(dist) for dist in re.findall(r"\d+", text)])
    else:
        distance = 0

    queue_duration += distance * DISTANCE_TIME_FACTOR

    return queue_duration


def queue_estimate_from_text(text: str) -> int:
    """Estimates the queue length in hours from the text messages"""
    if not isinstance(text, str):
        return 0

    text = text.lower()

    # Combine the keywords into a single regex pattern
    keyword_pattern_h = "|".join(KEYWORDS_HOURS)
    pattern_h = rf"(\d+)\s*({keyword_pattern_h})"
    match_hours = re.search(pattern_h, text)

    keyword_pattern_m = "|".join(KEYWORDS_MINUTES)
    pattern_m = rf"(\d+)\s*({keyword_pattern_m})"
    match_minutes = re.search(pattern_m, text)

    # Filter out reports for other clubs
    keyword_pattern_c = "|".join(KEYWORDS_CLUBS)
    pattern_c = rf"(\d+)\s*({keyword_pattern_c})"
    match_other_clubs = re.search(pattern_c, text)

    if match_hours and not match_other_clubs:
        list_hours = re.findall(r"\d+", text)
        list_hours += re.findall(r"\d+\.\d+", text)

        # Filters out unlikely reports
        list_hours = [float(hour) for hour in list_hours if float(hour) < 8]

        list_hours += [number_int for number_str, number_int in words_hours.items() if number_str in text]
        avg_hour = max(0, np.mean(list_hours))
        return avg_hour

    elif match_minutes and not match_other_clubs:
        list_minutes = [int(minutes) for minutes in re.findall(r"\d+", text)]
        list_minutes += [number_int for number_str, number_int in words_minutes.items() if number_str in text]
        avg_hour = max(0, np.mean(list_minutes) / 60)
        return avg_hour

    elif any(loc in text for loc in ["kiosk", "späti", "spati"]):
        return infer_duration_from_location("kiosk", text)

    elif any(loc in text for loc in ["hellweg"]):
        return infer_duration_from_location("hellweg", text)

    elif any(loc in text for loc in ["wriezener", "karree"]):
        return infer_duration_from_location("wriezener", text)

    else:
        return 0


def event_date(ts):
    if ts.hour > 0:
        return (ts - timedelta(days=1)).date()
    else:
        return ts.date()


def hour_since_opening(timestamp):
    """Calculates the hours passed since opening"""
    weekend_day = {4: 0, 5: 1, 6: 2}

    hour = weekend_day[timestamp.weekday()] * 24 + timestamp.hour
    return hour


def scale_prediction(row):
    """Given a waiting time estimate for a certain time, it fins the maximum time
    from a given
    """
    if row.hours_since_opening not in relative_queue_friday.keys():
        return row.prediction
    else:
        return min(row.prediction / relative_queue_friday[row.hours_since_opening], MAX_WAITING_TIME)


def queue_estimates(estimate_type: str = None, log=False) -> pd.DataFrame:
    """Estimates the waiting times from text data sources.
    The waiting time is expressed as the maximal waiting time. To get this,
    the function scale_prediction is used.

    The results are returned as a dataframe.
    Args:
        estimate_type: can be "telegram" or "reddit"
    """

    path_telegram = "data/berghain/telegram/data.csv"
    path_reddit = "data/berghain/reddit/data.csv"

    telegram_dict = {"path": path_telegram, "read_fun": read_all_msgs_telegram}
    reddit_dict = {"path": path_reddit, "read_fun": read_all_msgs_reddit}
    estimate_data = []

    if estimate_type == None:
        estimate_data.append(telegram_dict)
        estimate_data.append(reddit_dict)

    elif estimate_type == "reddit":
        estimate_data.append(reddit_dict)
    elif estimate_type == "telegram":
        estimate_data.append(telegram_dict)

    messages = []
    for estimate in estimate_data:
        path = estimate["path"]
        if not os.path.exists(path):
            data = estimate["read_fun"]()
            data.to_csv(path)
            messages.append(data)
        else:
            messages.append(pd.read_csv(path, index_col=0, parse_dates=["timestamp"]))
    messages = pd.concat(messages)

    condition_weekend = messages.timestamp.apply(lambda x: x.weekday() >= 4)
    messages_time = messages.loc[condition_weekend, :]

    # Actual estimate from the text messages
    messages_time["prediction"] = messages_time.text.apply(lambda x: queue_estimate_from_text(x))

    # Needed for the scaling
    messages_time["hours_since_opening"] = messages_time.timestamp.apply(lambda x: hour_since_opening(x))

    messages_time["calendar_week"] = messages_time.timestamp.apply(lambda x: x.isocalendar().week)
    messages_time["calendar_year"] = messages_time.timestamp.apply(lambda x: x.isocalendar().year)

    messages_time["max_waiting_time"] = messages_time.apply(lambda x: scale_prediction(x), axis=1)

    # Averaging the duration estimates
    for year in messages_time["calendar_year"].unique():
        messages_year = messages_time[messages_time["calendar_year"] == year]
        for week in messages_year.calendar_week.unique():
            # Monday is considered part of the weekend... welcome to Berlin
            is_monday = messages_year.timestamp.apply(lambda x: x.weekday() == 0)
            current_week_not_monday = (messages_year.calendar_week == week) & (~is_monday)
            next_week_monday = (messages_year.calendar_week == (week + 1)) & (is_monday)
            messages_year[(current_week_not_monday) | (next_week_monday)].max_waiting_time = messages_year[
                (current_week_not_monday) | (next_week_monday)
            ].max_waiting_time.mean()

    dates = []
    for i, row in messages_time.iterrows():
        dates.append(event_date(row.timestamp))
    messages_time["date"] = dates

    if log is True:
        for i, row in messages_time[messages_time.prediction > 0].iterrows():
            print(f"{row.text}, {row.prediction}\n")

    messages_time.reset_index(drop=True, inplace=True)

    messages_time_grouped = messages_time.groupby("date")["max_waiting_time"].mean().reset_index()
    return messages_time_grouped


if __name__ == "__main__":
    messages_time = queue_estimates()

    plt.style.use("ggplot")
    plt.rc("font", size=25)

    plt.scatter(
        messages_time.hours_since_opening, messages_time.prediction, alpha=0.3, s=70, label="Telegram estimates"
    )
    plt.scatter(relative_queue_friday.keys(), relative_queue_friday.values(), label="Google times")
    plt.xlabel("Time")
    plt.ylabel("Queue duration")
    plt.legend()
    plt.show()

    print("done")
