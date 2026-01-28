"""
Market Control Analyzer
Analyzes rotation factors across multiple timeframes and date ranges
to determine if buyers or sellers are in control
"""
import pandas as pd
from datetime import datetime
from tpo_live_processor import fetch_and_process_tpo
from auction_rotation_counter import extract_bracket_ranges, calculate_rotation_factor
import os


def analyze_market_control(symbol, asset):
    """
    Analyze market control across multiple timeframes and date ranges
    
    Parameters:
    -----------
    symbol : str
        Trading pair (e.g., 'BTCUSDT')
    asset : str
        Asset name (e.g., 'BTC')
    
    Returns:
    --------
    pd.DataFrame with summary of market control analysis
    """
    print(f"\n{'='*60}")
    print(f"MARKET CONTROL ANALYZER - {symbol}")
    print(f"{'='*60}\n")
    print("This will analyze multiple timeframes and date ranges...")
    print("Timeframes: 30m, 1h, 4h")
    print("Date ranges: 7 days, 30 days, 60 days")
    print("Total: 9 analyses\n")
    
    # Define parameters
    timeframes = [
        {"interval": "30m", "tpo_period": "30m", "name": "30 Minutes"},
        {"interval": "1h", "tpo_period": "1h", "name": "1 Hour"},
        {"interval": "4h", "tpo_period": "4h", "name": "4 Hours"}
    ]
    
    date_ranges = [7, 30, 60]
    
    results = []
    total_analyses = len(timeframes) * len(date_ranges)
    current = 0
    
    # Process each combination
    for tf in timeframes:
        for days in date_ranges:
            current += 1
            print(f"\n[{current}/{total_analyses}] Processing {tf['name']} - {days} days...")
            
            try:
                # Fetch and process TPO data
                tpo_df, bracket_ranges_df, summary_df = fetch_and_process_tpo(
                    symbol=symbol,
                    interval=tf['interval'],
                    days=days,
                    asset=asset,
                    tpo_period=tf['tpo_period'],
                    display=False,
                    save_csv=False
                )
                
                # Create temporary profile for rotation analysis
                profile = tpo_df.groupby(['date', 'price'])['letter'].apply(''.join).reset_index()
                profile_wide = profile.pivot(index='price', columns='date', values='letter')
                profile_wide = profile_wide.sort_index(ascending=False)
                profile_wide = profile_wide.fillna('.')
                
                # Calculate rotation factors for all dates and sum them
                total_net_rotation = 0
                dates_analyzed = 0
                
                for date_col in profile_wide.columns:
                    bracket_ranges = extract_bracket_ranges(profile_wide, date_col)
                    
                    if not bracket_ranges.empty and len(bracket_ranges) >= 2:
                        rf_table = calculate_rotation_factor(bracket_ranges)
                        
                        if not rf_table.empty:
                            # Get the Sum of Net row
                            net_sum = rf_table.loc['Net', 'Sum']
                            total_net_rotation += net_sum
                            dates_analyzed += 1
                
                # Determine control
                if total_net_rotation > 0:
                    control = "BUYER"
                    strength = "Strong" if total_net_rotation > dates_analyzed * 2 else "Moderate"
                elif total_net_rotation < 0:
                    control = "SELLER"
                    strength = "Strong" if total_net_rotation < -dates_analyzed * 2 else "Moderate"
                else:
                    control = "NEUTRAL"
                    strength = "Balanced"
                
                results.append({
                    'Timeframe': tf['name'],
                    'Date Range': f"{days} days",
                    'Total Net Rotation': total_net_rotation,
                    'Days Analyzed': dates_analyzed,
                    'Control': control,
                    'Strength': strength,
                    'Score': f"{total_net_rotation:+d}"
                })
                
                print(f"  ✔ {control} control ({strength}) - Score: {total_net_rotation:+d}")
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                results.append({
                    'Timeframe': tf['name'],
                    'Date Range': f"{days} days",
                    'Total Net Rotation': 0,
                    'Days Analyzed': 0,
                    'Control': 'ERROR',
                    'Strength': str(e),
                    'Score': '0'
                })
    
    return pd.DataFrame(results)


def generate_summary_report(results_df, symbol):
    """
    Generate a formatted summary report
    
    Parameters:
    -----------
    results_df : pd.DataFrame
        Results from market control analysis
    symbol : str
        Trading pair
    
    Returns:
    --------
    str: formatted report text
    """
    report_lines = []
    report_lines.append("="*60)
    report_lines.append(f"MARKET CONTROL SUMMARY REPORT - {symbol}")
    report_lines.append("="*60)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Group by date range
    for days in [7, 30, 60]:
        date_results = results_df[results_df['Date Range'] == f"{days} days"]
        
        report_lines.append(f"\n{'='*60}")
        report_lines.append(f"{days} DAY ANALYSIS")
        report_lines.append("="*60)
        
        # Count control types
        buyer_count = len(date_results[date_results['Control'] == 'BUYER'])
        seller_count = len(date_results[date_results['Control'] == 'SELLER'])
        neutral_count = len(date_results[date_results['Control'] == 'NEUTRAL'])
        
        if buyer_count > seller_count:
            overall = f"BUYERS are in control ({buyer_count}/{len(date_results)} timeframes)"
        elif seller_count > buyer_count:
            overall = f"SELLERS are in control ({seller_count}/{len(date_results)} timeframes)"
        else:
            overall = f"MARKET is BALANCED ({buyer_count} buyer, {seller_count} seller)"
        
        report_lines.append(f"\nOverall: {overall}")
        report_lines.append("\nBreakdown by Timeframe:")
        report_lines.append("-" * 60)
        
        for _, row in date_results.iterrows():
            report_lines.append(
                f"  {row['Timeframe']:12} -> {row['Control']:7} ({row['Strength']:8}) "
                f"Score: {row['Score']:>4} ({row['Days Analyzed']} days)"
            )
        
        # Summary stats
        total_score = date_results['Total Net Rotation'].sum()
        report_lines.append("-" * 60)
        report_lines.append(f"Combined Score: {total_score:+d}")
        
        if total_score > 0:
            report_lines.append(f"Interpretation: Bullish momentum across {days} days")
        elif total_score < 0:
            report_lines.append(f"Interpretation: Bearish momentum across {days} days")
        else:
            report_lines.append(f"Interpretation: Neutral/balanced across {days} days")
    
    report_lines.append("\n" + "="*60)
    report_lines.append("END OF REPORT")
    report_lines.append("="*60)
    
    return "\n".join(report_lines)


def run_market_control_analysis(symbol, asset):
    """
    Main function to run complete market control analysis
    
    Parameters:
    -----------
    symbol : str
        Trading pair (e.g., 'BTCUSDT')
    asset : str
        Asset name (e.g., 'BTC')
    """
    # Run analysis
    results_df = analyze_market_control(symbol, asset)
    
    # Generate report
    report_text = generate_summary_report(results_df, symbol)
    
    # Display report
    print("\n" + report_text)
    
    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"{symbol}_market_control_summary_{timestamp}.csv"
    
    # Save CSV
    results_df.to_csv(output_file, index=False)
    
    print(f"\n{'='*60}")
    print(f"✅ Analysis Complete!")
    print(f"{'='*60}")
    print(f"Output file: {output_file}")
    print("="*60)
    
    return results_df, report_text
