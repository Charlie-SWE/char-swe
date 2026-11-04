import sqlite3
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

filepath = "../../data/gaffer.db"

def db_query(x_cols: str, y_col: str) -> pd.DataFrame:
    query = f"SELECT {x_cols}, {y_col} FROM PlayerGameStats"
    
    with sqlite3.connect(filepath) as conn:
        df = pd.read_sql_query(query, conn)
    
    return df

class XGBoostModel:
    def __init__(self, X: pd.DataFrame, y: pd.Series):
        self.X = X
        self.y = y
        self.model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1)
        
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X, self.y, test_size=0.2, random_state=42
        )

    def train_model(self):
        self.model.fit(self.X_train, self.y_train)
        # insert adding columns and rows as metadata

    def test_model(self) -> float:
        predictions = self.model.predict(self.X_test)
        mse = mean_squared_error(self.y_test, predictions)
        return mse

    def make_prediction(self, input_features: pd.DataFrame):
        return float(self.model.predict(input_features))

    def save_model(self, filepath: str = 'player_goals_xgb.json'):
        self.model.save_model(filepath)
        # insert saving columns and rows as metadata (or somewhere in src)
