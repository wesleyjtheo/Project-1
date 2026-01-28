# TPO Analysis Platform - Quick Start Guide

## 🚀 Getting Started

### Option 1: Using the Startup Script (Recommended)
```bash
./start_web.sh
```

### Option 2: Manual Start
```bash
# Activate virtual environment
source .venv/bin/activate

# Start the server
python web_app.py
```

### Option 3: Using the original CLI version
```bash
python main_processor.py
```

## 📊 Web Interface Usage

1. **Open your browser** and go to: http://127.0.0.1:5001

2. **Select Parameters**:
   - **Cryptocurrency**: Choose from BTC, ETH, SOL, BNB, or PAXG
   - **Time Interval**: 30m, 1h, 4h, or 1d
   - **TPO Period**: How often TPO letters are assigned
   - **Date Range**: 7, 30, 60, or 90 days

3. **Enable Analysis Options**:
   - ✅ **TPO Generation** (Required) - Basic market profile
   - 🔄 **Rotation Factor** - Auction rotation patterns
   - 📈 **Market Control** - Buyer/Seller dominance (slow)
   - 📅 **Daily Analysis** - Today vs Yesterday comparison
   - 📍 **POC Movement** - Point of Control tracking

4. **Run Analysis**: Click "Run Analysis" button
   - Wait for processing (may take several minutes)
   - Results appear on screen when complete

5. **Download PDF**: Click "Download PDF Report" button
   - Professional formatted report
   - All analysis results included
   - Tables and summaries

## 📁 Output Files

### Web Version
- **PDF Reports**: All analysis in one formatted document
- **No CSV files**: Everything in PDF format

### CLI Version (main_processor.py)
- **CSV files**: Individual files for each analysis
- **Format**: Symbol_Analysis_Timestamp.csv

## ⚙️ Configuration

### Supported Cryptocurrencies
- BTCUSDT - Bitcoin
- ETHUSDT - Ethereum
- SOLUSDT - Solana
- BNBUSDT - Binance Coin
- PAXGUSDT - Paxos Gold

### Timeframe Options
- **30 Minutes**: High-frequency intraday analysis
- **1 Hour**: Standard intraday analysis (recommended)
- **4 Hours**: Swing trading timeframe
- **1 Day**: Position trading timeframe

### Analysis Modules

#### 1. TPO Generation
**What it does**: Creates Time Price Opportunity profile
**Output**:
- TPO blocks count
- Time brackets
- Daily sessions
- Value Area High/Low (VAH/VAL)
- Point of Control (POC)
- Volume metrics

**Time**: Fast (30 seconds)

#### 2. Rotation Factor Analysis
**What it does**: Analyzes auction rotation patterns
**Output**:
- Net rotation per day
- Up rotations
- Down rotations
- Buyer/Seller pressure

**Time**: Fast (1 minute)

#### 3. Market Control Analysis ⚠️ SLOW
**What it does**: Tests multiple timeframe/date combinations
**Output**:
- Control (BUYER/SELLER/NEUTRAL)
- Strength (Strong/Moderate/Balanced)
- Cross-timeframe analysis

**Tests**: 9 combinations (3 timeframes × 3 date ranges)
**Time**: Slow (5-10 minutes)

#### 4. Daily Analysis
**What it does**: Compares today vs yesterday
**Output**:
- Volume comparison
- Value Area volume
- Rotation patterns
- Current time metrics

**Time**: Fast (1 minute)

#### 5. POC Movement Analysis
**What it does**: Tracks Point of Control over time
**Output**:
- Daily POC positions
- Movement direction
- Bias score (+1 bullish, -1 bearish, 0 neutral)
- Trend analysis

**Time**: Medium (2-3 minutes)

## 🔍 Understanding Results

### TPO Profile
- **POC** (Point of Control): Price with most time spent
- **VAH** (Value Area High): Upper boundary of value area (70% volume)
- **VAL** (Value Area Low): Lower boundary of value area
- **IB** (Initial Balance): First 2 periods of the session

### Rotation Factor
- **Positive Net**: Buyers in control (price rotating up)
- **Negative Net**: Sellers in control (price rotating down)
- **Near Zero**: Balanced auction

### Market Control
- **BUYER Control**: Net rotation > 0 across timeframes
- **SELLER Control**: Net rotation < 0 across timeframes
- **Strong**: Consistent control (>2x net rotation)
- **Moderate**: Weak control (<2x net rotation)

### POC Movement
- **Bias Score > 0**: Bullish (POC moving higher)
- **Bias Score < 0**: Bearish (POC moving lower)
- **Bias Score = 0**: No clear direction

## 📝 Tips for Best Results

1. **Start with TPO only**: First run to understand the data
2. **Add Rotation Factor**: See auction behavior
3. **Skip Market Control initially**: Very time-consuming
4. **Use 1h timeframe**: Most reliable for most assets
5. **30-day range**: Good balance of data vs processing time

## 🐛 Troubleshooting

### "Address already in use" error
Change port in web_app.py line 437:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change 5000 to 5001
```

### "No data returned"
- Check internet connection
- Verify Binance API is accessible
- Try a different cryptocurrency

### Analysis takes too long
- Disable Market Control Analysis
- Reduce date range to 7 days
- Use larger timeframe (4h or 1d)

### PDF won't download
- Check browser popup blocker
- Try different browser
- Results may be too large - reduce analysis options

## 📊 Example Workflow

### For Day Trading
```
Cryptocurrency: ETHUSDT
Interval: 30m
TPO Period: 30m
Date Range: 7 days
Analysis: TPO + Rotation + Daily
```

### For Swing Trading
```
Cryptocurrency: BTCUSDT
Interval: 4h
TPO Period: 4h
Date Range: 30 days
Analysis: TPO + Rotation + POC Movement
```

### For Comprehensive Analysis
```
Cryptocurrency: SOLUSDT
Interval: 1h
TPO Period: 1h
Date Range: 30 days
Analysis: All modules enabled
Note: Will take 10-15 minutes
```

## 🔄 Differences: Web vs CLI

| Feature | Web Version | CLI Version |
|---------|------------|-------------|
| Interface | Web browser | Terminal |
| Output | PDF reports | CSV files |
| Interactive | Yes | Yes (prompts) |
| Visualization | Tables in browser | Text display |
| Multiple runs | Easy refresh | Re-run script |
| Simultaneous | One at a time | One at a time |
| Best for | Sharing reports | Data analysis |

## 🎯 Which Version to Use?

### Use Web Version When:
- ✅ You want professional PDF reports
- ✅ Sharing results with others
- ✅ Running occasional analyses
- ✅ Prefer graphical interface
- ✅ Need printer-friendly format

### Use CLI Version When:
- ✅ Doing batch processing
- ✅ Need CSV data for further analysis
- ✅ Writing automated scripts
- ✅ Working with data pipelines
- ✅ Prefer command-line workflow

## 📞 Support

For issues or questions:
1. Check this guide first
2. Review README.md
3. Check error messages in terminal
4. Verify all dependencies installed

## 🔐 Data Source

All data comes from **Binance Public API**:
- No API key required
- Real-time market data
- Historical data up to 1000 candles per request
- Rate limits may apply for excessive requests

## ⚡ Performance Tips

1. **Smaller date ranges = faster**: Use 7 days for quick tests
2. **Larger timeframes = faster**: 4h processes quicker than 30m
3. **Disable unused analyses**: Only enable what you need
4. **One analysis at a time**: Don't run multiple browser tabs
5. **Close and restart**: If server becomes slow

## 🎨 PDF Report Structure

1. **Title Page**: Analysis information
2. **TPO Summary**: Basic metrics and daily sessions
3. **Rotation Analysis**: Daily rotation factors (if enabled)
4. **Market Control**: Cross-timeframe analysis (if enabled)
5. **Daily Metrics**: Today vs Yesterday (if enabled)
6. **POC Movement**: Tracking results (if enabled)

All sections include:
- Color-coded tables
- Professional formatting
- Easy-to-read layout
- Comprehensive data

---

**Ready to analyze?** Start the server and visit http://localhost:5000 🚀
