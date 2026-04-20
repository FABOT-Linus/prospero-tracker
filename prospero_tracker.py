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

def get_open_price(ticker, date_str):
    try:
        data = yf.download(ticker, start=date_str, period='1d', progress=False)
        return round(float(data['Open'].iloc[0]), 2) if not data.empty else None
    except:
        return None

def main():
    raw_input = os.getenv('PROSPERO_LIST', '')
    current_tickers = [t.strip().upper() for t in raw_input.split() if t.strip()]
    if not current_tickers: return

    # Define the new column order
    cols = ['Ticker', 'Current_Price', 'Gain_%', 'Date_In', 'Price_In', 'Date_Out', 'Price_Out', 'Status', 'Days_Held']

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(columns=cols)

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    # Update Existing Rows
    for idx, row in df.iterrows():
        ticker = row['Ticker']
        date_in_dt = pd.to_datetime(row['Date_In'])
        end_date = now if row['Status'] == 'Active' else pd.to_datetime(row['Date_Out'])
        df.at[idx, 'Days_Held'] = (end_date - date_in_dt).days

        if row['Status'] == 'Active' and ticker not in current_tickers:
            p_out = get_current_price(ticker)
            if p_out:
                df.at[idx, 'Price_Out'], df.at[idx, 'Date_Out'], df.at[idx, 'Status'] = p_out, today_str, 'Closed'
                df.at[idx, 'Current_Price'] = p_out
                gain = ((p_out - row['Price_In']) / row['Price_In']) * 100
                df.at[idx, 'Gain_%'] = f"{'▲' if gain >= 0 else '▼'} {gain:.2f}%"
        elif row['Status'] == 'Active':
            curr_p = get_current_price(ticker)
            if curr_p:
                df.at[idx, 'Current_Price'] = curr_p
                gain = ((curr_p - row['Price_In']) / row['Price_In']) * 100
                df.at[idx, 'Gain_%'] = f"{'▲' if gain >= 0 else '▼'} {gain:.2f}%"

    # Add New Tickers
    for ticker in current_tickers:
        if ticker not in df[df['Status'] == 'Active']['Ticker'].values:
            p_open = get_open_price(ticker, today_str)
            curr_p = get_current_price(ticker)
            final_in = p_open if p_open else curr_p
            if final_in:
                new_row = {
                    'Ticker': ticker, 'Current_Price': curr_p, 'Gain_%': '0.00%', 
                    'Date_In': today_str, 'Price_In': final_in, 'Status': 'Active', 'Days_Held': 0
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Ensure final column order
    df = df[cols]
    df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
