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
    
    # Load Existing Data First
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE, skipinitialspace=True)
            for col in df.columns:
                df[col] = df[col].astype(str).str.replace('"', '').str.strip()
            df['Ticker'] = df['Ticker'].str.upper()
        except:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    # Determine Ticker List: 
    # If user provided input, use that. Otherwise, use what is currently 'Active' in the CSV.
    if raw_input and raw_input.strip():
        current_tickers = [t.strip().upper() for t in raw_input.split() if t.strip()]
        is_manual_override = True
    else:
        if not df.empty and 'Status' in df.columns:
            current_tickers = df[df['Status'] == 'Active']['Ticker'].tolist()
        else:
            current_tickers = []
        is_manual_override = False
    
    cols = ['Ticker', 'Current_Price', 'Gain_Loss', 'Today_Date', 'Today_Gain', 'Date_In', 'Price_In', 'Days_Held', 'Status', 'Date_Out', 'Price_Out']
    for col in cols:
        if col not in df.columns: df[col] = None

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    for idx, row in df.iterrows():
        ticker = row['Ticker']
        if not ticker or ticker == 'NAN' or ticker == 'TICKER': continue

        try:
            p_in = float(row['Price_In'])
        except:
            p_in = 0.0

        if p_in == 0:
            h_open = get_historical_open(ticker, row['Date_In'])
            if h_open: 
                p_in = h_open
                df.at[idx, 'Price_In'] = h_open

        # Update Logic
        if ticker in current_tickers:
            df.at[idx, 'Status'] = 'Active'
            df.at[idx, 'Today_Date'] = today_str
            curr_p, today_open = get_price_data(ticker)
            
            if curr_p and p_in > 0:
                df.at[idx, 'Current_Price'] = curr_p
                total_gain = ((curr_p - p_in) / p_in) * 100
                df.at[idx, 'Gain_Loss'] = format_gain(total_gain)
                if today_open:
                    day_gain = ((curr_p - today_open) / today_open) * 100
                    df.at[idx, 'Today_Gain'] = format_gain(day_gain)

            date_in_dt = pd.to_datetime(row['Date_In'], errors='coerce')
            if pd.notnull(date_in_dt):
                df.at[idx, 'Days_Held'] = float((now - date_in_dt).days)
        
        elif is_manual_override:
            # Only exit tickers if the user explicitly provided a new list that excludes them
            if df.at[idx, 'Status'] == 'Active':
                curr_p, _ = get_price_data(ticker)
                df.at[idx, 'Status'] = 'Closed'
                df.at[idx, 'Date_Out'] = today_str
                df.at[idx, 'Price_Out'] = curr_p

    # Add New Tickers
    active_list = df[df['Status'] == 'Active']['Ticker'].tolist() if not df.empty else []
    for ticker in current_tickers:
        if ticker not in active_list:
            curr_p, today_open = get_price_data(ticker)
            if curr_p:
                new_row = {
                    'Ticker': ticker, 'Current_Price': curr_p, 'Gain_Loss': format_gain(0.0),
                    'Today_Date': today_str, 'Today_Gain': format_gain(0.0), 
                    'Date_In': today_str, 'Price_In': today_open, 
                    'Days_Held': 0.0, 'Status': 'Active'
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df = df.drop_duplicates(subset=['Ticker', 'Status'], keep='first')
    df[cols].to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
