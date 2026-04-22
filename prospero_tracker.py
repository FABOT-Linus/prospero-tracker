import pandas as pd
import yfinance as yf
from datetime import datetime, date
import os
import pytz
import re

CSV_FILE = 'signals.csv'

def clean_gain_for_sort(gain_str):
    """Extracts numerical value from string like '🟢 ▲ 5.55%' for sorting."""
    try:
        # Extract numbers and decimal points
        clean = re.findall(r"[-+]?\d*\.\d+|\d+", str(gain_str))
        val = float(clean[0])
        # If the string contains the red indicator or a minus sign, make it negative
        if "🔴" in str(gain_str) or "-" in str(gain_str):
            return -abs(val)
        return abs(val)
    except:
        return -999.0

def get_price_data(ticker):
    try:
        # Using period='1d' to get today's session
        data = yf.download(ticker, period='1d', interval='1m', progress=False, auto_adjust=True)
        if not data.empty:
            latest = round(float(data['Close'].iloc[-1]), 2)
            # Official Open is the first recorded price of the session
            today_open = round(float(data['Open'].iloc[0]), 2)
            return latest, today_open
        return None, None
    except:
        return None, None

def format_gain(gain_val):
    """Applies red/green emojis based on the numerical value."""
    if gain_val >= 0:
        return f"🟢 ▲ {abs(gain_val):.2f}%"
    else:
        # Negative numbers get the red indicator
        return f"🔴 ▼ {abs(gain_val):.2f}%"

def main():
    raw_input = os.getenv('PROSPERO_LIST', '')
    input_items = [t.strip().upper() for t in raw_input.split() if t.strip()]
    
    tickers_to_exit = [t.lstrip('-') for t in input_items if t.startswith('-')]
    tickers_to_activate = [t for t in input_items if not t.startswith('-')]

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(columns=['Ticker', 'Current_Price', 'Gain_Loss', 'Today_Date', 'Today_Gain', 'Date_In', 'Price_In', 'Days_Held', 'Status', 'Date_Out', 'Price_Out'])

    tz = pytz.timezone('America/New_York')
    today_str = datetime.now(tz).strftime('%Y-%m-%d')

    # 1. PROCESS EXITS
    for ticker in tickers_to_exit:
        mask = (df['Ticker'] == ticker) & (df['Status'] == 'Active')
        if mask.any():
            idx = df.index[mask][0]
            curr_p, _ = get_price_data(ticker)
            df.at[idx, 'Status'] = 'Closed'
            df.at[idx, 'Date_Out'] = today_str
            df.at[idx, 'Price_Out'] = curr_p

    # 2. ADD/REACTIVATE
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

    # 3. UPDATE ACTIVE
    for idx, row in df.iterrows():
        if row['Status'] == 'Active':
            curr_p, today_open = get_price_data(row['Ticker'])
            if curr_p:
                df.at[idx, 'Current_Price'] = curr_p
                df.at[idx, 'Today_Date'] = today_str
                date_in = pd.to_datetime(row['Date_In']).date()
                df.at[idx, 'Days_Held'] = float((date.today() - date_in).days)
                
                p_in = float(row['Price_In']) if pd.notnull(row['Price_In']) else curr_p
                df.at[idx, 'Gain_Loss'] = format_gain(((curr_p - p_in) / p_in) * 100)
                
                if today_open:
                    df.at[idx, 'Today_Gain'] = format_gain(((curr_p - today_open) / today_open) * 100)

    # 4. SORTING: Most Positive at Top, Most Negative at Bottom
    df['sort_val'] = df['Gain_Loss'].apply(clean_gain_for_sort)
    active_df = df[df['Status'] == 'Active'].sort_values(by='sort_val', ascending=False)
    closed_df = df[df['Status'] == 'Closed'].sort_values(by='Date_Out', ascending=False)
    
    final_df = pd.concat([active_df, closed_df]).drop(columns=['sort_val'])
    final_df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
