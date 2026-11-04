from nicegui import ui
from src.components.Layout import frame

def init():
    @ui.page('/xgboost')
    def xgboost_page():
        frame()
        ui.label("XGBoost").classes("text-4xl font-bold")
        