import os
from datetime import datetime
from glob import glob

import numpy as np
import xgboost as xgb

from src.utils.bh_data_parser import BHParser


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
        features = self.get_features_at_date(date)
        if features:
            predictions = self.model.predict(features)
            return predictions
        else:
            return None

    def get_features_at_date(self, date):
        bh_parser = BHParser(club_name="Berghain", club_page_url="https://www.berghain.berlin/en/program/archive")
        followers = bh_parser.get_followers_at_date(date)

        if followers:
            features = xgb.DMatrix(np.array(followers).reshape(1, -1))
            return features
        else:
            return None


if __name__ == "__main__":
    pred = Predictor(club_name="berghain")
    prediction = pred.predict(datetime(2023, 8, 26).date())
