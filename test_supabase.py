"""
Test script to verify Supabase integration
"""
from supabase_client import save_analysis_result, get_recent_analyses
from datetime import datetime

def test_save():
    """Test saving an analysis to the database"""
    print("Testing Supabase connection and save functionality...")
    print("-" * 60)
    
    # Test data
    test_data = {
        'symbol': 'ETHUSDT',
        'coin': 'ETH',
        'analysis_date': '2026-01-28',
        'input_code': 'S,S,B,B',
        'score': -1,
        'direction': 'NEUTRAL',
        'market_analysis': 'BUYER COMPOSITE/TAIL VS SELLER ROTATION/EXTENSION - Bottom tail and buyer composite vs. seller rotation and downward extension. Sellers controlled time and extended down; buyers defended lows and lifted from there. Classic 2-2 split between initiative/time vs. response/structure. Conflicting forces. Expect balancing day as market resolves.',
        'interval': '1h',
        'tpo_period': '1h',
        'days_analyzed': 30
    }
    
    # Save to database
    result = save_analysis_result(**test_data)
    
    if result['success']:
        print("✅ Successfully saved analysis to database!")
        print(f"   Data: {result['data']}")
    else:
        print(f"❌ Failed to save: {result['error']}")
    
    print("-" * 60)
    
    # Retrieve recent analyses
    print("\nFetching recent analyses...")
    history = get_recent_analyses(limit=5)
    
    if history['success']:
        print(f"✅ Retrieved {history['count']} records:")
        for i, record in enumerate(history['data'], 1):
            print(f"\n{i}. {record['coin']} - {record['analysis_date']}")
            print(f"   Direction: {record['direction']} (Score: {record['score']})")
            print(f"   Input Code: {record['input_code']}")
    else:
        print(f"❌ Failed to retrieve: {history['error']}")

if __name__ == '__main__':
    test_save()
