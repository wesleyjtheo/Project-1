"""
Daily Analysis - Real-time TPO and Volume Analysis
Analyzes today's auction rotation, volume, and value area metrics
Compares with yesterday's data
"""
import pandas as pd
from datetime import datetime, timedelta
from tpo_live_processor import TPOProcessor, ASSET_TICK_SIZES
from fetch_data import fetch_binance_klines
from auction_rotation_counter import extract_bracket_ranges, calculate_rotation_factor


def fetch_today_data(symbol, interval, target_date=None):
    """
    Fetch data for a specific date (default: today)
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    interval : str
        Time interval (30m, 1h, 4h)
    target_date : datetime.date, optional
        Date to fetch (default: today)
    
    Returns:
    --------
    pd.DataFrame with data for the target date
    """
    # Get target date or use today
    if target_date is None:
        now = datetime.utcnow()
        target_date = now.replace(hour=0, minute=0, second=0, microsecond=0).date()
    
    # Use custom date range if target_date is provided
    if target_date is not None and target_date != datetime.utcnow().date():
        # Fetch data for specific date using custom range
        start_str = target_date.strftime('%Y-%m-%d')
        end_str = target_date.strftime('%Y-%m-%d')
        df = fetch_binance_klines(symbol=symbol, interval=interval, days=1,
                                 start_date=start_str, end_date=end_str)
    else:
        # Fetch data for last 2 days to ensure we get complete data
        df = fetch_binance_klines(symbol=symbol, interval=interval, days=2)
    
    # Filter for target date only
    df['date'] = df['timestamp'].dt.date
    
    target_df = df[df['date'] == target_date].copy()
    
    return target_df


def fetch_yesterday_data(symbol, interval, target_date=None):
    """
    Fetch complete data for yesterday (or one day before target_date)
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    interval : str
        Time interval (30m, 1h, 4h)
    target_date : datetime.date, optional
        Reference date (default: today)
    
    Returns:
    --------
    pd.DataFrame with data for one day before target_date
    """
    # Get yesterday's date relative to target_date
    if target_date is None:
        yesterday = (datetime.utcnow() - timedelta(days=1)).date()
    else:
        yesterday = target_date - timedelta(days=1)
    
    # Use custom date range if target_date is provided
    if target_date is not None:
        # Fetch data for specific date using custom range
        start_str = yesterday.strftime('%Y-%m-%d')
        end_str = yesterday.strftime('%Y-%m-%d')
        df = fetch_binance_klines(symbol=symbol, interval=interval, days=1,
                                 start_date=start_str, end_date=end_str)
    else:
        # Fetch data for last 4 days to ensure we get complete data
        df = fetch_binance_klines(symbol=symbol, interval=interval, days=4)
    
    # Filter for yesterday only
    df['date'] = df['timestamp'].dt.date
    yesterday_df = df[df['date'] == yesterday].copy()
    
    return yesterday_df


def fetch_day_before_yesterday_data(symbol, interval, target_date=None):
    """
    Fetch complete data for day before yesterday (or two days before target_date)
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    interval : str
        Time interval (30m, 1h, 4h)
    target_date : datetime.date, optional
        Reference date (default: today)
    
    Returns:
    --------
    pd.DataFrame with data for two days before target_date
    """
    # Get day before yesterday's date relative to target_date
    if target_date is None:
        day_before_yesterday = (datetime.utcnow() - timedelta(days=2)).date()
    else:
        day_before_yesterday = target_date - timedelta(days=2)
    
    # Use custom date range if target_date is provided
    if target_date is not None:
        # Fetch data for specific date using custom range
        start_str = day_before_yesterday.strftime('%Y-%m-%d')
        end_str = day_before_yesterday.strftime('%Y-%m-%d')
        df = fetch_binance_klines(symbol=symbol, interval=interval, days=1,
                                 start_date=start_str, end_date=end_str)
    else:
        # Fetch data for last 5 days to ensure we get complete data
        df = fetch_binance_klines(symbol=symbol, interval=interval, days=5)
    
    # Filter for day before yesterday only
    df['date'] = df['timestamp'].dt.date
    dby_df = df[df['date'] == day_before_yesterday].copy()
    
    return dby_df


def calculate_rotation_for_day(tpo_df):
    """
    Calculate total rotation factor for a single day
    
    Parameters:
    -----------
    tpo_df : pd.DataFrame
        TPO data for one day
    
    Returns:
    --------
    dict with rotation metrics
    """
    if tpo_df.empty:
        return {'total_rotation': 0, 'bracket_count': 0, 'high_score': 0, 'low_score': 0}
    
    # Create profile format
    profile = tpo_df.groupby(['date', 'price'])['letter'].apply(''.join).reset_index()
    profile_wide = profile.pivot(index='price', columns='date', values='letter')
    profile_wide = profile_wide.sort_index(ascending=False)
    profile_wide = profile_wide.fillna('.')
    
    # Get the single date column
    date_col = profile_wide.columns[0]
    
    # Extract bracket ranges
    bracket_ranges = extract_bracket_ranges(profile_wide, date_col)
    
    if bracket_ranges.empty or len(bracket_ranges) < 2:
        return {'total_rotation': 0, 'bracket_count': len(bracket_ranges), 'high_score': 0, 'low_score': 0}
    
    # Calculate rotation factor
    rf_table = calculate_rotation_factor(bracket_ranges)
    
    if rf_table.empty:
        return {'total_rotation': 0, 'bracket_count': len(bracket_ranges), 'high_score': 0, 'low_score': 0}
    
    # Get scores
    total_rotation = rf_table.loc['Net', 'Sum']
    high_score = rf_table.loc['High', 'Sum']
    low_score = rf_table.loc['Low', 'Sum']
    
    return {
        'total_rotation': total_rotation,
        'bracket_count': len(bracket_ranges),
        'high_score': high_score,
        'low_score': low_score
    }


def calculate_value_area_volume(df, processor, tpo_df):
    """
    Calculate volume in the value area (VAH to VAL)
    
    Parameters:
    -----------
    df : pd.DataFrame
        Price data with volume
    processor : TPOProcessor
        TPO processor instance
    tpo_df : pd.DataFrame
        TPO data for the session
    
    Returns:
    --------
    dict with VAH, VAL, and volume in that range
    """
    if tpo_df.empty or df.empty:
        return {'vah': 0, 'val': 0, 'va_volume': 0, 'total_volume': 0}
    
    # Calculate value area
    session_tpos = tpo_df.to_dict('records')
    vah, val = processor.calculate_value_area(session_tpos, value_area_pct=0.70)
    
    if vah is None or val is None:
        return {'vah': 0, 'val': 0, 'va_volume': 0, 'total_volume': df['volume'].sum()}
    
    # Calculate volume in value area range
    va_volume = df[
        (df['low'] <= vah) & (df['high'] >= val)
    ]['volume'].sum()
    
    total_volume = df['volume'].sum()
    
    return {
        'vah': vah,
        'val': val,
        'va_volume': va_volume,
        'total_volume': total_volume,
        'va_percentage': (va_volume / total_volume * 100) if total_volume > 0 else 0
    }


def analyze_daily_metrics(symbol, asset, end_date=None):
    """
    Analyze metrics for the last 3 days (ending on end_date)
    
    Parameters:
    -----------
    symbol : str
        Trading pair (e.g., 'BTCUSDT')
    asset : str
        Asset name (e.g., 'BTC')
    end_date : str or datetime.date, optional
        End date for analysis (default: today). Can be string 'YYYY-MM-DD' or date object
    
    Returns:
    --------
    dict with all daily metrics
    """
    # Parse end_date
    if end_date is None:
        target_date = datetime.utcnow().date()
    elif isinstance(end_date, str):
        target_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        target_date = end_date
    
    print(f"\n{'='*60}")
    print(f"DAILY ANALYSIS - {symbol}")
    print(f"{'='*60}")
    print(f"Analysis Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Current Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    
    timeframes = ['30m', '1h']
    results = {
        'symbol': symbol,
        'asset': asset,
        'analysis_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'target_date': target_date,  # Store target_date for report generation
        'timeframes': {}
    }
    
    # Analyze each timeframe
    for interval in timeframes:
        print(f"Analyzing {interval} timeframe...")
        
        try:
            # Fetch data for all 3 days relative to target_date
            today_df = fetch_today_data(symbol, interval, target_date)
            yesterday_df = fetch_yesterday_data(symbol, interval, target_date)
            dby_df = fetch_day_before_yesterday_data(symbol, interval, target_date)
            
            # Initialize processor
            processor = TPOProcessor(asset=asset, tpo_period=interval)
            
            # Process today's data
            today_df = processor.prepare_data(today_df)
            today_tpo_df, _, _ = processor.build_tpo(today_df)
            
            # Process yesterday's data
            yesterday_df = processor.prepare_data(yesterday_df)
            yesterday_tpo_df, _, _ = processor.build_tpo(yesterday_df)
            
            # Process day before yesterday's data
            dby_df = processor.prepare_data(dby_df)
            dby_tpo_df, _, _ = processor.build_tpo(dby_df)
            
            # Calculate rotation factors
            today_rotation = calculate_rotation_for_day(today_tpo_df)
            yesterday_rotation = calculate_rotation_for_day(yesterday_tpo_df)
            dby_rotation = calculate_rotation_for_day(dby_tpo_df)
            
            # Calculate volumes
            today_volume = today_df['volume'].sum()
            yesterday_volume = yesterday_df['volume'].sum()
            dby_volume = dby_df['volume'].sum()
            
            # Calculate value area metrics
            today_va = calculate_value_area_volume(today_df, processor, today_tpo_df)
            yesterday_va = calculate_value_area_volume(yesterday_df, processor, yesterday_tpo_df)
            dby_va = calculate_value_area_volume(dby_df, processor, dby_tpo_df)
            
            # Store results
            results['timeframes'][interval] = {
                'today': {
                    'rotation': today_rotation['total_rotation'],
                    'high_score': today_rotation['high_score'],
                    'low_score': today_rotation['low_score'],
                    'brackets': today_rotation['bracket_count'],
                    'total_volume': today_volume,
                    'vah': today_va['vah'],
                    'val': today_va['val'],
                    'va_volume': today_va['va_volume'],
                    'va_percentage': today_va['va_percentage']
                },
                'yesterday': {
                    'rotation': yesterday_rotation['total_rotation'],
                    'high_score': yesterday_rotation['high_score'],
                    'low_score': yesterday_rotation['low_score'],
                    'brackets': yesterday_rotation['bracket_count'],
                    'total_volume': yesterday_volume,
                    'vah': yesterday_va['vah'],
                    'val': yesterday_va['val'],
                    'va_volume': yesterday_va['va_volume'],
                    'va_percentage': yesterday_va['va_percentage']
                },
                'day_before_yesterday': {
                    'rotation': dby_rotation['total_rotation'],
                    'high_score': dby_rotation['high_score'],
                    'low_score': dby_rotation['low_score'],
                    'brackets': dby_rotation['bracket_count'],
                    'total_volume': dby_volume,
                    'vah': dby_va['vah'],
                    'val': dby_va['val'],
                    'va_volume': dby_va['va_volume'],
                    'va_percentage': dby_va['va_percentage']
                }
            }
            
            print(f"  ✔ {interval}: Today={today_rotation['total_rotation']:+d}, Yesterday={yesterday_rotation['total_rotation']:+d}, 2 Days Ago={dby_rotation['total_rotation']:+d}")
            
        except Exception as e:
            print(f"  ❌ Error analyzing {interval}: {str(e)}")
            results['timeframes'][interval] = {'error': str(e)}
    
    return results


def generate_daily_report(results):
    """
    Generate formatted daily analysis report
    
    Parameters:
    -----------
    results : dict
        Results from daily analysis
    
    Returns:
    --------
    pd.DataFrame with summary data
    """
    # Get target_date from results, or use current date as fallback
    target_date = results.get('target_date', datetime.utcnow().date())
    
    # Convert to datetime if it's a date object
    if isinstance(target_date, str):
        target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
    else:
        target_datetime = datetime.combine(target_date, datetime.min.time())
    
    # Calculate dates relative to target_date
    today_date = target_datetime.strftime('%Y-%m-%d')
    yesterday_date = (target_datetime - timedelta(days=1)).strftime('%Y-%m-%d')
    dby_date = (target_datetime - timedelta(days=2)).strftime('%Y-%m-%d')
    
    rows = []
    
    for interval, data in results['timeframes'].items():
        if 'error' in data:
            continue
        
        today = data['today']
        yesterday = data['yesterday']
        dby = data['day_before_yesterday']
        
        # Determine control based on today
        if today['rotation'] > 0:
            control = "BUYER"
        elif today['rotation'] < 0:
            control = "SELLER"
        else:
            control = "NEUTRAL"
        
        # Determine trend by comparing all 3 days
        rotations = [today['rotation'], yesterday['rotation'], dby['rotation']]
        if rotations[0] > rotations[1] and rotations[1] > rotations[2]:
            trend = "Strengthening ↑↑"
        elif rotations[0] > rotations[1]:
            trend = "Strengthening ↑"
        elif rotations[0] < rotations[1] and rotations[1] < rotations[2]:
            trend = "Weakening ↓↓"
        elif rotations[0] < rotations[1]:
            trend = "Weakening ↓"
        else:
            trend = "Stable →"
        
        row = {
            'Timeframe': interval.upper(),
            '': '━━━',  # Separator
            'Date_Today': today_date,
            'Rotation_Today': f"{today['rotation']:+d}",
            'Volume_Today': f"{today['total_volume']:,.0f}",
            'VAH_Today': f"{today['vah']:.2f}",
            'VAL_Today': f"{today['val']:.2f}",
            'VA_Vol_Today': f"{today['va_volume']:,.0f}",
            ' ': '━━━',  # Separator
            'Date_Yesterday': yesterday_date,
            'Rotation_Yesterday': f"{yesterday['rotation']:+d}",
            'Volume_Yesterday': f"{yesterday['total_volume']:,.0f}",
            'VAH_Yesterday': f"{yesterday['vah']:.2f}",
            'VAL_Yesterday': f"{yesterday['val']:.2f}",
            'VA_Vol_Yesterday': f"{yesterday['va_volume']:,.0f}",
            '  ': '━━━',  # Separator
            'Date_2_Days_Ago': dby_date,
            'Rotation_2_Days_Ago': f"{dby['rotation']:+d}",
            'Volume_2_Days_Ago': f"{dby['total_volume']:,.0f}",
            'VAH_2_Days_Ago': f"{dby['vah']:.2f}",
            'VAL_2_Days_Ago': f"{dby['val']:.2f}",
            'VA_Vol_2_Days_Ago': f"{dby['va_volume']:,.0f}",
            '   ': '━━━',  # Separator
            'Control': control,
            'Trend': trend
        }
        
        rows.append(row)
    
    return pd.DataFrame(rows)


def run_daily_analysis(symbol, asset):
    """
    Main function to run daily analysis
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    asset : str
        Asset name
    """
    # Analyze
    results = analyze_daily_metrics(symbol, asset)
    
    # Generate report
    report_df = generate_daily_report(results)
    
    # Display
    print(f"\n{'='*60}")
    print("DAILY ANALYSIS SUMMARY")
    print("="*60)
    print(f"\n{report_df.to_string(index=False)}\n")
    
    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"{symbol}_daily_analysis_{timestamp}.csv"
    report_df.to_csv(output_file, index=False)
    
    print(f"{'='*60}")
    print(f"✅ Daily Analysis Complete!")
    print(f"{'='*60}")
    print(f"Output file: {output_file}")
    print("="*60)
    
    return report_df


def run_daily_analysis_web(symbol, asset, end_date=None):
    """
    Web-compatible version - returns dict instead of displaying
    
    Parameters:
    -----------
    symbol : str
        Trading pair
    asset : str
        Asset name
    end_date : str, optional
        End date for analysis (YYYY-MM-DD format). If None, uses current date.
    """
    try:
        results = analyze_daily_metrics(symbol, asset, end_date)
        return results
    except Exception as e:
        return {'error': str(e)}
