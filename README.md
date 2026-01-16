# Stock Analyzer (Flask + MVC)

A lightweight web dashboard that tracks real-time stock prices and calculates daily volatility.

I built this project to transition from basic Python scripting to **Full-Stack Web Development**. My goal was to move away from pre-built UI tools (like Streamlit) and understand how to engineer a custom **MVC (Model-View-Controller)** architecture from scratch.

![Dashboard Screenshot](screenshot.png)

## 🛠️ Tech Stack
* **Backend:** Python (Flask)
* **Data Fetching:** `yfinance` API
* **Frontend:** HTML5 / CSS3 / Jinja2

## ⚙️ How It Works
1.  **User Input:** The user submits a ticker (e.g., AAPL).
2.  **Controller Logic:** Flask requests 5 days of history.
3.  **Data Processing:** Python calculates the percentage change.
4.  **View Rendering:** Jinja2 renders the HTML with conditional styling (Red/Green).

## 🚀 How to Run
```bash
pip install -r requirements.txt
python app.py
