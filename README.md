# 🏀 NBA Predictive Modeling & Betting Pipeline

This project is a complete, end-to-end machine learning and data pipeline for NBA sports betting. It ingests historical NBA statistics, trains probabilistic models to predict game outcomes, fetches real-world odds from bookmakers (like Polymarket and Superbet), and backtests the model's performance to find profitable Expected Value (EV) edges.

## 🚀 Core Features
* **Odds Ingestion:** Fetches and normalizes pregame Moneyline odds from traditional sportsbooks and prediction markets (Polymarket).
* **Walk-Forward Validation Training:** Uses chronological time-series splitting to train Logistic Regression and XGBoost models without data leakage.
* **Historical Backtester:** Simulates betting strategies based on a Minimum EV Edge threshold to calculate real-world Win Rate and R.O.I.
* **Arbitrage Scanner:** Scans the database for cross-bookmaker arbitrage opportunities where implied probabilities sum to less than 100%.

## 🛠️ Prerequisites & Setup

1. Make sure you have Python 3.9+ installed.
2. Clone this repository and navigate to the folder.
3. Install the required dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt

4. if u want to fetch more data use api key, get it at odds-api.io