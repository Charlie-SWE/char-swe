from nicegui import ui
from src.components.Layout import frame

def init():
    @ui.page('/xgboost')
    def xgboost_page():
        frame()
        ui.label("XGBoost").classes("text-4xl font-bold")
        
        # TODO:
        # Can make XGBoost model using sql database fetch from view_data
        # Will also fetch weather data 
        # Dropdown for y variable
        # Checkboxes for x variables
            
        # ENSURE:
        # Framework will accept model as file
        # Ability to see data columns of trained models