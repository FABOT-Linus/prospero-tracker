import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import re

CSV_FILE = 'signals.csv'

def get_current_price(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='1m', progress=False)
        return round(float(data['Close'].iloc[-1]), 2) if not data.empty else None
    except:
        return None

def get_historical_open(ticker, date_str):
    try:
        clean_date = re.sub(r'[^0-9-]', '', str(date_str))
        data = yf.download(ticker, start=clean_date, period='1d', progress=False)
        return round(float(data['Open'].iloc[0]), 2) if not data.empty else None
    except:
        return None

def format_gain(gain_val):
    indicator = "🟢 ▲" if gain_val >= 0 else "🔴 ▼"
    return f"{indicator} {abs(gain_val):.2f}%"

def main():
    raw_input = os.getenv('PROSPERO_LIST', '')
    current_tickers = [t.strip().upper() for t in raw_input.split() if t.strip()]
    
    cols = ['Ticker', 'Current_Price', 'Gain_Loss', 'Date_In', 'Price_In', 'Days_Held', 'Status']

    if os.path.exists(CSV_FILE):
        try:
            # We use quoting=3 and skipinitialspace to handle messy CSVs from previous versions
            df = pd.read_csv(CSV_FILE, skipinitialspace=True)
            # Scrub every column to remove quotes or stray characters
            for col in df.columns:
                df[col] = df[col].astype(str).str.replace('"', '').str.strip()
            df['Ticker'] = df['Ticker'].str.upper()
        except Exception:
            df = pd.DataFrame(columns=cols)
    else:
        df = pd.DataFrame(columns=cols)

    # Ensure all required columns exist even if the CSV was corrupted
    for col in cols:
        if col not in df.columns:
            df[col] = None

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    for idx, row in df.iterrows():
        ticker = row['Ticker']
        if not ticker or ticker == 'NAN': continue

        # Convert Price_In to float safely
        try:
            p_in = float(row['Price_In'])
        except (ValueError, TypeError):
            p_in = 0.0

        # Backdating logic: If Price_In is 0, fetch the Open for that Date_In
        if p_in == 0:
            h_open = get_historical_open(ticker, row['Date_In'])
            if h_open: 
                p_in = h_open
                df.at[idx, 'Price_In'] = h_open

        # Update Days Held
        try:
            date_in_dt = pd.to_datetime(row['Date_In'], errors='coerce')
            if pd.notnull(date_in_dt):
                df.at[idx, 'Days_Held'] = float((now - date_in_dt).days)
        except:
            df.at[idx, 'Days_Held'] = 0.0

        # Performance Sync
        if ticker in current_tickers:
            df.at[idx, 'Status'] = 'Active'
            curr_p = get_current_price(ticker)
            if curr_p and p_in > 0:
                df.at[idx, 'Current_Price'] = curr_p
                gain = ((float(curr_p) - float(p_in)) / float(p_in)) * 100
                df.at[idx, 'Gain_Loss'] = format_gain(gain)
        else:
            df.at[idx, 'Status'] = 'Closed'

    # Add New Tickers
    active_list = df[df['Status'] == 'Active']['Ticker'].tolist()
    for ticker in current_tickers:
        if ticker not in active_list:
            p_open = get_historical_open(ticker, today_str)
            curr_p = get_current_price(ticker)
            final_in = p_open if p_open else curr_p
            if final_in:
                new_row = {
                    'Ticker': ticker, 'Current_Price': curr_p, 'Gain_Loss': format_gain(0.0),
                    'Date_In': today_str, 'Price_In': final_in, 'Days_Held': 0.0, 'Status': 'Active'
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Final cleanup of duplicates and sorting
    df = df.drop_duplicates(subset=['Ticker'], keep='first')
    df[cols].to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
