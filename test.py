import sqlite3
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

conn = sqlite3.connect('data/gaffer.db')
query = """
    SELECT goals, minutes_played, shots, shots_on_goal, fouls, starter 
    FROM PlayerGameStats
"""
df = pd.read_sql_query(query, conn)
conn.close()

X = df[['minutes_played', 'shots', 'shots_on_goal', 'fouls', 'starter']]
y = df['goals']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=69)

model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1)
model.fit(X_train, y_train)

predictions = model.predict(X_test)
mse = mean_squared_error(y_test, predictions)
print(f"Mean Squared Error: {mse:.4f}")

# (e.g., 90 mins, 4 shots, 2 on goal, 1 foul, starter)
sample_player = pd.DataFrame([[90, 100, 100, 1, 1]], columns=X.columns)
demo_pred = model.predict(sample_player)
print(f"Predicted Goals: {demo_pred[0]:.2f}")