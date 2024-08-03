import os
from datetime import datetime
from glob import glob
from typing import Dict

import numpy as np
import json
import xgboost as xgb

from src.utils.bh_data_parser import BHParser
from src.utils.metadata_utils import get_weather_data


class Predictor:
    def __init__(self, club_name):
        self.club_name = club_name
        self.model = self.load_model()

    def load_model(self):
        path = f"models/{self.club_name}/*"
        model_paths = glob(os.path.join(path))

        model_paths.sort()
        model_dir = model_paths[-1]
        model_path = os.path.join(model_dir, "xgboost_model.model")

        # Load the XGBoost model
        model = xgb.Booster()
        model.load_model(model_path)

        with open(os.path.join(model_dir, "features.json"), "r") as json_file:
            self.required_features = json.load(json_file)

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

        features = []
        if "followers" in self.required_features:
            followers, artists_data = bh_parser.get_followers_at_date(date)
            features.append(followers)

        weather = get_weather_data(city="Berlin", start_date=date, end_date=date)
        if "temperature" in self.required_features:
            features.append(weather.temperature.min())

        if "precipitation" in self.required_features:
            features.append(weather.precipitation.max())

        features = np.array(features).reshape(1, -1)

        if followers:
            features = xgb.DMatrix(features)
            return features, artists_data
        else:
            return None, None


if __name__ == "__main__":
    pred = Predictor(club_name="berghain")
    prediction, artists_data = pred.predict(datetime(2023, 8, 26).date())
