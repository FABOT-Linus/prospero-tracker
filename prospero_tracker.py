import pandas as pd
import yfinance as yf
from datetime import datetime
import os

CSV_FILE = 'signals.csv'

def get_price(ticker):
    try:
        data = yf.download(ticker, period='1d', interval='1m', progress=False)
        return round(float(data['Close'].iloc[-1]), 2) if not data.empty else None
    except:
        return None

def main():
    raw_input = os.getenv('PROSPERO_LIST', '')
    current_tickers = [t.strip().upper() for t in raw_input.split() if t.strip()]
    if not current_tickers: return

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(columns=['Ticker', 'Date_In', 'Price_In', 'Date_Out', 'Price_Out', 'Status', 'Days_Held', 'Gain_%'])

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    # Update Existing Rows
    for idx, row in df.iterrows():
        ticker = row['Ticker']
        date_in = pd.to_datetime(row['Date_In'])
        
        # Calculate Days Held
        end_date = now if row['Status'] == 'Active' else pd.to_datetime(row['Date_Out'])
        df.at[idx, 'Days_Held'] = (end_date - date_in).days

        # Close position if ticker is missing from current list
        if row['Status'] == 'Active' and ticker not in current_tickers:
            p_out = get_price(ticker)
            if p_out:
                df.at[idx, 'Price_Out'], df.at[idx, 'Date_Out'], df.at[idx, 'Status'] = p_out, today_str, 'Closed'
                gain = ((p_out - row['Price_In']) / row['Price_In']) * 100
                df.at[idx, 'Gain_%'] = f"{'▲' if gain >= 0 else '▼'} {gain:.2f}%"

        # Update Live Gain for Active Tickers
        elif row['Status'] == 'Active':
            current_p = get_price(ticker)
            if current_p:
                gain = ((current_p - row['Price_In']) / row['Price_In']) * 100
                df.at[idx, 'Gain_%'] = f"{'▲' if gain >= 0 else '▼'} {gain:.2f}%"

    # Add New Tickers
    for ticker in current_tickers:
        if ticker not in df[df['Status'] == 'Active']['Ticker'].values:
            p_in = get_price(ticker)
            if p_in:
                new_row = {'Ticker': ticker, 'Date_In': today_str, 'Price_In': p_in, 'Status': 'Active', 'Days_Held': 0, 'Gain_%': '0.00%'}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
