import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import re

CSV_FILE = 'signals.csv'

def get_current_price(ticker):
    try:
        # Fetching the very latest 1-minute interval price
        data = yf.download(ticker, period='1d', interval='1m', progress=False)
        return round(float(data['Close'].iloc[-1]), 2) if not data.empty else None
    except:
        return None

def get_historical_open(ticker, date_str):
    try:
        # Standardize date format to YYYY-MM-DD
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
    
    # Target columns for your dashboard
    cols = ['Ticker', 'Current_Price', 'Gain_Loss', 'Date_In', 'Price_In', 'Days_Held', 'Status']

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Ticker'] = df['Ticker'].astype(str).str.replace('"', '').str.strip().upper()
    else:
        df = pd.DataFrame(columns=cols)

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    for idx, row in df.iterrows():
        ticker = row['Ticker']
        
        # Ensure Price_In is always the OPENING price of the Date_In
        # If you manually changed Date_In to April 20, the script will fetch that open price
        if pd.isna(row.get('Price_In')) or row.get('Price_In') == 0:
            h_open = get_historical_open(ticker, row['Date_In'])
            if h_open: 
                df.at[idx, 'Price_In'] = h_open

        # Update Days Held from the Date_In
        date_in_dt = pd.to_datetime(row['Date_In'], errors='coerce')
        if pd.notnull(date_in_dt):
            df.at[idx, 'Days_Held'] = float((now - date_in_dt).days)

        if ticker in current_tickers:
            df.at[idx, 'Status'] = 'Active'
            curr_p = get_current_price(ticker)
            price_in = df.at[idx, 'Price_In']
            
            if curr_p and price_in and price_in > 0:
                df.at[idx, 'Current_Price'] = curr_p
                # Calculation: (Current Price - Opening Price) / Opening Price
                gain = ((float(curr_p) - float(price_in)) / float(price_in)) * 100
                df.at[idx, 'Gain_Loss'] = format_gain(gain)
        else:
            df.at[idx, 'Status'] = 'Closed'

    # Add New Tickers
    active_in_df = df[df['Status'] == 'Active']['Ticker'].tolist()
    for ticker in current_tickers:
        if ticker not in active_in_df:
            p_open = get_historical_open(ticker, today_str)
            curr_p = get_current_price(ticker)
            final_in = p_open if p_open else curr_p
            if final_in:
                new_row = {
                    'Ticker': ticker, 'Current_Price': curr_p, 'Gain_Loss': format_gain(0.0),
                    'Date_In': today_str, 'Price_In': final_in, 'Days_Held': 0.0, 'Status': 'Active'
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df = df.drop_duplicates(subset=['Ticker'], keep='first')
    df[cols].to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
