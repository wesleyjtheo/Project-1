"""
Main Processor - Interactive TPO Generator
User interface for selecting cryptocurrency, timeframe, and date range
"""
from datetime import datetime
from tpo_live_processor import fetch_and_process_tpo, AVAILABLE_PAIRS
from auction_rotation_counter import analyze_tpo_profile
from market_control_analyzer import run_market_control_analysis
from daily_analysis import run_daily_analysis
from poc_movement import run_poc_analysis
import os


def select_coin():
    """
    Prompt user to select a cryptocurrency to analyze
    """
    print("\n" + "="*60)
    print("SELECT CRYPTOCURRENCY")
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
                asset = selected.replace('USDT', '')
                print(f"\n✔ Selected: {selected}\n")
                return selected, asset
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")
        except (ValueError, KeyboardInterrupt):
            print("\nInvalid input. Please enter a number between 1 and 5.")
        except EOFError:
            # Handle non-interactive environments
            print("\nNo input available. Using default: ETHUSDT")
            return 'ETHUSDT', 'ETH'


def select_timeframe():
    """
    Prompt user to select timeframe for analysis
    Returns: (interval, tpo_period)
    - interval: Binance API interval (e.g., '30m', '1h', '4h')
    - tpo_period: TPO letter assignment period (e.g., '30m', '1h')
    """
    timeframe_options = [
        {"name": "30 Minutes", "interval": "30m", "tpo_period": "30m", "description": "TPO every 30 mins (A-Z, a-z...)"},
        {"name": "1 Hour", "interval": "1h", "tpo_period": "1h", "description": "TPO every 1 hour (A-X for 24h)"},
        {"name": "4 Hours", "interval": "4h", "tpo_period": "4h", "description": "TPO every 4 hours (A-F for 24h)"},
        {"name": "1 Day", "interval": "1d", "tpo_period": "1d", "description": "TPO every 1 day"},
    ]
    
    print("\n" + "="*60)
    print("SELECT TIMEFRAME")
    print("="*60)
    print("\nAvailable options:")
    
    for i, option in enumerate(timeframe_options, 1):
        print(f"  {i}. {option['name']:12} - {option['description']}")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            idx = int(choice) - 1
            
            if 0 <= idx < len(timeframe_options):
                selected = timeframe_options[idx]
                print(f"\n✔ Selected: {selected['name']} (Interval: {selected['interval']}, TPO Period: {selected['tpo_period']})\n")
                return selected['interval'], selected['tpo_period']
            else:
                print("Invalid choice. Please enter a number between 1 and 4.")
        except (ValueError, KeyboardInterrupt):
            print("\nInvalid input. Please enter a number between 1 and 4.")
        except EOFError:
            # Handle non-interactive environments
            print("\nNo input available. Using default: 1 Hour")
            return '1h', '1h'


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
    """
    Interactive TPO Processor - Select your cryptocurrency, timeframe, and date range
    """
    
    # ============================================================
    # STEP 1: TPO GENERATION
    # ============================================================
    print("\n" + "="*60)
    print("TPO GENERATION")
    print("="*60)
    
    # Let user select coin
    SYMBOL, ASSET = select_coin()
    
    # Let user select timeframe
    INTERVAL, TPO_PERIOD = select_timeframe()
    
    # Let user select date range
    DAYS = select_date_range()
    
    # Configuration
    DISPLAY = True           # Show visual profile
    SAVE_CSV = True          # Set to True if you want CSV files
    
    # Ask about density file
    save_density_response = input("\nGenerate TPO density file (combined view with X's)? (y/n): ").strip().lower()
    SAVE_DENSITY = (save_density_response == 'y')
    
    # Run the processor
    tpo_df, bracket_ranges_df, summary_df = fetch_and_process_tpo(
        symbol=SYMBOL,
        interval=INTERVAL,
        days=DAYS,
        asset=ASSET,
        tpo_period=TPO_PERIOD,
        display=DISPLAY,
        save_csv=SAVE_CSV,
        save_density=SAVE_DENSITY
    )
    
    # Access the results (they're ready for further analysis/backtesting)
    print(f"\nResults available in memory:")
    print(f"  tpo_df: {len(tpo_df)} TPO blocks")
    print(f"  bracket_ranges_df: {len(bracket_ranges_df)} time brackets")
    print(f"  summary_df: {len(summary_df)} daily sessions")
    
    # ============================================================
    # STEP 2: AUCTION ROTATION FACTOR ANALYSIS
    # ============================================================
    print("\n" + "="*60)
    print("AUCTION ROTATION FACTOR ANALYSIS")
    print("="*60)
    
    generate_rf = input("\nGenerate rotation factor analysis? (y/n): ").strip().lower()
    
    if generate_rf == 'y':
        # Find the generated TPO profile file
        timestamp = datetime.now().strftime('%Y%m%d')
        pattern = f"{SYMBOL}_{INTERVAL}_tpo_profile_{timestamp}"
        
        # Look for the most recent file
        profile_files = [f for f in os.listdir('.') if f.startswith(pattern) and f.endswith('.csv')]
        
        if profile_files:
            # Use the most recent file
            profile_files.sort(reverse=True)
            profile_file = profile_files[0]
            
            print(f"\nAnalyzing: {profile_file}")
            
            try:
                rotation_output = analyze_tpo_profile(profile_file)
                if rotation_output:
                    print(f"\n✅ Rotation factor analysis complete!")
            except Exception as e:
                print(f"\n❌ Error during rotation factor analysis: {str(e)}")
        else:
            print(f"\n⚠ Could not find TPO profile file matching pattern: {pattern}*.csv")
            print("Please ensure CSV files were generated.")
    else:
        print("\nSkipping rotation factor analysis.")
    
    # ============================================================
    # STEP 3: MARKET CONTROL ANALYSIS
    # ============================================================
    print("\n" + "="*60)
    print("MARKET CONTROL ANALYSIS")
    print("="*60)
    print("\nThis analysis will:")
    print("  - Test ALL timeframes (30m, 1h, 4h, 1d)")
    print("  - Test ALL date ranges (7d, 30d, 60d)")
    print("  - Determine buyer/seller control for each combination")
    print("  - Generate a comprehensive summary report")
    print("\nNote: This will take several minutes to complete.")
    
    run_control_analysis = input("\nRun market control analysis? (y/n): ").strip().lower()
    
    if run_control_analysis == 'y':
        try:
            run_market_control_analysis(SYMBOL, ASSET)
            print("\n✅ Market control analysis completed!")
        except Exception as e:
            print(f"\n❌ Error during market control analysis: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("\nSkipping market control analysis.")
    
    # ============================================================
    # STEP 4: DAILY ANALYSIS
    # ============================================================
    print("\n" + "="*60)
    print("DAILY ANALYSIS")
    print("="*60)
    print("\nThis analysis will:")
    print("  - Extract today's auction rotation (30m, 1h, 4h)")
    print("  - Compare today's volume vs yesterday")
    print("  - Calculate Value Area volume (today vs yesterday)")
    print("  - Show current time and real-time metrics")
    
    run_daily = input("\nRun daily analysis? (y/n): ").strip().lower()
    
    if run_daily == 'y':
        try:
            run_daily_analysis(SYMBOL, ASSET)
            print("\n✅ Daily analysis completed!")
        except Exception as e:
            print(f"\n❌ Error during daily analysis: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("\nSkipping daily analysis.")
    
    # ============================================================
    # STEP 5: POC MOVEMENT ANALYSIS
    # ============================================================
    print("\n" + "="*60)
    print("POC MOVEMENT ANALYSIS")
    print("="*60)
    print("\nThis analysis will:")
    print("  - Track Point of Control (POC) movement over time")
    print("  - Compare daily POC positions")
    print("  - Generate directional bias score (+1 for up, -1 for down)")
    print("  - Available ranges: Today, 7 days, 30 days, or custom")
    
    run_poc = input("\nRun POC movement analysis? (y/n): ").strip().lower()
    
    if run_poc == 'y':
        try:
            run_poc_analysis(SYMBOL, ASSET)
            print("\n✅ POC movement analysis completed!")
        except Exception as e:
            print(f"\n❌ Error during POC movement analysis: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("\nSkipping POC movement analysis.")
    
    print("\n" + "="*60)
    print("✅ All processing complete!")
    print("="*60)
