import os
from datetime import datetime
from glob import glob

import numpy as np
import xgboost as xgb

from src.utils.bh_data_parser import BHParser
from src.utils.metadata_utils import get_weather_data

class Predictor:
    def __init__(self, club_name):
        self.club_name = club_name
        self.model = self.load_model()

    def load_model(self):
        path = f"models/{self.club_name}/*"
        model_path = glob(os.path.join(path))

        # Load the XGBoost model
        model = xgb.Booster()
        model.load_model(model_path[0])
        return model

    # Predict using the loaded model
    def predict(self, date):
        features, artists_data = self.get_features_at_date(date)
        if features:
            predictions = self.model.predict(features)
            return predictions, artists_data
        else:
            return None, None

    def get_features_at_date(self, date):
        bh_parser = BHParser(club_name="Berghain", club_page_url="https://www.berghain.berlin/en/program/archive")
        followers, artists_data = bh_parser.get_followers_at_date(date)
        weather = get_weather_data(city = "Berlin", start_date=date, end_date=date)
        temperature = weather.temperature.min()
        precipitation = weather.precipitation.max()

        features = np.array([followers, temperature, precipitation]).reshape(1, -1)

        if followers:
            features = xgb.DMatrix(features)
            return features, artists_data
        else:
            return None, None


if __name__ == "__main__":
    pred = Predictor(club_name="berghain")
    prediction, artists_data = pred.predict(datetime(2023, 8, 26).date())
