import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import re

CSV_FILE = 'signals.csv'

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
    raw_input = os.getenv('PROSPERO_LIST', '')
    input_items = [t.strip().upper() for t in raw_input.split() if t.strip()]
    
    # Separate tickers to ADD and tickers to REMOVE (-)
    tickers_to_add = [t for t in input_items if not t.startswith('-')]
    tickers_to_remove = [t.lstrip('-') for t in input_items if t.startswith('-')]

    cols = ['Ticker', 'Current_Price', 'Gain_Loss', 'Today_Date', 'Today_Gain', 'Date_In', 'Price_In', 'Days_Held', 'Status', 'Date_Out', 'Price_Out']

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Ticker'] = df['Ticker'].astype(str).str.upper()
    else:
        df = pd.DataFrame(columns=cols)

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    # 1. ADD NEW TICKERS (Additive logic)
    for ticker in tickers_to_add:
        # Only add if not already active
        if df.empty or not ((df['Ticker'] == ticker) & (df['Status'] == 'Active')).any():
            curr_p, today_open = get_price_data(ticker)
            if curr_p:
                new_row = {
                    'Ticker': ticker, 'Current_Price': curr_p, 'Gain_Loss': format_gain(0.0),
                    'Today_Date': today_str, 'Today_Gain': format_gain(0.0), 
                    'Date_In': today_str, 'Price_In': today_open, 
                    'Days_Held': 0, 'Status': 'Active'
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # 2. REMOVE TICKERS (The "-" logic)
    for ticker in tickers_to_remove:
        idx = df.index[(df['Ticker'] == ticker) & (df['Status'] == 'Active')]
        if not idx.empty:
            curr_p, _ = get_price_data(ticker)
            df.at[idx[0], 'Status'] = 'Closed'
            df.at[idx[0], 'Date_Out'] = today_str
            df.at[idx[0], 'Price_Out'] = curr_p

    # 3. UPDATE ALL ACTIVE TICKERS
    for idx, row in df.iterrows():
        if row['Status'] == 'Active':
            ticker = row['Ticker']
            curr_p, today_open = get_price_data(ticker)
            
            try:
                p_in = float(row['Price_In'])
            except:
                p_in = curr_p # Fallback if price_in is missing

            if curr_p:
                df.at[idx, 'Current_Price'] = curr_p
                df.at[idx, 'Today_Date'] = today_str
                # Total Gain calculation
                total_gain = ((curr_p - p_in) / p_in) * 100
                df.at[idx, 'Gain_Loss'] = format_gain(total_gain)
                # Today's Gain calculation
                if today_open:
                    day_gain = ((curr_p - today_open) / today_open) * 100
                    df.at[idx, 'Today_Gain'] = format_gain(day_gain)
                
                # Update Days Held
                date_in_dt = pd.to_datetime(row['Date_In'])
                df.at[idx, 'Days_Held'] = (now - date_in_dt).days

    df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
