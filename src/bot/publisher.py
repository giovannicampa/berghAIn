import os
from datetime import datetime
import time

import telebot

from src.inference.predict import Predictor


BOT_TOKEN = os.environ["BOT_TOKEN"]
bot = telebot.TeleBot(BOT_TOKEN)
chat_id = "33014672"


@bot.message_handler(commands=["start", "hello"])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")


def send_prediction():
    prediction, artists_data = pred.predict(date=datetime.today().date())

    artists_data.sort_values("followers", ascending=False, inplace=True)
    artists_data.reset_index(drop=True, inplace=True)

    if not prediction is None:
        if prediction >= 5:
            reply = f"🌟 Get ready for an electrifying night! The club's vibe is predicted to be off the charts tonight! 🕺🎉🎶\n\n"
            waiting_time_comment = "higher than usual"
        elif prediction < 5:
            reply = f"🌙 Tonight might be a bit more chill, but don't miss out on the fun! Join us for a great night at the club! 🍹🎵🎊\n\n"
            waiting_time_comment = "lower than usual"

        artist_summary = "Today:\n"

        # Group by location and iterate over the groups
        for location, group in artists_data.groupby("location"):
            artist_summary += f"at <b {location} </b>:\n"
            for _, row in group.iterrows():
                artist_summary += f"- {row['name']} <a href='{row['url']}'>{row['url']}</a>\n"
            artist_summary += "\n"

        if prediction[0] > 1:
            waiting_time = f"{prediction[0]:.2f} h"
        else:
            waiting_time = f"less than 1 hour"

        waiting_str = f"\nMax estimated waiting time: {waiting_time} ({waiting_time_comment})"

        reply += artist_summary
        reply += waiting_str
    else:
        reply = "No predictions for tonight"

    bot.send_message(chat_id, reply, parse_mode="HTML")


if __name__ == "__main__":
    pred = Predictor(club_name="berghain")

    while True:
        try:
            bot.polling()
        except:
            time.sleep(15)
