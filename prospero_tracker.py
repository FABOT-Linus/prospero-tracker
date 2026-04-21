import pandas as pd
import yfinance as yf
from datetime import datetime
import os

CSV_FILE = 'signals.csv'

def get_current_price(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='1m', progress=False)
        return round(float(data['Close'].iloc[-1]), 2) if not data.empty else None
    except:
        return None

def get_historical_open(ticker, date_str):
    try:
        data = yf.download(ticker, start=date_str, period='1d', progress=False)
        return round(float(data['Open'].iloc[0]), 2) if not data.empty else None
    except:
        return None

def format_gain(gain_val):
    indicator = "🟢 ▲" if gain_val >= 0 else "🔴 ▼"
    return f"{indicator} {abs(gain_val):.2f}%"

def main():
    raw_input = os.getenv('PROSPERO_LIST', '')
    current_tickers = [t.strip().upper() for t in raw_input.split() if t.strip()]
    
    # Final desired column order
    cols = ['Ticker', 'Current_Price', 'Gain_Loss', 'Date_In', 'Price_In', 'Days_Held', 'Status', 'Date_Out', 'Price_Out']

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        # Fix messy data from previous versions (remove quotes/extra spaces)
        df['Ticker'] = df['Ticker'].astype(str).str.replace('"', '').str.strip().upper()
        # Ensure we only keep the earliest 'Date_In' for each ticker to fix duplicates
        df = df.sort_values(by=['Ticker', 'Date_In'])
        df = df.drop_duplicates(subset=['Ticker'], keep='first')
    else:
        df = pd.DataFrame(columns=cols)

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    # Update Current Tickers
    for idx, row in df.iterrows():
        ticker = row['Ticker']
        
        # 1. Force the Price_In to be the OPEN price of the Date_In
        if pd.isna(row['Price_In']) or row['Price_In'] == 0:
             h_open = get_historical_open(ticker, str(row['Date_In']))
             if h_open: df.at[idx, 'Price_In'] = h_open

        # 2. Update Days Held
        date_in_dt = pd.to_datetime(row['Date_In'])
        df.at[idx, 'Days_Held'] = (now - date_in_dt).days

        # 3. Handle Status Updates
        if ticker in current_tickers:
            df.at[idx, 'Status'] = 'Active'
            curr_p = get_current_price(ticker)
            if curr_p:
                df.at[idx, 'Current_Price'] = curr_p
                gain = ((curr_p - df.at[idx, 'Price_In']) / df.at[idx, 'Price_In']) * 100
                df.at[idx, 'Gain_Loss'] = format_gain(gain)
        else:
            if df.at[idx, 'Status'] == 'Active':
                p_out = get_current_price(ticker)
                df.at[idx, 'Status'] = 'Closed'
                df.at[idx, 'Date_Out'] = today_str
                df.at[idx, 'Price_Out'] = p_out
                df.at[idx, 'Current_Price'] = p_out
                gain = ((p_out - df.at[idx, 'Price_In']) / df.at[idx, 'Price_In']) * 100
                df.at[idx, 'Gain_Loss'] = format_gain(gain)

    # 4. Add Brand New Tickers
    known_tickers = df['Ticker'].tolist()
    for ticker in current_tickers:
        if ticker not in known_tickers:
            p_open = get_historical_open(ticker, today_str)
            curr_p = get_current_price(ticker)
            final_in = p_open if p_open else curr_p
            if final_in:
                new_row = {
                    'Ticker': ticker, 'Current_Price': curr_p, 'Gain_Loss': format_gain(0.0),
                    'Date_In': today_str, 'Price_In': final_in, 'Days_Held': 0, 'Status': 'Active'
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df[cols].to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
