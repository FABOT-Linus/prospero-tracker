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
    """Fetches the actual market open price for a specific historical date."""
    try:
        # We download 1 day of data starting at that specific date
        data = yf.download(ticker, start=date_str, period='1d', progress=False)
        if not data.empty:
            return round(float(data['Open'].iloc[0]), 2)
        return None
    except Exception as e:
        print(f"Error fetching open for {ticker} on {date_str}: {e}")
        return None

def format_gain(gain_val):
    arrow = "▲" if gain_val >= 0 else "▼"
    color = "green" if gain_val >= 0 else "red"
    return f"$\\color{{{color}}}{{\\text{{{arrow}}} \\space {abs(gain_val):.2f}\\%}}$"

def main():
    raw_input = os.getenv('PROSPERO_LIST', '')
    current_tickers = [t.strip().upper() for t in raw_input.split() if t.strip()]
    if not current_tickers: return

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
        
        # 1. Ensure Price_In is ALWAYS the Open price of the Date_In
        if pd.isna(row['Price_In']) or row['Price_In'] == 0 or row['Status'] == 'Active':
             # This locks the entry price to the historical OPEN of that day
             historical_open = get_historical_open(ticker, row['Date_In'])
             if historical_open:
                 df.at[idx, 'Price_In'] = historical_open

        # 2. Update Days Held
        date_in_dt = pd.to_datetime(row['Date_In'])
        end_date = now if row['Status'] == 'Active' else pd.to_datetime(row['Date_Out'])
        df.at[idx, 'Days_Held'] = (end_date - date_in_dt).days

        # 3. Handle Exits or Updates
        if row['Status'] == 'Active' and ticker not in current_tickers:
            p_out = get_current_price(ticker)
            if p_out:
                df.at[idx, 'Price_Out'], df.at[idx, 'Date_Out'], df.at[idx, 'Status'] = p_out, today_str, 'Closed'
                df.at[idx, 'Current_Price'] = p_out
                gain = ((p_out - df.at[idx, 'Price_In']) / df.at[idx, 'Price_In']) * 100
                df.at[idx, 'Gain_%'] = format_gain(gain)
        elif row['Status'] == 'Active':
            curr_p = get_current_price(ticker)
            if curr_p:
                df.at[idx, 'Current_Price'] = curr_p
                gain = ((curr_p - df.at[idx, 'Price_In']) / df.at[idx, 'Price_In']) * 100
                df.at[idx, 'Gain_%'] = format_gain(gain)

    # 4. Add New Tickers
    for ticker in current_tickers:
        if ticker not in df[df['Status'] == 'Active']['Ticker'].values:
            p_open = get_historical_open(ticker, today_str)
            curr_p = get_current_price(ticker)
            # If market isn't open yet, it might return None, so we use current as placeholder
            final_in = p_open if p_open else curr_p
            if final_in:
                new_row = {
                    'Ticker': ticker, 'Current_Price': curr_p, 'Gain_%': format_gain(0.0), 
                    'Date_In': today_str, 'Price_In': final_in, 'Status': 'Active', 'Days_Held': 0
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df = df[cols]
    df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
