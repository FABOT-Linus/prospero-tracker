import pandas as pd
import yfinance as yf
from datetime import datetime
import os

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
    
    tickers_to_activate = [t for t in input_items if not t.startswith('-')]
    tickers_to_exit = [t.lstrip('-') for t in input_items if t.startswith('-')]

    cols = ['Ticker', 'Current_Price', 'Gain_Loss', 'Today_Date', 'Today_Gain', 'Date_In', 'Price_In', 'Days_Held', 'Status', 'Date_Out', 'Price_Out']

    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Ticker'] = df['Ticker'].astype(str).str.upper()
    else:
        df = pd.DataFrame(columns=cols)

    for col in cols:
        if col not in df.columns: df[col] = None

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    # 1. REACTIVATE OR ADD TICKERS
    for ticker in tickers_to_activate:
        # Check if ticker already exists in any status
        mask = (df['Ticker'] == ticker)
        if mask.any():
            idx = df.index[mask][0]
            # If it was closed, reopen it and clear exit data
            df.at[idx, 'Status'] = 'Active'
            df.at[idx, 'Date_Out'] = None
            df.at[idx, 'Price_Out'] = None
        else:
            # Brand new ticker
            curr_p, today_open = get_price_data(ticker)
            if curr_p:
                new_row = {
                    'Ticker': ticker, 'Current_Price': curr_p, 'Gain_Loss': format_gain(0.0),
                    'Today_Date': today_str, 'Today_Gain': format_gain(0.0), 
                    'Date_In': today_str, 'Price_In': today_open, 
                    'Days_Held': 0, 'Status': 'Active'
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # 2. MANUAL EXIT ONLY (The "-" Logic)
    for ticker in tickers_to_exit:
        mask = (df['Ticker'] == ticker) & (df['Status'] == 'Active')
        if mask.any():
            idx = df.index[mask][0]
            curr_p, _ = get_price_data(ticker)
            df.at[idx, 'Status'] = 'Closed'
            df.at[idx, 'Date_Out'] = today_str
            df.at[idx, 'Price_Out'] = curr_p

    # 3. UPDATE ALL ACTIVE TICKERS (Including the ones we just reactivated)
    for idx, row in df.iterrows():
        if row['Status'] == 'Active':
            ticker = row['Ticker']
            curr_p, today_open = get_price_data(ticker)
            
            try:
                p_in = float(row['Price_In'])
                if p_in == 0 or pd.isna(p_in): p_in = curr_p
            except:
                p_in = curr_p

            if curr_p:
                df.at[idx, 'Current_Price'] = curr_p
                df.at[idx, 'Today_Date'] = today_str
                # Performance calculations
                total_gain = ((curr_p - p_in) / p_in) * 100
                df.at[idx, 'Gain_Loss'] = format_gain(total_gain)
                if today_open:
                    day_gain = ((curr_p - today_open) / today_open) * 100
                    df.at[idx, 'Today_Gain'] = format_gain(day_gain)
                
                # Update Days Held
                date_in_dt = pd.to_datetime(row['Date_In'])
                df.at[idx, 'Days_Held'] = (now - date_in_dt).days

    # Ensure Date_Out and Price_Out are empty for Active rows
    df.loc[df['Status'] == 'Active', ['Date_Out', 'Price_Out']] = None
    
    df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    main()
