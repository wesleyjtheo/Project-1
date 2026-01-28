"""
Fetch ETHUSDT data from Binance API for TPO analysis and backtesting
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time


def fetch_binance_klines(symbol='ETHUSDT', interval='1h', days=30, limit=1000, 
                         start_date=None, end_date=None):
    """
    Fetch historical kline/candlestick data from Binance API
    
    Parameters:
    -----------
    symbol : str
        Trading pair (e.g., 'ETHUSDT', 'BTCUSDT')
    interval : str
        Time interval: '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w'
    days : int
        Number of days of historical data to fetch (ignored if start_date and end_date are provided)
    limit : int
        Number of candles per request (max 1000)
    start_date : str, optional
        Custom start date in YYYY-MM-DD format for backtesting
    end_date : str, optional
        Custom end date in YYYY-MM-DD format for backtesting
    
    Returns:
    --------
    pd.DataFrame with columns: timestamp, open, high, low, close, volume
    """
    base_url = 'https://api.binance.com/api/v3/klines'
    
    # Handle custom date range or default days
    if start_date and end_date:
        # Parse custom dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999000)
        print(f"Custom date range: {start_date} to {end_date}")
    else:
        # Calculate start time - align to beginning of day (00:00:00 UTC)
        now = datetime.utcnow()
        end_dt = now.replace(hour=23, minute=59, second=59, microsecond=999000)
        start_dt = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    end_time = int(end_dt.timestamp() * 1000)
    start_time = int(start_dt.timestamp() * 1000)
    
    all_data = []
    current_start = start_time
    
    # Determine display text for date range
    if start_date and end_date:
        date_range_display = f"{start_date} to {end_date}"
    else:
        date_range_display = f"the last {days} days"
    
    print(f"Fetching {symbol} data with {interval} interval for {date_range_display}...")
    print(f"Date range: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} to {end_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    while current_start < end_time:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_time,
            'limit': limit
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
            
            all_data.extend(data)
            print(f"Fetched {len(data)} candles... Total: {len(all_data)}")
            
            # Update start time to the last candle's close time + 1ms
            current_start = data[-1][6] + 1
            
            # Rate limiting - Binance has weight limits
            time.sleep(0.1)
            
            # If we got less than limit, we've reached the end
            if len(data) < limit:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            break
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Keep only essential columns and convert types
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Add datetime components for TPO analysis
    df['date'] = df['timestamp'].dt.date
    df['time'] = df['timestamp'].dt.time
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    
    print(f"\nTotal candles fetched: {len(df)}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Data preview:\n{df.head()}\n")
    
    return df


def save_to_csv(df, symbol='ETHUSDT', interval='1h', custom_name=None):
    """
    Save DataFrame to CSV file
    
    Parameters:
    -----------
    df : pd.DataFrame
        Data to save
    symbol : str
        Trading pair name
    interval : str
        Time interval
    custom_name : str, optional
        Custom filename (without .csv extension)
    """
    if custom_name:
        filename = f"{custom_name}.csv"
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"BINANCE_{symbol}_{interval}_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    print(f"Data saved to: {filename}")
    return filename


def get_recent_data(symbol='ETHUSDT', interval='1h', hours=24):
    """
    Fetch recent data for quick testing
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    interval : str
        Time interval
    hours : int
        Number of recent hours to fetch
    """
    days = max(1, hours / 24)
    return fetch_binance_klines(symbol=symbol, interval=interval, days=days)


def fetch_multiple_timeframes(symbol='ETHUSDT', days=30):
    """
    Fetch data for multiple timeframes suitable for TPO analysis
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    days : int
        Number of days of historical data
    """
    timeframes = {
        '30m': '30 minute',
        '1h': '1 hour',
        '4h': '4 hour'
    }
    
    results = {}
    
    for interval, description in timeframes.items():
        print(f"\n{'='*60}")
        print(f"Fetching {description} data...")
        print(f"{'='*60}")
        
        df = fetch_binance_klines(symbol=symbol, interval=interval, days=days)
        results[interval] = df
        
        # Save to file
        filename = f"BINANCE_{symbol}_{interval}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved to: {filename}")
        
        time.sleep(1)  # Rate limiting between requests
    
    return results


# Available trading pairs
AVAILABLE_PAIRS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "PAXGUSDT"
]


def select_coin():
    """
    Prompt user to select a cryptocurrency to fetch
    """
    print("\n" + "="*60)
    print("SELECT CRYPTOCURRENCY TO FETCH")
    print("="*60)
    print("\nAvailable options:")
    
    for i, pair in enumerate(AVAILABLE_PAIRS, 1):
        asset = pair.replace('USDT', '')
        print(f"  {i}. {pair:12} ({asset})")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            idx = int(choice) - 1
            
            if 0 <= idx < len(AVAILABLE_PAIRS):
                selected = AVAILABLE_PAIRS[idx]
                print(f"\n✔ Selected: {selected}\n")
                return selected
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")
        except (ValueError, KeyboardInterrupt):
            print("\nInvalid input. Please enter a number between 1 and 5.")
        except EOFError:
            # Handle non-interactive environments
            print("\nNo input available. Using default: ETHUSDT")
            return 'ETHUSDT'


def select_timeframe():
    """
    Prompt user to select timeframe for data fetching
    """
    timeframe_options = [
        {"name": "30 Minutes", "interval": "30m"},
        {"name": "1 Hour", "interval": "1h"},
        {"name": "4 Hours", "interval": "4h"},
        {"name": "1 Day", "interval": "1d"},
    ]
    
    print("\n" + "="*60)
    print("SELECT TIMEFRAME")
    print("="*60)
    print("\nAvailable options:")
    
    for i, option in enumerate(timeframe_options, 1):
        print(f"  {i}. {option['name']:12} ({option['interval']})")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            idx = int(choice) - 1
            
            if 0 <= idx < len(timeframe_options):
                selected = timeframe_options[idx]
                print(f"\n✔ Selected: {selected['name']} ({selected['interval']})\n")
                return selected['interval']
            else:
                print("Invalid choice. Please enter a number between 1 and 4.")
        except (ValueError, KeyboardInterrupt):
            print("\nInvalid input. Please enter a number between 1 and 4.")
        except EOFError:
            # Handle non-interactive environments
            print("\nNo input available. Using default: 1 Hour")
            return '1h'


def select_date_range():
    """
    Prompt user to select date range for data
    Returns: days (int) - number of days to fetch
    """
    print("\n" + "="*60)
    print("SELECT DATE RANGE")
    print("="*60)
    print("\nAvailable options:")
    print("  1. Last 7 days")
    print("  2. Last 30 days")
    print("  3. Last 60 days")
    print("  4. Last 90 days")
    print("  5. Custom range (specify from and to dates)")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                print("\n✔ Selected: Last 7 days\n")
                return 7
            elif choice == '2':
                print("\n✔ Selected: Last 30 days\n")
                return 30
            elif choice == '3':
                print("\n✔ Selected: Last 60 days\n")
                return 60
            elif choice == '4':
                print("\n✔ Selected: Last 90 days\n")
                return 90
            elif choice == '5':
                print("\nEnter date range (format: YYYY-MM-DD)")
                from_date_str = input("From date: ").strip()
                to_date_str = input("To date: ").strip()
                
                # Parse dates
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
                to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
                
                # Calculate difference
                if to_date < from_date:
                    print("Error: 'To date' must be after 'From date'. Please try again.")
                    continue
                
                days = (to_date - from_date).days + 1
                
                if days > 365:
                    print("Error: Date range cannot exceed 365 days. Please try again.")
                    continue
                
                print(f"\n✔ Selected: {from_date_str} to {to_date_str} ({days} days)\n")
                return days
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")
        except ValueError as e:
            print(f"\nInvalid date format. Please use YYYY-MM-DD format (e.g., 2026-01-01).")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return 30
        except EOFError:
            # Handle non-interactive environments
            print("\nNo input available. Using default: 30 days")
            return 30


if __name__ == "__main__":
    # Example usage - customize as needed
    
    print("Binance Data Fetcher for TPO Analysis")
    print("=" * 60)
    
    # Let user select coin
    symbol = select_coin()
    
    # Let user select timeframe
    interval = select_timeframe()
    
    # Let user select date range
    days = select_date_range()
    
    df = fetch_binance_klines(symbol=symbol, interval=interval, days=days)
    
    # Optional: Save to CSV (uncomment if needed)
    # save_to_csv(df, symbol=symbol, interval=interval, custom_name=f"BINANCE_{symbol}, {interval.replace('h', ' hour').replace('m', ' min')}")
    
    # Option 2: Fetch multiple timeframes (uncomment to use)
    # results = fetch_multiple_timeframes(symbol='ETHUSDT', days=60)
    
    # Option 3: Fetch recent data for testing (uncomment to use)
    # df_recent = get_recent_data(symbol='ETHUSDT', interval='1h', hours=48)
    
    print("\n" + "=" * 60)
    print("Data fetch complete! Ready for TPO analysis.")
    print("=" * 60)
