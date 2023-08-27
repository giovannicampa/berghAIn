import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import glob
import pandas as pd
import os
import re
import numpy as np
from datetime import timedelta

# List of number words

words_hours = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "half": 0.5}

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

location_time = {"kiosk": 1, "hellweg": 2}
distance_time_multiplier = 2/60 # where 2 is [min/meter]


def parse_telegram_chat_export(file_path):
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
                timestamp = pd.Timestamp(timestamp["title"])
                messages_list.append({"sender": sender, "text": text, "timestamp": timestamp})

    return pd.DataFrame(messages_list)


def read_all_msgs():
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


def infer_duration_from_location(location, text):

    queue_duration = location_time[location]

    match_meters = re.search(r"(\d+)\s*meters", text)
    match_m = re.search(r"(\d+)\s*m", text)
    if match_m or match_meters:
        distance = np.average([int(dist) for dist in re.findall(r"\d+", text)])
    else:
        distance = 0

    queue_duration += distance*distance_time_multiplier

    return queue_duration


def queue_estimate_from_text(text: str) -> int:
    if not isinstance(text, str):
        return 0
    
    text = text.lower()

    match_hours = re.search(r"(\d+)\s*hour", text)
    match_hrs = re.search(r"(\d+)\s*hrs", text)
    match_h = re.search(r"(\d+)\s*h", text)

    match_minutes = re.search(r"(\d+)\s*minutes", text)
    match_mins = re.search(r"(\d+)\s*mins", text)


    if match_hrs or match_hours or match_h:
        list_hours = re.findall(r"\d+", text)
        list_hours += re.findall(r'\d+\.\d+', text)

        list_hours = [float(hour) for hour in list_hours if float(hour) < 8]

        list_hours += [number_int for number_str, number_int in words_hours.items() if number_str in text]
        avg_hour = max(0, np.mean(list_hours))
        return avg_hour


    elif match_mins or match_minutes:
        list_minutes = [int(minutes) for minutes in re.findall(r"\d+", text)]
        list_minutes += [number_int for number_str, number_int in words_minutes.items() if number_str in text]
        avg_hour = max(0, np.mean(list_minutes) / 60)
        return avg_hour

    elif any(loc in text for loc in ["kiosk", "späti", "spati"]):
        return infer_duration_from_location("kiosk", text)

    elif "hellweg" in text:
        return infer_duration_from_location("hellweg", text)

    else:
        return 0

def event_date(ts):

    if ts.hour > 0:
        return (ts - timedelta(days=1)).date()
    else:
        return ts.date()


def queue_estimates(path, log = False):

    if not os.path.exists(path):
        messages = read_all_msgs()
        messages.to_csv(path)
    else:
        messages = pd.read_csv(path, index_col=0, parse_dates=["timestamp"])

    condition_hour = messages.timestamp.apply(lambda x: x.hour > 22 or x.hour < 5)
    condition_year = messages.timestamp.apply(lambda x: x.year >= 2023)

    messages_time = messages.loc[(condition_hour & condition_year), :]

    messages_time["prediction"] = messages_time.text.apply(lambda x: queue_estimate_from_text(x))
    dates = []
    for i, row in messages_time.iterrows():
        dates.append(event_date(row.timestamp))
    messages_time["date"] = dates

    if log is True:
        for i, row in messages_time[messages_time.prediction > 0].iterrows():
            print(f"{row.text}, {row.prediction}\n")

    return messages_time


if __name__ == "__main__":
    path = "data/berghain/telegram/data.csv"

    messages_time = queue_estimates(path)

    plt.scatter(messages_time.timestamp, messages_time.prediction)
    plt.show()

    print("done")
