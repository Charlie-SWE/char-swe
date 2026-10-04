import calendar
from datetime import datetime

import streamlit as st

from src.components.Colors import (
    PrimaryDarkHex,
    PrimaryLightHex,
    SecondaryDarkHex,
    SecondaryLightHex,
    SecondaryYellowHex,
)


def main():
    today = datetime.today()

    year = today.year
    month = today.month

    highlighted_days = {8, 15, 22} # for now this is just example days that show highlighted days

    month_name = calendar.month_name[month]
    month_calendar = calendar.monthcalendar(year, month)

    st.title("Calendar")
    st.subheader(f"{month_name} {year}")

    st.markdown(
        f"""
        <style>
            .calendar {{
                width: 100%;
                border-collapse: collapse;
                text-align: center;
            }}

            .calendar th {{
                background-color: {PrimaryDarkHex};
                color: white;
                padding: 12px;
            }}

            .calendar td {{
                border: 1px solid {SecondaryLightHex};
                padding: 20px 10px;
                height: 65px;
                position: relative;
            }}

            .today {{
                background-color: {PrimaryLightHex};
                font-weight: bold;
            }}

            .event-dot {{
                height: 8px;
                width: 8px;
                background-color: {SecondaryYellowHex};
                border-radius: 50%;
                display: block;
                margin: 5px auto 0 auto;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    html = '<table class="calendar">'

    html += "<tr>"
    for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        html += f"<th>{day_name}</th>"
    html += "</tr>"

    for week in month_calendar:
        html += "<tr>"

        for day in week:
            if day == 0:
                html += "<td></td>"
                continue

            cell_class = ""

            if day == today.day:
                cell_class = "today"

            html += f'<td class="{cell_class}">{day}'

            if day in highlighted_days:
                html += '<span class="event-dot"></span>'

            html += "</td>"

        html += "</tr>"

    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)

    st.caption("Yellow dots tell us about upcoming events.")


if __name__ == "__main__":
    main()