"""
POC Movement Tracker
Tracks Point of Control (POC) movement over different timeframes
to determine directional bias
"""
import pandas as pd
from datetime import datetime, timedelta
from tpo_live_processor import TPOProcessor
from fetch_data import fetch_binance_klines


def select_poc_date_range():
    """
    Ask user to select date range for POC analysis
    
    Returns:
    --------
    tuple: (range_type, days)
        range_type: '7days', '14days', '30days', 'custom'
        days: number of days
    """
    print("\n" + "="*60)
    print("POC MOVEMENT TRACKER - DATE RANGE SELECTION")
    print("="*60)
    print("\nSelect date range:")
    print("  1. Last 7 days (1h TPO end-of-day)")
    print("  2. Last 14 days (1h TPO end-of-day)")
    print("  3. Last 1 month (30 days) (1h TPO end-of-day)")
    print("  4. Custom range (1h TPO end-of-day)")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            return ('7days', 7)
        elif choice == "2":
            return ('14days', 14)
        elif choice == "3":
            return ('30days', 30)
        elif choice == "4":
            while True:
                try:
                    days = int(input("Enter number of days: ").strip())
                    if days > 0:
                        return ('custom', days)
                    else:
                        print("Please enter a positive number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


def calculate_daily_poc(df, processor):
    """
    Calculate POC (Point of Control) for a given dataset
    
    Parameters:
    -----------
    df : pd.DataFrame
        Price data
    processor : TPOProcessor
        Initialized TPO processor
    
    Returns:
    --------
    float: POC price
    """
    if df.empty:
        return None
    
    # Prepare and build TPO
    df = processor.prepare_data(df)
    tpo_df, _, summary_df = processor.build_tpo(df)
    
    if summary_df.empty or 'poc' not in summary_df.columns:
        return None
    
    # Get POC from summary
    poc = summary_df['poc'].iloc[0]
    
    return poc


def track_poc_movement_web(symbol, asset, days, start_date=None, end_date=None):
    """
    Web-compatible version - returns dict with POC movement data
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    asset : str
        Asset name
    days : int
        Number of days to analyze (ignored if start_date and end_date are provided)
    start_date : str, optional
        Custom start date (YYYY-MM-DD) for backtesting
    end_date : str, optional
        Custom end date (YYYY-MM-DD) for backtesting
    
    Returns:
    --------
    dict with tracking results
    """
    try:
        from tpo_live_processor import ASSET_TICK_SIZES
        
        # Fetch data
        df = fetch_binance_klines(symbol=symbol, interval='1h', days=days,
                                 start_date=start_date, end_date=end_date)
        
        # Initialize processor
        tick_size = ASSET_TICK_SIZES.get(asset, 1.0)
        processor = TPOProcessor(asset=asset, tick_size=tick_size, tpo_period='1h')
        
        # Calculate daily POCs
        daily_pocs = []
        df['date'] = df['timestamp'].dt.date
        
        for date in df['date'].unique():
            date_df = df[df['date'] == date]
            poc = calculate_daily_poc(date_df, processor)
            
            if poc:
                daily_pocs.append({
                    'date': str(date),
                    'poc': float(poc)
                })
        
        # Calculate directional bias
        if len(daily_pocs) >= 2:
            movements = []
            for i in range(1, len(daily_pocs)):
                prev_poc = daily_pocs[i-1]['poc']
                curr_poc = daily_pocs[i]['poc']
                direction = 1 if curr_poc > prev_poc else (-1 if curr_poc < prev_poc else 0)
                movements.append(direction)
            
            bias_score = sum(movements)
            bias = "BULLISH" if bias_score > 0 else ("BEARISH" if bias_score < 0 else "NEUTRAL")
        else:
            bias_score = 0
            bias = "INSUFFICIENT DATA"
        
        return {
            'daily_pocs': daily_pocs,
            'bias_score': bias_score,
            'bias': bias,
            'days_analyzed': len(daily_pocs)
        }
        
    except Exception as e:
        return {'error': str(e)}


def track_poc_movement_today(symbol, asset):
    """
    Track POC movement throughout today using 30m intervals
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    asset : str
        Asset name
    
    Returns:
    --------
    dict with tracking results
    """
    print("\nTracking today's POC movement (30m intervals)...")
    
    # Fetch today's data and yesterday's complete data
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get data for last 2 days
    df_all = fetch_binance_klines(symbol=symbol, interval='30m', days=2)
    df_all['date'] = df_all['timestamp'].dt.date
    
    today_date = today_start.date()
    yesterday_date = (now - timedelta(days=1)).date()
    
    today_df = df_all[df_all['date'] == today_date].copy()
    yesterday_df = df_all[df_all['date'] == yesterday_date].copy()
    
    # Initialize processor
    processor = TPOProcessor(asset=asset, tpo_period='30m')
    
    # Calculate yesterday's end-of-day POC
    yesterday_poc = calculate_daily_poc(yesterday_df, processor)
    
    if yesterday_poc is None:
        print("  ❌ Could not calculate yesterday's POC")
        return None
    
    print(f"  Yesterday's POC: {yesterday_poc:.2f}")
    
    # Track POC movement throughout today
    movements = []
    prev_poc = yesterday_poc
    
    # Group today's data by 30-minute intervals
    today_df = today_df.sort_values('timestamp').reset_index(drop=True)
    
    for idx in range(1, len(today_df) + 1):
        # Get data up to this point
        current_df = today_df.iloc[:idx].copy()
        current_time = current_df['timestamp'].iloc[-1]
        
        # Calculate POC for data up to this point
        current_poc = calculate_daily_poc(current_df, processor)
        
        if current_poc is not None:
            # Compare with previous POC
            if current_poc > prev_poc:
                score = 1
                direction = "UP"
            elif current_poc < prev_poc:
                score = -1
                direction = "DOWN"
            else:
                score = 0
                direction = "FLAT"
            
            movements.append({
                'time': current_time.strftime('%H:%M'),
                'poc': current_poc,
                'prev_poc': prev_poc,
                'score': score,
                'direction': direction
            })
            
            prev_poc = current_poc
    
    total_score = sum(m['score'] for m in movements)
    
    print(f"  Today's POC tracking: {len(movements)} intervals analyzed")
    print(f"  Total Score: {total_score:+d}")
    
    return {
        'range_type': 'today',
        'symbol': symbol,
        'date': today_date.strftime('%Y-%m-%d'),
        'yesterday_poc': yesterday_poc,
        'movements': movements,
        'total_score': total_score,
        'intervals_tracked': len(movements)
    }


def track_poc_movement_multiday(symbol, asset, days):
    """
    Track POC movement over multiple days using 1h end-of-day data
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    asset : str
        Asset name
    days : int
        Number of days to analyze
    
    Returns:
    --------
    dict with tracking results
    """
    print(f"\nTracking POC movement over {days} days (1h TPO end-of-day)...")
    
    # Fetch data for days + 1 (need previous day for comparison)
    df_all = fetch_binance_klines(symbol=symbol, interval='1h', days=days+1)
    df_all['date'] = df_all['timestamp'].dt.date
    
    # Initialize processor
    processor = TPOProcessor(asset=asset, tpo_period='1h')
    
    # Get unique dates
    unique_dates = sorted(df_all['date'].unique())
    
    if len(unique_dates) < 2:
        print("  ❌ Not enough data for comparison")
        return None
    
    # Track POC for each day
    daily_pocs = []
    
    for date in unique_dates:
        day_df = df_all[df_all['date'] == date].copy()
        poc = calculate_daily_poc(day_df, processor)
        
        if poc is not None:
            daily_pocs.append({
                'date': date.strftime('%Y-%m-%d'),
                'poc': poc
            })
    
    print(f"  Calculated POC for {len(daily_pocs)} days")
    
    # Calculate movements (compare each day with previous)
    movements = []
    
    for i in range(1, len(daily_pocs)):
        current = daily_pocs[i]
        previous = daily_pocs[i-1]
        
        if current['poc'] > previous['poc']:
            score = 1
            direction = "UP"
        elif current['poc'] < previous['poc']:
            score = -1
            direction = "DOWN"
        else:
            score = 0
            direction = "FLAT"
        
        movements.append({
            'date': current['date'],
            'poc': current['poc'],
            'prev_poc': previous['poc'],
            'change': current['poc'] - previous['poc'],
            'score': score,
            'direction': direction
        })
    
    total_score = sum(m['score'] for m in movements)
    
    print(f"  Total Score: {total_score:+d}")
    
    return {
        'range_type': f'{days}days',
        'symbol': symbol,
        'days_analyzed': len(movements),
        'movements': movements,
        'total_score': total_score
    }


def generate_poc_report(results):
    """
    Generate POC movement report
    
    Parameters:
    -----------
    results : dict
        Results from POC tracking
    
    Returns:
    --------
    pd.DataFrame with report
    """
    if results is None:
        return None
    
    movements = results['movements']
    
    # Multi-day tracking
    df = pd.DataFrame(movements)
    df = df[['date', 'poc', 'prev_poc', 'change', 'direction', 'score']]
    df.columns = ['Date', 'End_of_Day_POC', 'Previous_Day_POC', 'Change', 'Direction', 'Score']
    
    # Add summary row
    summary = pd.DataFrame([{
        'Date': 'TOTAL',
        'End_of_Day_POC': '',
        'Previous_Day_POC': '',
        'Change': '',
        'Direction': 'UP' if results['total_score'] > 0 else ('DOWN' if results['total_score'] < 0 else 'FLAT'),
        'Score': results['total_score']
    }])
    
    df = pd.concat([df, summary], ignore_index=True)
    
    return df


def run_poc_analysis(symbol, asset):
    """
    Main function to run POC movement analysis
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    asset : str
        Asset name
    """
    # Get user selection
    range_type, days = select_poc_date_range()
    
    # Run analysis
    results = track_poc_movement_multiday(symbol, asset, days)
    
    if results is None:
        print("\n❌ POC analysis failed")
        return
    
    # Generate report
    report_df = generate_poc_report(results)
    
    if report_df is None:
        print("\n❌ Could not generate report")
        return
    
    # Display
    print(f"\n{'='*60}")
    print("POC MOVEMENT ANALYSIS SUMMARY")
    print("="*60)
    print(f"Symbol: {symbol}")
    print(f"Range: {range_type}")
    print(f"Days Analyzed: {results['days_analyzed']}")
    print(f"Total Score: {results['total_score']:+d}")
    print(f"\nInterpretation:")
    if results['total_score'] > 0:
        print(f"  ✅ Bullish POC movement (score: {results['total_score']:+d})")
    elif results['total_score'] < 0:
        print(f"  ⚠️  Bearish POC movement (score: {results['total_score']:+d})")
    else:
        print(f"  ➡️  Neutral POC movement (score: 0)")
    print("="*60)
    print(f"\n{report_df.to_string(index=False)}\n")
    
    # Save to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"{symbol}_POC_movement_{days}days_{timestamp}.csv"
    
    report_df.to_csv(output_file, index=False)
    
    print("="*60)
    print(f"✅ POC Movement Analysis Complete!")
    print("="*60)
    print(f"Output file: {output_file}")
    print("="*60)
    
    return report_df
