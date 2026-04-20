import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import sys

CSV_FILE = 'signals.csv'

def get_price(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='1m', progress=False)
        if data.empty: return None
        return round(float(data['Close'].iloc[-1]), 2)
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def main():
    # Get tickers from the environment variable
    raw_input = os.getenv('PROSPERO_LIST', '')
    if not raw_input:
        print("ERROR: No tickers provided.")
        sys.exit(1) # Exit with error if no tickers
        
    current_tickers = [t.strip().upper() for t in raw_input.split() if t.strip()]
    
    # Load or Create the CSV
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(columns=['Ticker', 'Date_In', 'Price_In', 'Date_Out', 'Price_Out', 'Status', 'Alpha'])

    now = datetime.now().strftime('%Y-%m-%d')

    # 1. Logic for Exits
    active_mask = df['Status'] == 'Active'
    for idx, row in df[active_mask].iterrows():
        if row['Ticker'] not in current_tickers:
            p_out = get_price(row['Ticker'])
            if p_out:
                df.at[idx, 'Price_Out'] = p_out
                df.at[idx, 'Date_Out'] = now
                df.at[idx, 'Status'] = 'Closed'
                ret = (p_out - row['Price_In']) / row['Price_In']
                df.at[idx, 'Alpha'] = round(ret * 100, 2)

    # 2. Logic for Entries
    for ticker in current_tickers:
        if ticker not in df[df['Status'] == 'Active']['Ticker'].values:
            p_in = get_price(ticker)
            if p_in:
                new_row = {'Ticker': ticker, 'Date_In': now, 'Price_In': p_in, 'Status': 'Active', 'Alpha': 0}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(CSV_FILE, index=False)
    print("Update complete.")

if __name__ == "__main__":
    main()
