"""
Supabase Client for Analysis Results
Handles database operations for storing and retrieving analysis results
"""
from supabase import create_client, Client
from datetime import datetime
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase configuration from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Lazy initialization of Supabase client
_supabase_client = None

def get_supabase_client() -> Client:
    """Get or create the Supabase client instance"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def save_analysis_result(
    symbol: str,
    coin: str,
    analysis_date: str,
    input_code: Optional[str] = None,
    score: Optional[int] = None,
    direction: Optional[str] = None,
    market_analysis: Optional[str] = None,
    interval: Optional[str] = None,
    tpo_period: Optional[str] = None,
    days_analyzed: Optional[int] = None,
    full_analysis_data: Optional[Dict] = None
) -> Dict:
    """
    Save analysis result to Supabase
    
    Parameters:
    -----------
    symbol : str
        Trading pair (e.g., ETHUSDT)
    coin : str
        Coin name (e.g., ETH)
    analysis_date : str
        Date of analysis (YYYY-MM-DD format)
    input_code : str, optional
        Input code pattern (e.g., S,S,B,B)
    score : int, optional
        Prediction score
    direction : str, optional
        Direction prediction (BULLISH, BEARISH, NEUTRAL)
    market_analysis : str, optional
        Detailed market analysis text
    interval : str, optional
        Time interval used
    tpo_period : str, optional
        TPO period used
    days_analyzed : int, optional
        Number of days analyzed
    full_analysis_data : dict, optional
        Complete analysis data as JSON
    
    Returns:
    --------
    Dict with operation result
    """
    try:
        # Parse date if it's a string
        if isinstance(analysis_date, str):
            try:
                date_obj = datetime.strptime(analysis_date, '%Y-%m-%d')
            except ValueError:
                # Try parsing with time
                date_obj = datetime.strptime(analysis_date.split()[0], '%Y-%m-%d')
        else:
            date_obj = analysis_date
        
        # Prepare data for insertion
        data = {
            'symbol': symbol,
            'coin': coin,
            'analysis_date': date_obj.strftime('%Y-%m-%d'),
            'analysis_timestamp': datetime.now().isoformat(),
            'input_code': input_code,
            'score': score,
            'direction': direction,
            'market_analysis': market_analysis,
            'interval': interval,
            'tpo_period': tpo_period,
            'days_analyzed': days_analyzed,
            'full_analysis_data': full_analysis_data
        }
        
        # Insert into Supabase
        supabase = get_supabase_client()
        response = supabase.table('analysis_results').insert(data).execute()
        
        return {
            'success': True,
            'data': response.data,
            'message': 'Analysis saved successfully'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to save analysis: {str(e)}'
        }


def get_analysis_history(
    symbol: Optional[str] = None,
    coin: Optional[str] = None,
    limit: int = 50,
    order_by: str = 'created_at',
    ascending: bool = False
) -> Dict:
    """
    Retrieve analysis history from Supabase
    
    Parameters:
    -----------
    symbol : str, optional
        Filter by trading pair
    coin : str, optional
        Filter by coin
    limit : int
        Maximum number of records to return
    order_by : str
        Field to order by
    ascending : bool
        Sort order
    
    Returns:
    --------
    Dict with query results
    """
    try:
        supabase = get_supabase_client()
        query = supabase.table('analysis_results').select('*')
        
        # Apply filters
        if symbol:
            query = query.eq('symbol', symbol)
        if coin:
            query = query.eq('coin', coin)
        
        # Order and limit
        query = query.order(order_by, desc=not ascending).limit(limit)
        
        response = query.execute()
        
        return {
            'success': True,
            'data': response.data,
            'count': len(response.data)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to retrieve history: {str(e)}'
        }


def get_recent_analyses(limit: int = 10) -> Dict:
    """Get most recent analyses"""
    return get_analysis_history(limit=limit, order_by='created_at', ascending=False)


def get_analyses_by_coin(coin: str, limit: int = 20) -> Dict:
    """Get analyses for a specific coin"""
    return get_analysis_history(coin=coin, limit=limit, order_by='created_at', ascending=False)


def get_analyses_by_date_range(start_date: str, end_date: str) -> Dict:
    """Get analyses within a date range"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('analysis_results')\
            .select('*')\
            .gte('analysis_date', start_date)\
            .lte('analysis_date', end_date)\
            .order('analysis_date', desc=True)\
            .execute()
        
        return {
            'success': True,
            'data': response.data,
            'count': len(response.data)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to retrieve date range: {str(e)}'
        }


def delete_analysis(analysis_id: str) -> Dict:
    """Delete an analysis by ID"""
    try:
        supabase = get_supabase_client()
        response = supabase.table('analysis_results')\
            .delete()\
            .eq('id', analysis_id)\
            .execute()
        
        return {
            'success': True,
            'message': 'Analysis deleted successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to delete analysis: {str(e)}'
        }
