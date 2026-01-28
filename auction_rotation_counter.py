"""
Auction Rotation Factor Counter
Analyzes TPO profile CSV files and calculates rotation factors
"""
import pandas as pd
import os
from datetime import datetime


def score(curr, prev):
    """
    Score the rotation between two values
    +1 if current > previous
    -1 if current < previous
     0 if equal
    """
    if curr > prev:
        return 1
    elif curr < prev:
        return -1
    return 0


def extract_bracket_ranges(profile_df, date_column):
    """
    Extract high and low prices for each letter (bracket) in a date column
    
    Parameters:
    -----------
    profile_df : pd.DataFrame
        TPO profile data with prices as index
    date_column : str
        Column name (date) to analyze
    
    Returns:
    --------
    pd.DataFrame with columns: letter, low, high
    """
    import string
    
    # Get all rows where this date has TPO activity
    date_data = profile_df[date_column]
    
    # Filter out '.' (no activity) and get prices
    active_data = date_data[date_data != '.']
    
    if active_data.empty:
        return pd.DataFrame(columns=['letter', 'low', 'high'])
    
    # Collect all unique letters present
    letters_present = set()
    for letters_str in active_data.values:
        for letter in letters_str:
            letters_present.add(letter)
    
    # Define proper letter order (A-Z, then a-z)
    letter_order = list(string.ascii_uppercase + string.ascii_lowercase)
    
    # Sort letters in chronological order (A, B, C, ...)
    letters_sorted = [l for l in letter_order if l in letters_present]
    
    # For each letter, find its high and low
    bracket_ranges = []
    for letter in letters_sorted:
        # Find all prices where this letter appears
        prices_with_letter = []
        for price, letters_str in active_data.items():
            if letter in letters_str:
                prices_with_letter.append(price)
        
        if prices_with_letter:
            bracket_ranges.append({
                'letter': letter,
                'low': min(prices_with_letter),
                'high': max(prices_with_letter)
            })
    
    return pd.DataFrame(bracket_ranges)


def calculate_rotation_factor(bracket_ranges_df):
    """
    Calculate rotation factor scores for consecutive brackets
    
    Parameters:
    -----------
    bracket_ranges_df : pd.DataFrame
        DataFrame with columns: letter, low, high
    
    Returns:
    --------
    pd.DataFrame with rotation factor comparison table
    """
    if len(bracket_ranges_df) < 2:
        return pd.DataFrame()
    
    col_names = []
    high_scores = []
    low_scores = []
    net_scores = []
    
    for j in range(1, len(bracket_ranges_df)):
        prev = bracket_ranges_df.iloc[j - 1]
        curr = bracket_ranges_df.iloc[j]
        
        col_names.append(f"{curr['letter']} vs {prev['letter']}")
        
        h = score(curr['high'], prev['high'])
        l = score(curr['low'], prev['low'])
        n = h + l
        
        high_scores.append(h)
        low_scores.append(l)
        net_scores.append(n)
    
    # Add sum column
    col_names.append('Sum')
    high_scores.append(sum(high_scores))
    low_scores.append(sum(low_scores))
    net_scores.append(sum(net_scores))
    
    rf_comparison = pd.DataFrame(
        [high_scores, low_scores, net_scores],
        index=['High', 'Low', 'Net'],
        columns=col_names
    )
    
    return rf_comparison


def analyze_tpo_profile(input_file):
    """
    Analyze TPO profile file and generate rotation factor tables
    
    Parameters:
    -----------
    input_file : str
        Path to the TPO profile CSV file (e.g., BTCUSDT_4h_tpo_profile_*.csv)
    """
    print(f"\n{'='*60}")
    print(f"AUCTION ROTATION FACTOR ANALYZER")
    print(f"{'='*60}\n")
    
    # Read the TPO profile CSV
    print(f"Reading file: {input_file}")
    profile_df = pd.read_csv(input_file, index_col=0)
    
    # Convert index to numeric (prices)
    profile_df.index = pd.to_numeric(profile_df.index, errors='coerce')
    profile_df = profile_df.dropna()
    
    # Sort by price descending (high to low)
    profile_df = profile_df.sort_index(ascending=False)
    
    print(f"Found {len(profile_df.columns)} date(s) in the file")
    print(f"Date range: {profile_df.columns[0]} to {profile_df.columns[-1]}\n")
    
    # Extract base filename for output
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    base_name = base_name.replace('_tpo_profile', '')
    
    # Process each date column
    all_results = {}
    
    for date_col in profile_df.columns:
        print(f"Processing: {date_col}")
        
        # Extract bracket ranges for this date
        bracket_ranges = extract_bracket_ranges(profile_df, date_col)
        
        if bracket_ranges.empty or len(bracket_ranges) < 2:
            print(f"  ⚠ Insufficient data for rotation factor calculation")
            continue
        
        # Calculate rotation factor
        rf_table = calculate_rotation_factor(bracket_ranges)
        
        if not rf_table.empty:
            all_results[date_col] = rf_table
            print(f"  ✔ Rotation factor calculated ({len(bracket_ranges)} brackets)")
    
    if not all_results:
        print("\n❌ No rotation factor data could be calculated")
        return None
    
    # Generate output file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"{base_name}_rotation_factor_{timestamp}.csv"
    
    # Write all rotation factor tables to one CSV
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, (date_col, rf_table) in enumerate(all_results.items()):
            if i > 0:
                f.write('\n\n')
            
            f.write(f"Date: {date_col}\n")
            rf_table.to_csv(f)
    
    print(f"\n{'='*60}")
    print(f"✔ Rotation Factor Analysis Complete!")
    print(f"{'='*60}")
    print(f"Output file: {output_file}")
    print(f"Total dates analyzed: {len(all_results)}")
    
    return output_file



