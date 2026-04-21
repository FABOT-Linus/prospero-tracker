import pandas as pd
import yfinance as yf
from datetime import datetime, time
import os
import pytz

CSV_FILE = 'signals.csv'

def is_market_open():
    # Set timezone to Eastern Time (Market Time)
    tz = pytz.timezone('America/New_York')
    now = datetime.now(tz)
    
    # 1. Check for Weekends (5 = Saturday, 6 = Sunday)
    if now.weekday() >= 5:
        return False
        
    # 2. Check for Market Hours (9:30 AM to 4:00 PM)
    market_start = time(9, 30)
    market_end = time(16, 0)
    current_time = now.time()
    
    if current_time < market_start or current_time > market_end:
        return False
        
    return True

def get_price_data(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='1m', progress=False)
        if not data.empty:
            latest = round(float(data['Close'].iloc[-1]), 2)
            today_open = round(float(data['Open'].iloc[0]), 2)
            return latest, today_open
        return None, None
    except:
        return None, None

def format_gain(gain_val):
    indicator = "🟢 ▲" if gain_val >= 0 else "🔴 ▼"
    return f"{indicator} {abs(gain_val):.2f}%"

def main():
    # Check if we should even run
    # If it's a manual run from the UI, we let it through. 
    # Otherwise, we check the market clock.
    is_manual = os.getenv('PROSPERO_LIST', '') != ''
    
    if not is_market_open() and not is_manual:
        print("Market is currently closed. Skipping automated sync.")
        return

    # ... [Rest of your existing Add/Remove and Update logic remains the same] ...
    raw_input = os.getenv('PROSPERO_LIST', '')
    input_items = [t.strip().upper() for t in raw_input.split() if t.strip()]
    
    tickers_to_activate = [t for t in input_items if not t.startswith('-')]
    tickers_to_exit = [t.lstrip('-') for t in input_items if t.startswith('-')]

    cols = ['Ticker', 'Current_Price', 'Gain_Loss', 'Today_Date', 'Today_Gain', 'Date_In', 'Price_In', 'Days_Held', 'Status', 'Date_Out', 'Price_Out']

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Ticker'] = df['Ticker'].astype(str).str.upper()
    else:
        df = pd.DataFrame(columns=cols)

    # (Keep the rest of your main() logic exactly as I sent in the last update)
    # ... logic for adding/removing/updating ...
    # [Final save to CSV]
    df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
