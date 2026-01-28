# Supabase Database Integration Guide

## Overview
Your TPO analysis app is now connected to Supabase database to store analysis results including predictions, scores, and market analysis.

## Database Schema

### Table: `analysis_results`

| Column Name          | Data Type      | Description                                    |
|---------------------|----------------|------------------------------------------------|
| `id`                | UUID           | Primary key (auto-generated)                   |
| `created_at`        | TIMESTAMPTZ    | Record creation timestamp (auto)               |
| `symbol`            | VARCHAR(20)    | Trading pair (e.g., ETHUSDT)                   |
| `coin`              | VARCHAR(20)    | Coin name (e.g., ETH)                          |
| `analysis_date`     | DATE           | Date of the analysis                           |
| `analysis_timestamp`| TIMESTAMPTZ    | Exact time of analysis                         |
| `input_code`        | VARCHAR(50)    | Input pattern code (e.g., S,S,B,B)            |
| `score`             | INTEGER        | Prediction score                               |
| `direction`         | VARCHAR(20)    | Direction prediction (BULLISH/BEARISH/NEUTRAL) |
| `market_analysis`   | TEXT           | Detailed market analysis text                  |
| `interval`          | VARCHAR(10)    | Time interval (e.g., 1h)                       |
| `tpo_period`        | VARCHAR(10)    | TPO period used                                |
| `days_analyzed`     | INTEGER        | Number of days analyzed                        |
| `full_analysis_data`| JSONB          | Complete analysis data as JSON                 |

## Connection Details

- **Project URL**: `https://yjocerexovxaaizuuzji.supabase.co`
- **API Key**: Stored in `supabase_client.py` (anon key - safe for client use)
- **Client Library**: `supabase-py` v2.27.2

## Files Added/Modified

### New Files:
1. **`supabase_client.py`** - Supabase database client with functions:
   - `save_analysis_result()` - Save analysis to database
   - `get_analysis_history()` - Retrieve analysis history with filters
   - `get_recent_analyses()` - Get most recent analyses
   - `get_analyses_by_coin()` - Filter by coin
   - `get_analyses_by_date_range()` - Filter by date range
   - `delete_analysis()` - Delete an analysis by ID

2. **`test_supabase.py`** - Test script to verify database connection

3. **`SUPABASE_INTEGRATION.md`** - This documentation file

### Modified Files:
1. **`requirements.txt`** - Added `supabase==2.3.4` and `pillow`
2. **`web_app.py`** - Added new endpoints:
   - `POST /api/save-analysis` - Save analysis results
   - `GET /api/analysis-history` - Get analysis history
   - `GET /api/recent-analyses` - Get recent analyses

3. **`templates/daily_summary.html`** - Added:
   - Save button with coin input field
   - JavaScript function to save analysis to database
   - Status messages for save operations

## Usage

### 1. Using the Web Interface

1. Go to the Daily Summary page: http://localhost:5000/daily-summary
2. Fill in all the prediction fields
3. Click "Generate Prediction" button
4. After results appear, enter the coin symbol (e.g., "ETH")
5. Click "💾 Save to Database" button
6. Success message will confirm the save

### 2. Using Python API

```python
from supabase_client import save_analysis_result, get_recent_analyses

# Save an analysis
result = save_analysis_result(
    symbol='ETHUSDT',
    coin='ETH',
    analysis_date='2026-01-28',
    input_code='S,S,B,B',
    score=-1,
    direction='NEUTRAL',
    market_analysis='Detailed analysis text...',
    interval='1h',
    tpo_period='1h',
    days_analyzed=30
)

if result['success']:
    print("Saved successfully!")
    print(result['data'])

# Retrieve recent analyses
history = get_recent_analyses(limit=10)
for record in history['data']:
    print(f"{record['coin']}: {record['direction']}")
```

### 3. Testing the Connection

Run the test script:
```bash
source .venv/bin/activate
python test_supabase.py
```

## API Endpoints

### POST /api/save-analysis
Save an analysis result to the database.

**Request Body:**
```json
{
    "symbol": "ETHUSDT",
    "coin": "ETH",
    "analysis_date": "2026-01-28",
    "input_code": "S,S,B,B",
    "score": -1,
    "direction": "NEUTRAL",
    "market_analysis": "Detailed analysis...",
    "interval": "1h",
    "tpo_period": "1h",
    "days_analyzed": 30
}
```

**Response:**
```json
{
    "success": true,
    "data": {...},
    "message": "Analysis saved successfully"
}
```

### GET /api/analysis-history
Retrieve analysis history with optional filters.

**Query Parameters:**
- `symbol` (optional) - Filter by trading pair
- `coin` (optional) - Filter by coin
- `limit` (optional) - Max records to return (default: 50)

**Example:** `/api/analysis-history?coin=ETH&limit=20`

### GET /api/recent-analyses
Get most recent analyses.

**Query Parameters:**
- `limit` (optional) - Max records to return (default: 10)

## Security

- Row Level Security (RLS) is enabled on the table
- Current policy allows all operations (adjust for production use)
- Using anon key for client-side operations
- Never expose service_role key in client code

## Common Queries

### View all analyses for a specific coin:
```sql
SELECT * FROM analysis_results 
WHERE coin = 'ETH' 
ORDER BY analysis_date DESC;
```

### Get analyses from the last 7 days:
```sql
SELECT * FROM analysis_results 
WHERE analysis_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY analysis_date DESC;
```

### Count analyses by direction:
```sql
SELECT direction, COUNT(*) 
FROM analysis_results 
GROUP BY direction;
```

### Average score by coin:
```sql
SELECT coin, AVG(score) as avg_score, COUNT(*) as total_analyses
FROM analysis_results 
GROUP BY coin
ORDER BY total_analyses DESC;
```

## Troubleshooting

### Connection Issues
- Verify Supabase project is active
- Check API key in `supabase_client.py`
- Ensure `supabase` package is installed: `pip install supabase`

### Save Failures
- Check required fields are provided (symbol, coin)
- Verify direction is valid (BULLISH, BEARISH, NEUTRAL, UP, DOWN)
- Check browser console for detailed error messages

### Package Installation
If you see import errors:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Next Steps

Consider adding:
1. **User Authentication** - Link analyses to specific users
2. **Charts/Dashboard** - Visualize historical predictions
3. **Performance Tracking** - Compare predictions vs actual outcomes
4. **Export Features** - Download analysis history as CSV/Excel
5. **Filtering UI** - Add filters in web interface to view historical data
6. **Analytics Page** - Show statistics and trends over time

## Support

For issues related to:
- **Database structure**: Check [supabase_client.py](supabase_client.py)
- **Web interface**: Check [templates/daily_summary.html](templates/daily_summary.html)
- **API endpoints**: Check [web_app.py](web_app.py) (lines 320-430)
- **Testing**: Run [test_supabase.py](test_supabase.py)
