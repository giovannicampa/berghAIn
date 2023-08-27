import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error
from datetime import datetime
from src.utils.telegram_data_parser import queue_estimates
from src.data_exploration.data_exploration import get_features, get_targets
import matplotlib.pyplot as plt

class Trainer:

    def __init__(self, metrics: list, loss: list):
        self.metrics = metrics
        self.loss = loss
        self.params = {
            'objective': self.loss,  # Regression task
            'max_depth': 3,                   # Maximum depth of a tree
            'learning_rate': 0.1,             # Step size for each iteration
            'n_estimators': 100              # Number of boosting rounds
        }

    def load_data(self, weather: bool = True, followers: bool = True, trends: bool = True):
        followers_by_date, weather_data_by_date, trends_data = get_features()
        messages_time = get_targets()

        self.data = pd.merge(followers_by_date, messages_time, on ='date')

        return self.data

    def prepare_data(self, data, target):
        data = data[data.prediction != 0]
        X = data.drop(target, axis=1)["followers"]
        y = data[target]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        dtrain = xgb.DMatrix(data=X_train, label=y_train)
        dtest = xgb.DMatrix(data=X_test, label=y_test)

        return X_train, X_test, y_train, y_test, dtrain, dtest

    def train(self, dtrain):
        model = xgb.train(params=self.params, dtrain=dtrain)
        return model

    def evaluate(self, model, dtest, y_test, subset):
        # Make predictions on the test set
        y_pred = model.predict(dtest)

        plt.style.use("ggplot")
        plt.plot(y_pred, label = "Pred")
        plt.plot(y_test.values, label = "True")
        plt.legend()
        plt.show()

        # Calculate and print the root mean squared error (RMSE)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        print(f'Root Mean Squared Error on {subset}: {rmse*60:.2f} minutes')

    def parameter_search(self, X_train, X_test, y_test, y_train, save, *args, **kwargs):
        xgb_reg = xgb.XGBRegressor(objective='reg:squarederror')

        param_grid = {
            'max_depth': [1,2,3,4,5,6,7,8,9,10],
            'learning_rate': [0.1, 0.01, 0.001],
            'n_estimators': [5,10,25,50,100]
        }

        # Perform grid search using cross-validation
        grid_search = GridSearchCV(estimator=xgb_reg, param_grid=param_grid, scoring='neg_mean_squared_error', cv=5)
        grid_search.fit(X_train, y_train)


        best_params = grid_search.best_params_
        best_estimator = grid_search.best_estimator_
        print(best_params)

        if save:
            current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")
            model_filename = f'xgboost_model_{current_datetime}.model'
            best_estimator.save_model(os.path.join("models", model_filename))

        # Make predictions on the test set using the best estimator
        y_pred = best_estimator.predict(X_test)

        plt.style.use("ggplot")
        plt.plot(y_pred, label = "Pred")
        plt.plot(y_test.values, label = "True")
        plt.legend()
        plt.show()

        # Calculate and print the root mean squared error (RMSE)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        print(f'Root Mean Squared Error: {rmse*60:.2f} minutes')

if __name__ == "__main__":
    trainer = Trainer(loss = 'reg:squarederror', metrics=["msq"])
    data = trainer.load_data()
    X_train, X_test, y_train, y_test, dtrain, dtest = trainer.prepare_data(data, target = "prediction")
    model = trainer.train(dtrain)
    trainer.evaluate(model, dtest, y_test, subset = "test")
    trainer.evaluate(model, dtrain, y_train, subset = "train")
    trainer.parameter_search(X_train, X_test, y_test, y_train, save = True)
