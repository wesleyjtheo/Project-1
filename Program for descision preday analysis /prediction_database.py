"""
Prediction Database Creator and Query Module
Creates and manages SQLite database for Algorithm Predictions
"""
import sqlite3
import csv
import os
from pathlib import Path

# Get the directory of this script
SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / 'predictions.db'
CSV1_PATH = SCRIPT_DIR / 'Algorithm Prediction.csv'
CSV2_PATH = SCRIPT_DIR / 'Algorithm Prediction 2.csv'


def create_database():
    """Create SQLite database and populate with CSV data"""
    
    # Remove existing database if it exists
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    # Create connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table for Algorithm Prediction (rotation-based)
    cursor.execute('''
        CREATE TABLE rotation_predictions (
            id INTEGER PRIMARY KEY,
            rotation TEXT NOT NULL,
            range_extension TEXT NOT NULL,
            tails TEXT NOT NULL,
            composite TEXT NOT NULL,
            score INTEGER,
            direction TEXT,
            detailed_comments TEXT,
            UNIQUE(rotation, range_extension, tails, composite)
        )
    ''')
    
    # Create index for fast lookups
    cursor.execute('''
        CREATE INDEX idx_rotation_lookup 
        ON rotation_predictions(rotation, range_extension, tails, composite)
    ''')
    
    # Create table for Algorithm Prediction 2 (volume-based)
    cursor.execute('''
        CREATE TABLE volume_predictions (
            id INTEGER PRIMARY KEY,
            volume_daily TEXT NOT NULL,
            volume_avg TEXT NOT NULL,
            va_placement TEXT NOT NULL,
            va_width TEXT NOT NULL,
            performance_strength TEXT,
            detailed_comments TEXT,
            expected_results TEXT,
            UNIQUE(volume_daily, volume_avg, va_placement, va_width)
        )
    ''')
    
    # Create index for fast lookups
    cursor.execute('''
        CREATE INDEX idx_volume_lookup 
        ON volume_predictions(volume_daily, volume_avg, va_placement, va_width)
    ''')
    
    print("Database tables created successfully")
    
    # Populate rotation predictions
    rotation_count = 0
    if CSV1_PATH.exists():
        print(f"Loading data from {CSV1_PATH.name}...")
        with open(CSV1_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Skip header row
            
            for row in reader:
                try:
                    # Parse the CSV - it's wrapped in quotes as one string
                    # Split by comma but handle quoted fields
                    if len(row) == 1 and ',' in row[0]:
                        # The entire row is in one cell, need to parse it
                        parts = []
                        current = []
                        in_quotes = False
                        chars = row[0]
                        i = 0
                        while i < len(chars):
                            c = chars[i]
                            if c == '"':
                                if i + 1 < len(chars) and chars[i+1] == '"':
                                    current.append('"')
                                    i += 2
                                    continue
                                else:
                                    in_quotes = not in_quotes
                                    i += 1
                                    continue
                            elif c == ',' and not in_quotes:
                                parts.append(''.join(current))
                                current = []
                                i += 1
                                continue
                            current.append(c)
                            i += 1
                        parts.append(''.join(current))
                        
                        if len(parts) >= 7:
                            rotation = parts[1].strip()
                            range_ext = parts[2].strip()
                            tails = parts[3].strip()
                            composite = parts[4].strip()
                            score = parts[5].strip()
                            direction = parts[6].strip()
                            comments = parts[7].strip() if len(parts) > 7 else ''
                        else:
                            continue
                    elif len(row) >= 8:
                        # Normal CSV parsing worked
                        rotation = row[1].strip()
                        range_ext = row[2].strip()
                        tails = row[3].strip()
                        composite = row[4].strip()
                        score = row[5].strip()
                        direction = row[6].strip()
                        comments = row[7].strip()
                    else:
                        continue
                    
                    if rotation and range_ext and tails and composite:
                        cursor.execute('''
                            INSERT OR REPLACE INTO rotation_predictions 
                            (rotation, range_extension, tails, composite, score, direction, detailed_comments)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (rotation, range_ext, tails, composite, score, direction, comments))
                        rotation_count += 1
                except Exception as e:
                    print(f"Error processing rotation row: {e}")
                    continue
        
        print(f"  ✓ Loaded {rotation_count} rotation predictions")
    else:
        print(f"  ⚠ Warning: {CSV1_PATH.name} not found")
    
    # Populate volume predictions
    volume_count = 0
    if CSV2_PATH.exists():
        print(f"Loading data from {CSV2_PATH.name}...")
        with open(CSV2_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Skip header row
            
            for row in reader:
                try:
                    # Parse the CSV - handle quoted fields
                    if len(row) == 1 and ',' in row[0]:
                        # The entire row is in one cell, need to parse it
                        parts = []
                        current = []
                        in_quotes = False
                        chars = row[0]
                        i = 0
                        while i < len(chars):
                            c = chars[i]
                            if c == '"':
                                if i + 1 < len(chars) and chars[i+1] == '"':
                                    current.append('"')
                                    i += 2
                                    continue
                                else:
                                    in_quotes = not in_quotes
                                    i += 1
                                    continue
                            elif c == ',' and not in_quotes:
                                parts.append(''.join(current))
                                current = []
                                i += 1
                                continue
                            current.append(c)
                            i += 1
                        parts.append(''.join(current))
                        
                        if len(parts) >= 7:
                            vol_daily = parts[1].strip()
                            vol_avg = parts[2].strip()
                            va_placement = parts[3].strip()
                            va_width = parts[4].strip()
                            perf_strength = parts[5].strip()
                            comments = parts[6].strip()
                            expected = parts[7].strip() if len(parts) > 7 else ''
                        else:
                            continue
                    elif len(row) >= 8:
                        # Normal CSV parsing worked
                        vol_daily = row[1].strip()
                        vol_avg = row[2].strip()
                        va_placement = row[3].strip()
                        va_width = row[4].strip()
                        perf_strength = row[5].strip()
                        comments = row[6].strip()
                        expected = row[7].strip()
                    else:
                        continue
                    
                    if vol_daily and vol_avg and va_placement and va_width:
                        cursor.execute('''
                            INSERT OR REPLACE INTO volume_predictions 
                            (volume_daily, volume_avg, va_placement, va_width, 
                             performance_strength, detailed_comments, expected_results)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (vol_daily, vol_avg, va_placement, va_width, 
                              perf_strength, comments, expected))
                        volume_count += 1
                except Exception as e:
                    print(f"Error processing volume row: {e}")
                    continue
        
        print(f"  ✓ Loaded {volume_count} volume predictions")
    else:
        print(f"  ⚠ Warning: {CSV2_PATH.name} not found")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Database created successfully at: {DB_PATH}")
    print(f"  Rotation predictions: {rotation_count}")
    print(f"  Volume predictions: {volume_count}")


def query_rotation_prediction(rotation, range_extension, tails, composite):
    """
    Query rotation-based prediction
    
    Parameters:
    -----------
    rotation : str (B/S/N)
        Buyer/Seller/Neutral rotation
    range_extension : str (B/S/N)
        Buyer/Seller/Neutral range extension
    tails : str (B/S/N)
        Buyer/Seller/Neutral tails
    composite : str (B/S/N/X)
        Buyer/Seller/Neutral/N/A composite
    
    Returns:
    --------
    dict with score, direction, and detailed_comments
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT score, direction, detailed_comments
        FROM rotation_predictions
        WHERE rotation = ? AND range_extension = ? AND tails = ? AND composite = ?
    ''', (rotation, range_extension, tails, composite))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'score': result[0],
            'direction': result[1],
            'detailed_comments': result[2]
        }
    return None


def query_volume_prediction(volume_daily, volume_avg, va_placement, va_width):
    """
    Query volume-based prediction
    
    Parameters:
    -----------
    volume_daily : str (H/L/U)
        High/Low/Unchanged volume daily
    volume_avg : str (H/L/U)
        High/Low/Unchanged volume average
    va_placement : str (Hi/Lo/OH/OL/Un)
        Higher/Lower/Overlapping High/Overlapping Low/Unchanged
    va_width : str (W/A/N)
        Wide/Average/Narrow
    
    Returns:
    --------
    dict with performance_strength, detailed_comments, and expected_results
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT performance_strength, detailed_comments, expected_results
        FROM volume_predictions
        WHERE volume_daily = ? AND volume_avg = ? 
        AND LOWER(va_placement) = LOWER(?) 
        AND LOWER(va_width) = LOWER(?)
    ''', (volume_daily, volume_avg, va_placement, va_width))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'performance_strength': result[0],
            'detailed_comments': result[1],
            'expected_results': result[2]
        }
    return None


def get_all_rotation_predictions():
    """Get all rotation predictions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT rotation, range_extension, tails, composite, score, direction, detailed_comments
        FROM rotation_predictions
        ORDER BY id
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            'rotation': r[0],
            'range_extension': r[1],
            'tails': r[2],
            'composite': r[3],
            'score': r[4],
            'direction': r[5],
            'detailed_comments': r[6]
        }
        for r in results
    ]


def get_all_volume_predictions():
    """Get all volume predictions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT volume_daily, volume_avg, va_placement, va_width, 
               performance_strength, detailed_comments, expected_results
        FROM volume_predictions
        ORDER BY id
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            'volume_daily': r[0],
            'volume_avg': r[1],
            'va_placement': r[2],
            'va_width': r[3],
            'performance_strength': r[4],
            'detailed_comments': r[5],
            'expected_results': r[6]
        }
        for r in results
    ]


if __name__ == '__main__':
    """Run this script to create/rebuild the database"""
    print("="*60)
    print("Creating Prediction Database")
    print("="*60)
    create_database()
    
    print("\n" + "="*60)
    print("Testing Database Queries")
    print("="*60)
    
    # Test rotation prediction
    print("\n1. Testing rotation prediction (B,B,B,B):")
    result = query_rotation_prediction('B', 'B', 'B', 'B')
    if result:
        print(f"   Score: {result['score']}")
        print(f"   Direction: {result['direction']}")
        print(f"   Comments: {result['detailed_comments'][:100]}...")
    else:
        print("   No result found")
    
    # Test volume prediction
    print("\n2. Testing volume prediction (H,H,Hi,W):")
    result = query_volume_prediction('H', 'H', 'Hi', 'W')
    if result:
        print(f"   Strength: {result['performance_strength']}")
        print(f"   Comments: {result['detailed_comments'][:100]}...")
        print(f"   Expected: {result['expected_results'][:100]}...")
    else:
        print("   No result found")
    
    print("\n" + "="*60)
    print("Database ready for use!")
    print("="*60)
    print("\nUsage example in your Python code:")
    print("""
from prediction_database import query_rotation_prediction, query_volume_prediction

# Query rotation prediction
result = query_rotation_prediction('B', 'B', 'B', 'B')
print(result['direction'])  # 'HIGHER'

# Query volume prediction  
result = query_volume_prediction('H', 'H', 'Hi', 'W')
print(result['performance_strength'])  # 'VERY STRONG UP'
    """)
