#!/usr/bin/env python3
"""
Main Processor 2 - Prediction Query Tool
Queries the prediction database based on user inputs for market analysis
"""

import sys
from pathlib import Path

# Add the prediction database folder to path
PREDICTION_DB_PATH = Path(__file__).parent / "Program for descision preday analysis "
sys.path.insert(0, str(PREDICTION_DB_PATH))

from prediction_database import query_rotation_prediction, query_volume_prediction


def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_section(text):
    """Print a formatted section header"""
    print("\n" + "-"*70)
    print(f"  {text}")
    print("-"*70)


def get_user_input(prompt, valid_options=None):
    """Get user input with validation"""
    while True:
        user_input = input(prompt).strip().upper()
        if valid_options:
            if user_input in valid_options:
                return user_input
            else:
                print(f"  ⚠ Invalid input. Please enter one of: {', '.join(valid_options)}")
        else:
            return user_input


def part1_direction_prediction():
    """Part 1: Direction Prediction based on Rotation Factors"""
    print_section("PART 1: DIRECTION PREDICTION")
    print("\nBased on Algorithm Prediction.csv (Rotation Analysis)")
    print("\nPlease enter the following parameters:")
    print("  • Rotation: B (Buyer) or S (Seller)")
    print("  • Range Extension: B (Up) or S (Down)")
    print("  • Tails: B (Bottom tail/rejection below) or S (Top tail/rejection above)")
    print("  • Composite: B (Opened low, closed high) or S (Opened high, closed low)")
    
    print("\n")
    rotation = get_user_input("1. Rotation (B/S): ", ['B', 'S'])
    range_ext = get_user_input("2. Range Extension (B/S): ", ['B', 'S'])
    tails = get_user_input("3. Tails (B/S): ", ['B', 'S'])
    composite = get_user_input("4. Composite (B/S): ", ['B', 'S'])
    
    # Query the database
    result = query_rotation_prediction(rotation, range_ext, tails, composite)
    
    # Display results
    print("\n" + "━"*70)
    print("  📊 DIRECTION PREDICTION RESULTS")
    print("━"*70)
    
    if result:
        print(f"\n  Input Code: {rotation},{range_ext},{tails},{composite}")
        print(f"\n  🎯 Score: {result['score']}")
        print(f"  📈 Direction: {result['direction']}")
        print(f"\n  💬 Market Analysis:")
        print(f"     {result['detailed_comments']}")
    else:
        print("\n  ⚠ No prediction found for this combination.")
        print(f"     Code: {rotation},{range_ext},{tails},{composite}")
    
    print("\n" + "━"*70)
    
    return result


def part2_performance_strength():
    """Part 2: How Well It Goes - Performance Strength based on Volume"""
    print_section("PART 2: HOW WELL IT GOES")
    print("\nBased on Algorithm Prediction 2.csv (Volume & Value Area Analysis)")
    print("\nPlease enter the following parameters:")
    print("  • Volume Daily: H (High) or L (Low)")
    print("  • Volume Avg: H (Above average) or L (Below average)")
    print("  • VA Placement: Hi (Higher), OH (Overlapping High), Lo (Lower), OL (Overlapping Low), Un (Unchanged)")
    print("  • VA Width: W (Wide), A (Average), or N (Narrow)")
    
    print("\n")
    vol_daily = get_user_input("1. Volume Daily (H/L): ", ['H', 'L'])
    vol_avg = get_user_input("2. Volume Avg (H/L): ", ['H', 'L'])
    va_placement = get_user_input("3. VA Placement (Hi/OH/Lo/OL/Un): ", ['HI', 'OH', 'LO', 'OL', 'UN'])
    va_width = get_user_input("4. VA Width (W/A/N): ", ['W', 'A', 'N'])
    
    # Query the database
    result = query_volume_prediction(vol_daily, vol_avg, va_placement, va_width)
    
    # Display results
    print("\n" + "━"*70)
    print("  📊 PERFORMANCE STRENGTH RESULTS")
    print("━"*70)
    
    if result:
        print(f"\n  Input Code: {vol_daily},{vol_avg},{va_placement},{va_width}")
        print(f"\n  💪 Performance Strength: {result['performance_strength']}")
        print(f"\n  💬 Detailed Comments:")
        print(f"     {result['detailed_comments']}")
        print(f"\n  📈 Expected Results & Trading Strategy:")
        print(f"     {result['expected_results']}")
    else:
        print("\n  ⚠ No prediction found for this combination.")
        print(f"     Code: {vol_daily},{vol_avg},{va_placement},{va_width}")
    
    print("\n" + "━"*70)
    
    return result


def main():
    """Main function to run the prediction processor"""
    print_header("PREDICTION QUERY TOOL - Main Processor 2")
    print("\nThis tool queries the prediction database to provide market analysis")
    print("based on rotation factors and volume/value area patterns.")
    
    # Part 1: Direction Prediction
    rotation_result = part1_direction_prediction()
    
    # Part 2: Performance Strength
    volume_result = part2_performance_strength()
    
    # Final Summary
    print_header("SUMMARY")
    
    if rotation_result:
        print(f"\n  Direction: {rotation_result['direction']} (Score: {rotation_result['score']})")
    else:
        print("\n  Direction: No prediction available")
    
    if volume_result:
        print(f"  Strength: {volume_result['performance_strength']}")
    else:
        print("  Strength: No prediction available")
    
    print("\n" + "="*70)
    print("\n✓ Analysis complete!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
