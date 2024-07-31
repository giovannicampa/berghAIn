import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import mean_squared_error
from datetime import datetime
from src.utils.telegram_data_parser import queue_estimates
from src.data_exploration.data_exploration import get_features_historical, get_targets
import matplotlib.pyplot as plt
import functools as ft


class Trainer:
    def __init__(self, metrics: list, loss: list, model=str):
        models = {"knn": KNeighborsRegressor, "random_forest": RandomForestRegressor, "xgboost": xgb.XGBRegressor}
        self.model = models[model]()
        self.metrics = metrics
        self.loss = loss
        self.params = {}

        self.params[xgb] = {
            "objective": self.loss,  # Regression task
            "max_depth": 3,  # Maximum depth of a tree
            "learning_rate": 0.1,  # Step size for each iteration
            "n_estimators": 100,  # Number of boosting rounds
        }

        self.params[RandomForestRegressor] = {
            "bootstrap": True,
            "max_depth": 50,
            "min_samples_leaf": 2,
            "min_samples_split": 2,
            "min_weight_fraction_leaf": 0.05,
            "n_estimators": 10,
        }

        self.params[KNeighborsRegressor] = {
            "bootstrap": True,
            "max_depth": 50,
            "min_samples_leaf": 2,
            "min_samples_split": 2,
            "min_weight_fraction_leaf": 0.05,
            "n_estimators": 10,
        }

        self.param_grid = {}

        self.param_grid[RandomForestRegressor] = {
            "max_depth": [None, 1, 5, 20, 30, 50, 70],
            "n_estimators": [5, 10, 25, 50, 100, 150],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "bootstrap": [True, False],
            "min_weight_fraction_leaf": [0.0, 0.01, 0.05],
        }

        self.param_grid[xgb.XGBRegressor] = {
            "objective": [self.loss],  # Regression task
            "max_depth": [None, 1, 5, 20, 30, 50, 70],
            "learning_rate": [0.1, 0.01, 0.001],
            "n_estimators": [5, 10, 25, 50, 100, 150],
        }

        self.param_grid[KNeighborsRegressor] = {
            "n_neighbors": [
                1,
                3,
                7,
                11,
                15,
            ],  # Number of neighbors to use. Commonly, odd numbers are chosen to avoid ties.
            "weights": [
                "uniform",
                "distance",
            ],  # Uniform weights (all points have the same weight) or distance weights (inverse of the distance)
            "algorithm": ["auto", "ball_tree", "kd_tree", "brute"],  # Algorithm used to compute the nearest neighbors
            "leaf_size": [
                10,
                20,
                40,
            ],  # Leaf size passed to BallTree or KDTree. Can affect the speed of the query and the memory required.
            "p": [1, 2],  # Power parameter. 1: manhattan_distance (l1), 2: euclidean_distance (l2).
            "metric": ["euclidean", "manhattan", "minkowski", "chebyshev"],  # The distance metric to use.
        }

        self.features = ["followers", "hours_since_opening", "temperature"]

    def load_data(self, weather: bool = False, followers: bool = True, trends: bool = False):
        followers_by_date, weather_data_by_date, trends_data, temperature = get_features_historical(
            weather=weather, followers=followers, trends=trends
        )
        messages_time = get_targets()

        # temperature
        self.data = ft.reduce(
            lambda left, right: pd.merge(left, right, on="date"),
            [followers_by_date, messages_time, weather_data_by_date],
        )

        return self.data

    def prepare_data(self, data, target, scale_features=False):
        data = data[data.prediction != 0]
        X = data.drop(target, axis=1)[self.features]
        y = data[target]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        if scale_features is True:
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)

        dtrain = xgb.DMatrix(data=X_train, label=y_train)
        dtest = xgb.DMatrix(data=X_test, label=y_test)

        return X_train, X_test, y_train, y_test, dtrain, dtest

    def train(self, dtrain):
        # model = RandomForestRegressor(n_estimators=100, random_state=42)
        # model = RandomForestRegressor(**self.params[RandomForestRegressor], random_state=42)

        # Train the model
        self.model.fit(X_train, y_train)

        # model = xgb.train(params=self.params, dtrain=dtrain)
        return self.model

    def evaluate(self, model, X, dtest, y_test, subset):
        # Make predictions on the test set
        y_pred = model.predict(X)

        plt.style.use("ggplot")
        plt.title(f"Subset: {subset}")
        plt.plot(y_pred, label="Pred")
        plt.plot(y_test.values, label="True")
        plt.legend()
        plt.show()

        # Calculate and print the root mean squared error (RMSE)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        print(f"Root Mean Squared Error on {subset}: {rmse*60:.2f} minutes")

    def parameter_search(self, X_train, X_test, y_test, y_train, save, *args, **kwargs):
        # model = xgb.XGBRegressor(objective='reg:squarederror')
        # model = RandomForestRegressor()

        param_grid = self.param_grid[type(self.model)]

        # Perform grid search using cross-validation
        grid_search = GridSearchCV(
            estimator=self.model, param_grid=param_grid, scoring="neg_mean_squared_error", cv=2, verbose=10
        )
        grid_search.fit(X_train, y_train)

        best_params = grid_search.best_params_
        best_estimator = grid_search.best_estimator_
        print(best_params)

        if save:
            current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")
            model_filename = f"xgboost_model_{current_datetime}.model"
            best_estimator.save_model(os.path.join("models", model_filename))

        # Make predictions on the test set using the best estimator
        y_pred = best_estimator.predict(X_test)

        plt.style.use("ggplot")
        plt.plot(y_pred, label="Pred")
        plt.plot(y_test.values, label="True")
        plt.legend()
        plt.show()

        # Calculate and print the root mean squared error (RMSE)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        print(f"Root Mean Squared Error: {rmse*60:.2f} minutes")


if __name__ == "__main__":
    trainer = Trainer(loss="reg:squarederror", metrics=["msq"], model="xgboost")
    data = trainer.load_data(weather=True)
    X_train, X_test, y_train, y_test, dtrain, dtest = trainer.prepare_data(
        data, target="max_waiting_time", scale_features=True
    )
    model = trainer.train(dtrain)
    trainer.evaluate(model, X_test, dtest, y_test, subset="test")
    trainer.evaluate(model, X_train, dtrain, y_train, subset="train")
    trainer.parameter_search(X_train, X_test, y_test, y_train, save=False)
