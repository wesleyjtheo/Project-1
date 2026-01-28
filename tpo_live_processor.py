"""
Live TPO (Market Profile) Processor with Binance Integration
Fetches data directly from Binance API and processes into TPO format
"""
import pandas as pd
import string
from decimal import Decimal, ROUND_FLOOR
from datetime import datetime, timedelta
import sys

# Import our fetch_data module
from fetch_data import fetch_binance_klines, get_recent_data


# ============================================================
# ASSET CONFIGURATION
# ============================================================
ASSET_TICK_SIZES = {
    "BTC": 100.0,
    "ETH": 3.0,
    "XRP": 0.0050,
    "SOL": 0.15,
    "BNB": 1.0,
    "PAXG": 5.0
}

# Available trading pairs
AVAILABLE_PAIRS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "PAXGUSDT"
]


class TPOProcessor:
    """
    TPO/Market Profile processor that works with live Binance data
    """
    
    def __init__(self, asset='ETH', tick_size=None, tpo_period='1h'):
        """
        Initialize TPO processor
        
        Parameters:
        -----------
        asset : str
            Asset symbol (BTC, ETH, XRP, SOL)
        tick_size : float, optional
            Override default tick size
        tpo_period : str
            TPO letter assignment period ('30m', '1h', etc.)
        """
        self.asset = asset.upper()
        self.tick_size = tick_size or ASSET_TICK_SIZES.get(self.asset, 1.0)
        self.tick_dec = Decimal(str(self.tick_size))
        self.tpo_period = tpo_period
        
        # Display decimals
        tick_decimals = max(0, -self.tick_dec.as_tuple().exponent)
        self.display_decimals = max(tick_decimals, 4) if self.asset == "XRP" else tick_decimals
        
        # Letters for TPO
        self.letters = list(string.ascii_uppercase + string.ascii_lowercase)
        
        print(f"✔ TPO Processor initialized for {self.asset}")
        print(f"  Tick Size: {self.tick_size}")
        print(f"  TPO Period: {self.tpo_period}")
        print(f"  Display Decimals: {self.display_decimals}")
    
    def prepare_data(self, df):
        """
        Prepare raw data for TPO processing
        
        Parameters:
        -----------
        df : pd.DataFrame
            Raw data from fetch_binance_klines with columns:
            timestamp, open, high, low, close, volume
        
        Returns:
        --------
        pd.DataFrame with date column added
        """
        # Ensure we have the right columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
        
        # Add date column if not exists
        if 'date' not in df.columns:
            df['date'] = df['timestamp'].dt.date
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def _parse_period_to_minutes(self, period):
        """Convert period string (e.g., '30m', '1h') to minutes"""
        if period.endswith('m'):
            return int(period[:-1])
        elif period.endswith('h'):
            return int(period[:-1]) * 60
        elif period.endswith('d'):
            return int(period[:-1]) * 1440
        else:
            return 60  # default to 1 hour
    
    def _assign_tpo_groups(self, df, tpo_minutes):
        """Assign TPO group numbers based on time periods within each day"""
        # Calculate time of day in minutes (0-1439 for a 24-hour day)
        time_of_day_minutes = df['timestamp'].dt.hour * 60 + df['timestamp'].dt.minute
        
        # Group by TPO period within the day
        return (time_of_day_minutes / tpo_minutes).astype(int)
    
    def low_to_tick_index(self, price):
        """Convert low price to tick index (inclusive)"""
        p = Decimal(str(price))
        return int((p / self.tick_dec).to_integral_value(rounding=ROUND_FLOOR))
    
    def high_to_tick_index_exclusive(self, price):
        """
        Convert high price to tick index (exclusive boundary)
        If high is exactly on tick boundary, do NOT include that level
        """
        p = Decimal(str(price))
        q = p / self.tick_dec
        if q == q.to_integral_value():  # exact boundary
            return int(q) - 1
        return int(q.to_integral_value(rounding=ROUND_FLOOR))
    
    def tick_index_to_price(self, idx):
        """Convert tick index back to price"""
        return Decimal(idx) * self.tick_dec
    
    def build_tpo(self, df):
        """
        Build TPO profile from prepared data
        
        Parameters:
        -----------
        df : pd.DataFrame
            Prepared data with date column
        
        Returns:
        --------
        tuple: (tpo_df, bracket_ranges_df, summary_df)
            - tpo_df: Individual TPO blocks (date, price, letter)
            - bracket_ranges_df: Price ranges for each time bracket
            - summary_df: Daily profile summaries
        """
        print(f"\nBuilding TPO profiles...")
        
        tpo_records = []
        bracket_ranges_records = []
        summary_records = []
        
        # Calculate TPO period in minutes for grouping
        tpo_minutes = self._parse_period_to_minutes(self.tpo_period)
        
        # Group by date
        for session_date, session_df in df.groupby('date'):
            session_df = session_df.reset_index(drop=True)
            
            # Track session metrics
            session_high = session_df['high'].max()
            session_low = session_df['low'].min()
            session_open = session_df['open'].iloc[0]
            session_close = session_df['close'].iloc[-1]
            
            # Assign TPO groups based on period
            session_df['tpo_group'] = self._assign_tpo_groups(session_df, tpo_minutes)
            
            # Build TPO blocks for each period
            letter_index = 0
            for tpo_group, group_df in session_df.groupby('tpo_group'):
                letter = self.letters[letter_index % len(self.letters)]
                letter_index += 1
                
                # Get the range for this entire TPO group
                group_low = group_df['low'].min()
                group_high = group_df['high'].max()
                
                low_idx = self.low_to_tick_index(group_low)
                high_idx = self.high_to_tick_index_exclusive(group_high)
                
                if high_idx < low_idx:
                    high_idx = low_idx
                
                low_price = self.tick_index_to_price(low_idx)
                high_price = self.tick_index_to_price(high_idx)
                
                # Record bracket range for the group
                bracket_ranges_records.append({
                    'date': session_date,
                    'letter': letter,
                    'bracket_index': letter_index - 1,
                    'timestamp': group_df['timestamp'].iloc[0],
                    'low': float(low_price),
                    'high': float(high_price),
                    'candle_open': group_df['open'].iloc[0],
                    'candle_close': group_df['close'].iloc[-1],
                    'volume': group_df['volume'].sum() if 'volume' in group_df.columns else 0
                })
                
                # Build TPO blocks for this entire group
                for idx in range(low_idx, high_idx + 1):
                    price_dec = self.tick_index_to_price(idx)
                    tpo_records.append({
                        'date': session_date,
                        'price': float(price_dec),
                        'letter': letter
                    })
            
            # Calculate POC (Point of Control) - price with most TPOs
            if tpo_records:
                session_tpos = [r for r in tpo_records if r['date'] == session_date]
                if session_tpos:
                    tpo_counts = pd.DataFrame(session_tpos).groupby('price').size()
                    poc = tpo_counts.idxmax() if len(tpo_counts) > 0 else session_open
                else:
                    poc = session_open
            else:
                poc = session_open
            
            # Calculate Value Area (70% of TPO volume)
            value_area_high, value_area_low = self.calculate_value_area(
                [r for r in tpo_records if r['date'] == session_date]
            )
            
            # Session summary
            summary_records.append({
                'date': session_date,
                'session_high': session_high,
                'session_low': session_low,
                'session_open': session_open,
                'session_close': session_close,
                'poc': poc,
                'value_area_high': value_area_high,
                'value_area_low': value_area_low,
                'range': session_high - session_low,
                'num_periods': len(session_df)
            })
        
        # Convert to DataFrames
        tpo_df = pd.DataFrame(tpo_records)
        bracket_ranges_df = pd.DataFrame(bracket_ranges_records)
        summary_df = pd.DataFrame(summary_records)
        
        print(f"✔ TPO profiles built for {len(summary_df)} trading sessions")
        print(f"  Total TPO blocks: {len(tpo_df)}")
        print(f"  Total time brackets: {len(bracket_ranges_df)}")
        
        return tpo_df, bracket_ranges_df, summary_df
    
    def calculate_value_area(self, session_tpos, value_area_pct=0.70):
        """
        Calculate Value Area (price range containing X% of TPO volume)
        
        Parameters:
        -----------
        session_tpos : list
            List of TPO records for a single session
        value_area_pct : float
            Percentage of TPO volume (default 70%)
        
        Returns:
        --------
        tuple: (value_area_high, value_area_low)
        """
        if not session_tpos:
            return None, None
        
        # Count TPOs at each price level
        price_counts = pd.DataFrame(session_tpos).groupby('price').size().sort_index()
        
        if len(price_counts) == 0:
            return None, None
        
        # Find POC (Point of Control)
        poc_price = price_counts.idxmax()
        poc_idx = price_counts.index.get_loc(poc_price)
        
        # Expand from POC to include value_area_pct of volume
        total_tpos = price_counts.sum()
        target_tpos = int(total_tpos * value_area_pct)
        
        va_tpos = price_counts.iloc[poc_idx]
        upper_idx = poc_idx
        lower_idx = poc_idx
        
        while va_tpos < target_tpos:
            # Check which side to expand
            can_go_up = upper_idx < len(price_counts) - 1
            can_go_down = lower_idx > 0
            
            if not can_go_up and not can_go_down:
                break
            
            if can_go_up and not can_go_down:
                upper_idx += 1
                va_tpos += price_counts.iloc[upper_idx]
            elif can_go_down and not can_go_up:
                lower_idx -= 1
                va_tpos += price_counts.iloc[lower_idx]
            else:
                # Expand to side with more TPOs
                if price_counts.iloc[upper_idx + 1] >= price_counts.iloc[lower_idx - 1]:
                    upper_idx += 1
                    va_tpos += price_counts.iloc[upper_idx]
                else:
                    lower_idx -= 1
                    va_tpos += price_counts.iloc[lower_idx]
        
        return price_counts.index[upper_idx], price_counts.index[lower_idx]
    
    def display_profile(self, tpo_df, date=None, max_rows=50):
        """
        Display visual TPO profile for a specific date
        
        Parameters:
        -----------
        tpo_df : pd.DataFrame
            TPO data
        date : datetime.date, optional
            Specific date to display (default: most recent)
        max_rows : int
            Maximum price levels to display
        """
        if date is None:
            date = tpo_df['date'].max()
        
        session_tpos = tpo_df[tpo_df['date'] == date].copy()
        
        if session_tpos.empty:
            print(f"No TPO data for {date}")
            return
        
        print(f"\n{'='*60}")
        print(f"TPO PROFILE - {self.asset} - {date}")
        print(f"{'='*60}\n")
        
        # Group by price and collect letters
        profile = session_tpos.groupby('price')['letter'].apply(lambda x: ''.join(sorted(x))).to_dict()
        
        # Sort prices descending
        prices = sorted(profile.keys(), reverse=True)
        
        # Limit display if too many rows
        if len(prices) > max_rows:
            mid = len(prices) // 2
            display_prices = prices[:max_rows//2] + ['...'] + prices[-max_rows//2:]
        else:
            display_prices = prices
        
        # Find POC
        tpo_counts = session_tpos.groupby('price').size()
        poc = tpo_counts.idxmax()
        
        # Display profile
        for price in display_prices:
            if price == '...':
                print(f"{'...':>12}  {'...':50}")
                continue
            
            letters = profile[price]
            poc_marker = " <-- POC" if price == poc else ""
            print(f"{price:>{self.display_decimals + 8}.{self.display_decimals}f}  {letters:50}{poc_marker}")
        
        print()
    
    def export_results(self, tpo_df, bracket_ranges_df, summary_df, 
                      prefix='tpo_output', save_csv=False, save_density=True):
        """
        Optionally export results to CSV files
        
        Parameters:
        -----------
        tpo_df : pd.DataFrame
            TPO data
        bracket_ranges_df : pd.DataFrame
            Bracket ranges
        summary_df : pd.DataFrame
            Session summaries
        prefix : str
            Filename prefix
        save_csv : bool
            Whether to actually save CSV files
        save_density : bool
            Whether to save the density file
        """
        if not save_csv:
            print("\n✔ Results ready (not saving to CSV as requested)")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        files = {}
        files['tpo_profile'] = f"{prefix}_tpo_profile_{timestamp}.csv"
        
        # Market Profile format (dates as columns)
        profile_df = self.create_profile_format(tpo_df)
        profile_df.to_csv(files['tpo_profile'], index=True)
        
        # Combined TPO Density (all dates combined with X's) - optional
        if save_density:
            # Extract symbol and interval from prefix
            # prefix format: "BTCUSDT_30m" or similar
            parts = prefix.split('_')
            symbol = parts[0] if len(parts) > 0 else prefix
            interval = parts[1] if len(parts) > 1 else ""
            
            files['tpo_density'] = f"long term profile_{interval}_{symbol}.csv"
            density_df = self.create_combined_tpo_density(tpo_df)
            density_df.to_csv(files['tpo_density'], index=False)
        
        print(f"\n✔ Results saved:")
        for key, filename in files.items():
            print(f"  {key}: {filename}")
        
        return files
    
    def create_profile_format(self, tpo_df):
        """
        Create Market Profile format with dates as columns and prices as rows
        
        Parameters:
        -----------
        tpo_df : pd.DataFrame
            TPO data with columns: date, price, letter
        
        Returns:
        --------
        pd.DataFrame with prices as index and dates as columns
        """
        # Group by date and price, concatenate letters
        profile = tpo_df.groupby(['date', 'price'])['letter'].apply(''.join).reset_index()
        
        # Pivot to wide format
        profile_wide = profile.pivot(index='price', columns='date', values='letter')
        
        # Sort prices in descending order
        profile_wide = profile_wide.sort_index(ascending=False)
        
        # Fill NaN with '.' to match screenshot format
        profile_wide = profile_wide.fillna('.')
        
        # Format column names as dates (e.g., "April 28")
        profile_wide.columns = [col.strftime('%B %-d') if hasattr(col, 'strftime') else str(col) 
                               for col in profile_wide.columns]
        
        return profile_wide
    
    def create_combined_tpo_density(self, tpo_df):
        """
        Create combined TPO density view across all dates
        Shows how many days visited each price and total TPO density with X's
        
        Parameters:
        -----------
        tpo_df : pd.DataFrame
            TPO data with columns: date, price, letter
        
        Returns:
        --------
        pd.DataFrame with columns: PRICE, DYS TPO, TPO DENSITY (with X's)
        """
        if tpo_df.empty:
            return pd.DataFrame()
        
        # Group by price
        price_groups = tpo_df.groupby('price')
        
        # Count how many unique days visited each price
        days_visited = price_groups['date'].nunique()
        
        # Count total TPO blocks at each price (all letters combined)
        tpo_count = price_groups.size()
        
        # Create the combined dataframe
        combined_df = pd.DataFrame({
            'PRICE': days_visited.index,
            'DYS TPO': days_visited.values,
            'TPO_COUNT': tpo_count.values
        })
        
        # Create the TPO DENSITY column with X's
        combined_df['TPO DENSITY'] = combined_df['TPO_COUNT'].apply(
            lambda count: f"{count} {'X' * count}"
        )
        
        # Sort by price descending
        combined_df = combined_df.sort_values('PRICE', ascending=False).reset_index(drop=True)
        
        # Keep only the display columns
        result_df = combined_df[['PRICE', 'DYS TPO', 'TPO DENSITY']]
        
        # Format price with appropriate decimals
        result_df['PRICE'] = result_df['PRICE'].apply(
            lambda x: f"{x:.{self.display_decimals}f}"
        )
        
        return result_df


def fetch_and_process_tpo(symbol='ETHUSDT', interval='1h', days=30, 
                          asset='ETH', tpo_period=None, display=True, save_csv=False, save_density=True,
                          start_date=None, end_date=None):
    """
    Main function: Fetch data from Binance and process into TPO
    
    Parameters:
    -----------
    symbol : str
        Trading pair (e.g., 'ETHUSDT', 'BTCUSDT')
    interval : str
        Time interval for data fetching (e.g., '1h', '30m', '4h')
    days : int
        Number of days of historical data (ignored if start_date and end_date are provided)
    asset : str
        Asset name for tick size (BTC, ETH, XRP, SOL)
    tpo_period : str, optional
        TPO letter assignment period (e.g., '30m', '1h'). If None, uses interval.
    display : bool
        Display visual profile for most recent date
    save_csv : bool
        Save results to CSV files
    save_density : bool
        Save TPO density file (combined view with X's)
    start_date : str, optional
        Custom start date (YYYY-MM-DD format) for backtesting
    end_date : str, optional
        Custom end date (YYYY-MM-DD format) for backtesting
    
    Returns:
    --------
    tuple: (tpo_df, bracket_ranges_df, summary_df)
    """
    if tpo_period is None:
        tpo_period = interval
    print(f"\n{'='*60}")
    print(f"LIVE TPO PROCESSOR - {symbol}")
    print(f"{'='*60}\n")
    
    # Step 1: Fetch data from Binance
    print(f"Step 1: Fetching {symbol} data...")
    df = fetch_binance_klines(symbol=symbol, interval=interval, days=days, 
                              start_date=start_date, end_date=end_date)
    
    # Step 2: Initialize TPO processor
    print(f"\nStep 2: Initializing TPO processor...")
    processor = TPOProcessor(asset=asset, tpo_period=tpo_period)
    
    # Step 3: Prepare data
    print(f"\nStep 3: Preparing data...")
    df = processor.prepare_data(df)
    
    # Step 4: Build TPO profiles
    print(f"\nStep 4: Building TPO profiles...")
    tpo_df, bracket_ranges_df, summary_df = processor.build_tpo(df)
    
    # Step 5: Display results
    if display and not tpo_df.empty:
        print(f"\nStep 5: Displaying profile...")
        processor.display_profile(tpo_df)
        
        print("\nSummary Statistics (Last 5 Sessions):")
        print(summary_df.tail(5).to_string())
        
        # Display combined TPO density
        print(f"\n{'='*60}")
        print(f"COMBINED TPO DENSITY (All {days} days)")
        print(f"{'='*60}")
        density_df = processor.create_combined_tpo_density(tpo_df)
        if not density_df.empty:
            # Display top 20 and bottom 20 prices
            total_rows = len(density_df)
            if total_rows > 40:
                print(density_df.head(20).to_string(index=False))
                print("\n... (middle prices omitted) ...\n")
                print(density_df.tail(20).to_string(index=False))
            else:
                print(density_df.to_string(index=False))
        print()
    
    # Step 6: Export (optional)
    processor.export_results(tpo_df, bracket_ranges_df, summary_df, 
                           prefix=f"{symbol}_{interval}", save_csv=save_csv, save_density=save_density)
    
    print(f"\n{'='*60}")
    print(f"✔ TPO Processing Complete!")
    print(f"{'='*60}\n")
    
    return tpo_df, bracket_ranges_df, summary_df
