import os
from datetime import datetime
import time

import numpy as np
import pandas as pd
import telebot

from src.inference.predict import Predictor


BOT_TOKEN = os.environ["BOT_TOKEN"]
bot = telebot.TeleBot(BOT_TOKEN)
chat_id = "33014672"

pred = Predictor(club_name="berghain")


def generate_text(predicted_hours: np.array, artists_data: pd.DataFrame, features: dict) -> str:
    if predicted_hours is not None:
        reply = ""
        if predicted_hours >= 5:
            waiting_time_comment = "higher than usual"
        elif predicted_hours < 5:
            waiting_time_comment = "lower than usual"

        artist_summary = "🎶 <b>Today:</b>\n\n"

        # Group by location and iterate over the groups
        for location, group in artists_data.groupby("location"):
            artist_summary += f"📍 <b>{location}</b>:\n"
            for _, row in group.iterrows():
                # Ensure soundcloud_url is valid (replace NaN with an empty string or a fallback message)
                soundcloud_url = row["soundcloud_url"] if pd.notna(row["soundcloud_url"]) else "#"
                link_text = soundcloud_url if soundcloud_url != "#" else "No link available"

                artist_summary += f"{row['name']} <a href='{soundcloud_url}'>{link_text}</a>\n"
            artist_summary += "\n"

        if predicted_hours[0] > 1:
            waiting_time = f"{predicted_hours[0]:.2f} h"
        else:
            waiting_time = f"less than 1 hour"

        waiting_str = f"⏳ Max estimated waiting time: {waiting_time} ({waiting_time_comment})\n\n"

        # Extract weather info
        temperature = features["features_dict"].get("temperature", "N/A")
        precipitation = features["features_dict"].get("precipitation", "N/A")

        # Choose weather emoji based on temperature
        if temperature != "N/A":
            if temperature < 5:
                temp_emoji = "❄️"
            elif 5 <= temperature < 10:
                temp_emoji = "🌝"
            else:
                temp_emoji = "🔥"
        else:
            temp_emoji = ""

        # Choose rain emoji based on precipitation probability
        if precipitation != "N/A":
            if precipitation == 0:
                rain_emoji = "🌵"  # No rain
            elif 0 < precipitation < 30:
                rain_emoji = "🌤️"  # Low probability
            elif 30 <= precipitation < 70:
                rain_emoji = "🌦️"  # Medium probability
            else:
                rain_emoji = "🌧️"  # High probability
        else:
            rain_emoji = ""

        weather_str = f"Temperature: {temperature}°C {temp_emoji}\n" f"Precipitation: {precipitation}% {rain_emoji}\n"

        reply += artist_summary
        reply += waiting_str
        reply += weather_str
    else:
        reply = "🚫 No predictions for tonight"

    return reply


@bot.message_handler(commands=["start", "hello"])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")


def send_prediction(chat_id_to_send):
    try:
        predicted_hours, features, artists_data = pred.predict(date=datetime.today().date())

        artists_data.sort_values("followers", ascending=False, inplace=True)
        artists_data.reset_index(drop=True, inplace=True)

        reply = generate_text(predicted_hours, artists_data, features)

        bot.send_message(chat_id_to_send, reply, parse_mode="HTML")
    except Exception as e:
        print(f"Error during prediction: {e}")
        bot.send_message(chat_id_to_send, "An error occurred while generating the prediction.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    send_prediction(message.chat.id)


if __name__ == "__main__":
    while True:
        try:
            bot.polling()
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(15)
