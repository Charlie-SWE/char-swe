from src.components.Layout import frame
from nicegui import ui
import pandas as pd
import sqlite3
from src.xgboost.xgboost_model import XGBoostModel

DB_PATH = 'data/gaffer.db'

AVAILABLE_STATS = [
    'goals', 'assists', 'minutes_played', 'shots', 'shots_on_goal',
    'penalty_shot_goals', 'penalty_shot_attempts', 'fouls', 
    'yellow_cards', 'red_cards', 'saves', 'goals_against'
]

x_checkboxes = {}
prediction_inputs = {}

def fetch_data(x_cols: list, y_col: str):
    conn = sqlite3.connect(DB_PATH)
    columns = x_cols + [y_col]
    query = f"SELECT {', '.join(columns)} FROM PlayerGameStats"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df[x_cols], df[[y_col]]

def execute_pipeline(y_select, result_display):
    x_cols = [col for col, cb in x_checkboxes.items() if cb.value]
    y_col = y_select.value
    
    if not x_cols or not y_col: return
        
    if y_col in x_cols:
        ui.notify('Y variable cannot match any X variable', type='negative')
        return

    try: # tries to fetch from db and train model
        X_df, y_df = fetch_data(x_cols, y_col)
        
        if X_df.empty:
            ui.notify('Query returned no results', type='negative')
            return

        model = XGBoostModel(X_df, y_df)
        model.train_model()
        
        input_data = {col: [prediction_inputs[col].value] for col in x_cols}
        input_features = pd.DataFrame(input_data)
        
        prediction = model.make_prediction(input_features)

        result_display.set_text(f"Predicted {y_col}: {prediction:.4f}")
        ui.notify('Prediction successful!', type='positive')
        
    except Exception as e:
        ui.notify(f'An error occurred: {e}', type='negative')


def init():
    @ui.page('/xgboost')
    def xgboost_page():
        frame()
        ui.label("XGBoost").classes("text-4xl font-bold")
        
        x_checkboxes.clear()
        prediction_inputs.clear()
        with ui.column().classes('w-full max-w-6xl mt-6'):
            with ui.row().classes('w-full gap-8 items-start'):
                
                # column 1: x variables
                with ui.column().classes('flex-1'):
                    ui.label('1. Select X Variables').classes('text-xl font-semibold mb-2')
                    for stat in AVAILABLE_STATS:
                        x_checkboxes[stat] = ui.checkbox(stat, on_change=lambda: dynamic_input_section.refresh())
                        
                # column 2: y variable
                with ui.column().classes('flex-1'):
                    ui.label('2. Select Target Y Variable').classes('text-xl font-semibold mb-2')
                    y_select = ui.select(AVAILABLE_STATS, value='goals').classes('w-full')

                # column 3: results
                with ui.column().classes('flex-1'):
                    ui.label('3. Enter Inputs & Predict').classes('text-xl font-semibold mb-2')
                    
                    @ui.refreshable
                    def dynamic_input_section():
                        active_x = [col for col, cb in x_checkboxes.items() if cb.value]
                        prediction_inputs.clear()
                        
                        if not active_x:
                            ui.label('Select X variables to reveal prediction inputs.').classes('text-gray-500 italic mt-2')
                            return
                            
                        # Stack inputs vertically within this 3rd column
                        with ui.column().classes('gap-2 mb-4 w-full'):
                            for col in active_x:
                                prediction_inputs[col] = ui.number(label=col, value=0.0, format='%.2f').classes('w-full')
            
                        ui.button('Train Model & Predict', on_click=lambda: execute_pipeline(y_select, result_display)).classes('bg-blue-600 text-white w-full')

                    dynamic_input_section()
                    
                    result_display = ui.label('').classes('text-2xl font-bold text-green-700 mt-4')