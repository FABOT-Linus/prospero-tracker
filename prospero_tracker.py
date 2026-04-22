import pandas as pd
import yfinance as yf
from datetime import datetime, date
import os
import pytz

CSV_FILE = 'signals.csv'

def is_market_open():
    tz = pytz.timezone('America/New_York')
    now = datetime.now(tz)
    if now.weekday() >= 5: return False
    # Wider window (9:00 AM to 5:00 PM) to catch delayed GitHub runs
    return 9 <= now.hour < 17

def get_price_data(ticker):
    try:
        # Fetching 2 days of data ensures we always get a valid "Open" price
        data = yf.download(ticker, period='2d', interval='1m', progress=False)
        if not data.empty:
            latest = round(float(data['Close'].iloc[-1]), 2)
            # Get the open price from the most recent session
            today_open = round(float(data['Open'].iloc[-1]), 2)
            return latest, today_open
        return None, None
    except:
        return None, None

def format_gain(gain_val):
    indicator = "🟢 ▲" if gain_val >= 0 else "🔴 ▼"
    return f"{indicator} {abs(gain_val):.2f}%"

def main():
    raw_input = os.getenv('PROSPERO_LIST', '')
    is_manual = raw_input.strip() != ""
    
    if not is_market_open() and not is_manual:
        print("Market closed and no manual input. Skipping.")
        return

    input_items = [t.strip().upper() for t in raw_input.split() if t.strip()]
    tickers_to_activate = [t for t in input_items if not t.startswith('-')]
    tickers_to_exit = [t.lstrip('-') for t in input_items if t.startswith('-')]

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(columns=['Ticker', 'Current_Price', 'Gain_Loss', 'Today_Date', 'Today_Gain', 'Date_In', 'Price_In', 'Days_Held', 'Status', 'Date_Out', 'Price_Out'])

    today_str = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d')

    # ADD/REACTIVATE
    for ticker in tickers_to_activate:
        curr_p, today_open = get_price_data(ticker)
        if curr_p:
            mask = (df['Ticker'] == ticker)
            if mask.any():
                idx = df.index[mask][0]
                df.at[idx, 'Status'] = 'Active'
                df.at[idx, 'Date_Out'] = None
                df.at[idx, 'Price_Out'] = None
            else:
                new_row = {'Ticker': ticker, 'Status': 'Active', 'Date_In': today_str, 'Price_In': today_open}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # UPDATE ACTIVE
    for idx, row in df.iterrows():
        if row['Status'] == 'Active':
            curr_p, today_open = get_price_data(row['Ticker'])
            if curr_p:
                df.at[idx, 'Current_Price'] = curr_p
                df.at[idx, 'Today_Date'] = today_str
                
                # Math for Days Held
                date_in = pd.to_datetime(row['Date_In']).date()
                days_held = (date.today() - date_in).days
                df.at[idx, 'Days_Held'] = float(max(0, days_held))
                
                # Math for Gains
                p_in = float(row['Price_In']) if pd.notnull(row['Price_In']) else curr_p
                df.at[idx, 'Gain_Loss'] = format_gain(((curr_p - p_in) / p_in) * 100)
                if today_open:
                    df.at[idx, 'Today_Gain'] = format_gain(((curr_p - today_open) / today_open) * 100)

    df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
