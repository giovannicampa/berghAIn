import os
import datetime
import time

import telebot

from src.inference.predict import Predictor


BOT_TOKEN = os.environ["BOT_TOKEN"]
bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start", "hello"])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")


@bot.message_handler(func=lambda message: True)
def respond_to_message(message):
    prediction = pred.predict(date=datetime.datetime.now().date())

    if not prediction is None:
        if prediction >= 5:
            prediction_text = (
                "🌟 Get ready for an electrifying night! The club's vibe is predicted to be off the charts tonight! 🕺🎉🎶"
            )
        elif prediction < 5:
            prediction_text = "🌙 Tonight might be a bit more chill, but don't miss out on the fun! Join us for a great night at the club! 🍹🎵🎊"
    else:
        prediction_text = "No predictions for tonight"

    bot.reply_to(message, prediction_text)


if __name__ == "__main__":
    pred = Predictor(club_name="berghain")

    while True:
        try:
            bot.polling()
        except:
            time.sleep(15)
