"""
Web Application for TPO Analysis
Interactive web interface for cryptocurrency TPO analysis with PDF output
"""
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import os
import io
import numpy as np
import base64
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import pandas as pd

# Import analysis modules
from tpo_live_processor import fetch_and_process_tpo, AVAILABLE_PAIRS
from auction_rotation_counter import analyze_tpo_profile, extract_bracket_ranges, calculate_rotation_factor
from daily_analysis import run_daily_analysis_web
from poc_movement import track_poc_movement_web

# Import prediction database functions
import sys
from pathlib import Path
PREDICTION_DB_PATH = Path(__file__).parent / "Program for descision preday analysis "
sys.path.insert(0, str(PREDICTION_DB_PATH))
from prediction_database import query_rotation_prediction, query_volume_prediction

# Import Supabase client
from supabase_client import save_analysis_result, get_analysis_history, get_recent_analyses

def convert_to_serializable(obj):
    """Convert numpy/pandas types to Python native types for JSON serialization"""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.to_list()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj

app = Flask(__name__)

# Configure Flask for larger payloads (for base64 images)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max request size

# Store analysis results temporarily
analysis_results = {}


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', available_pairs=AVAILABLE_PAIRS)


@app.route('/daily-summary')
def daily_summary():
    """Daily Summary page for prediction queries"""
    return render_template('daily_summary.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Run TPO analysis based on user parameters"""
    try:
        data = request.json
        
        symbol = data.get('symbol', 'ETHUSDT')
        interval = data.get('interval', '1h')
        tpo_period = data.get('tpo_period', '1h')
        days = data.get('days', 30)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        asset = symbol.replace('USDT', '')
        
        # Options for analysis types
        run_tpo = data.get('run_tpo', True)
        run_rotation = data.get('run_rotation', False)
        run_daily = data.get('run_daily', False)
        run_poc = data.get('run_poc', False)
        save_density = data.get('save_density', False)
        
        # Handle custom date range
        if days == 'custom' and start_date and end_date:
            date_range_str = f"{start_date} to {end_date}"
            print(f"Custom date range detected:")
            print(f"  Start: {start_date}")
            print(f"  End: {end_date}")
            print(f"  Days: {days}")
        else:
            days = int(days)
            date_range_str = f"Last {days} days"
        
        results = {
            'symbol': symbol,
            'asset': asset,
            'interval': interval,
            'tpo_period': tpo_period,
            'days': days if days != 'custom' else date_range_str,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'save_density': save_density,
            'analyses': {}
        }
        
        # Step 1: TPO Generation
        if run_tpo:
            print(f"Generating TPO for {symbol}...")
            
            # Prepare parameters for TPO processing
            tpo_params = {
                'symbol': symbol,
                'interval': interval,
                'asset': asset,
                'tpo_period': tpo_period,
                'display': False,
                'save_csv': False,
                'save_density': False
            }
            
            # Add either custom dates or days parameter
            if days == 'custom' and start_date and end_date:
                tpo_params['start_date'] = start_date
                tpo_params['end_date'] = end_date
                tpo_params['days'] = 30  # Default, will be ignored
            else:
                tpo_params['days'] = days
            
            tpo_df, bracket_ranges_df, summary_df = fetch_and_process_tpo(**tpo_params)
            
            # Create TPO profile format (letter-based view)
            profile = tpo_df.groupby(['date', 'price'])['letter'].apply(''.join).reset_index()
            profile_wide = profile.pivot(index='price', columns='date', values='letter')
            profile_wide = profile_wide.sort_index(ascending=False)
            profile_wide = profile_wide.fillna('.')
            
            # Convert to format for display
            tpo_profile_data = []
            for price in profile_wide.index:
                row = {'price': float(price)}
                for date in profile_wide.columns:
                    row[str(date)] = profile_wide.loc[price, date]
                tpo_profile_data.append(row)
            
            # Generate TPO density if requested
            density_data = None
            if save_density:
                from tpo_live_processor import TPOProcessor
                processor = TPOProcessor(asset=asset, tpo_period=tpo_period)
                density_df = processor.create_combined_tpo_density(tpo_df)
                if not density_df.empty:
                    density_data = convert_to_serializable(density_df.to_dict('records'))
            
            results['analyses']['tpo'] = {
                'tpo_blocks': int(len(tpo_df)),
                'time_brackets': int(len(bracket_ranges_df)),
                'daily_sessions': int(len(summary_df)),
                'summary': convert_to_serializable(summary_df.to_dict('records')) if not summary_df.empty else [],
                'bracket_ranges': convert_to_serializable(bracket_ranges_df.to_dict('records')) if not bracket_ranges_df.empty else [],
                'tpo_profile': convert_to_serializable(tpo_profile_data),
                'dates': [str(d) for d in profile_wide.columns],
                'tpo_density': density_data
            }
            
            # Store for rotation analysis
            analysis_results['tpo_df'] = tpo_df
            analysis_results['summary_df'] = summary_df
            analysis_results['profile_wide'] = profile_wide
        
        # Step 2: Auction Rotation Analysis
        if run_rotation and 'profile_wide' in analysis_results:
            print("Running rotation factor analysis...")
            profile_wide = analysis_results['profile_wide']
            
            rotation_results = []
            rotation_details = []
            
            for date_col in profile_wide.columns:
                bracket_ranges = extract_bracket_ranges(profile_wide, date_col)
                
                if not bracket_ranges.empty and len(bracket_ranges) >= 2:
                    rf_table = calculate_rotation_factor(bracket_ranges)
                    
                    if not rf_table.empty:
                        # Store summary
                        rotation_results.append({
                            'date': str(date_col),
                            'net_rotation': float(rf_table.loc['Net', 'Sum']) if 'Net' in rf_table.index else 0,
                            'total_up': float(rf_table.loc['Up', 'Sum']) if 'Up' in rf_table.index else 0,
                            'total_down': float(rf_table.loc['Down', 'Sum']) if 'Down' in rf_table.index else 0
                        })
                        
                        # Store detailed rotation table
                        rotation_details.append({
                            'date': str(date_col),
                            'bracket_ranges': bracket_ranges.to_dict('records'),
                            'rotation_table': rf_table.to_dict()
                        })
            
            results['analyses']['rotation'] = convert_to_serializable(rotation_results)
            results['analyses']['rotation_details'] = convert_to_serializable(rotation_details)
        
        # Step 3: Daily Analysis
        if run_daily:
            print("Running daily analysis...")
            from daily_analysis import analyze_daily_metrics, generate_daily_report
            
            # Use end_date for custom date range, otherwise analyze current data
            analysis_end_date = end_date if (days == 'custom' and end_date) else None
            print(f"  Days value: {days} (type: {type(days)})")
            print(f"  End date value: {end_date}")
            print(f"  Analysis end date: {analysis_end_date}")
            if analysis_end_date:
                print(f"  Using custom end date for daily analysis: {analysis_end_date}")
            else:
                print(f"  Using current date for daily analysis")
            
            daily_results = analyze_daily_metrics(symbol, asset, end_date=analysis_end_date)
            report_df = generate_daily_report(daily_results)
            
            # Store both raw results and formatted report
            results['analyses']['daily'] = {
                'raw_data': convert_to_serializable(daily_results),
                'report': convert_to_serializable(report_df.to_dict('records')) if not report_df.empty else []
            }
        
        # Step 5: POC Movement Analysis
        if run_poc:
            print("Running POC movement analysis...")
            
            # Prepare parameters for POC analysis
            if days == 'custom' and start_date and end_date:
                poc_results = track_poc_movement_web(symbol, asset, 30, 
                                                     start_date=start_date, end_date=end_date)
            else:
                poc_results = track_poc_movement_web(symbol, asset, int(days))
            
            results['analyses']['poc'] = convert_to_serializable(poc_results)
        
        # Store results for PDF generation
        analysis_results['latest'] = results
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in analysis: {error_trace}")
        return jsonify({'success': False, 'error': str(e), 'trace': error_trace}), 500


@app.route('/api/daily-summary', methods=['POST'])
def daily_summary_query():
    """Process daily summary prediction queries"""
    try:
        data = request.json
        
        # Part 1: Direction Prediction (Rotation)
        rotation = data.get('rotation', '').upper()
        range_ext = data.get('range_extension', '').upper()
        tails = data.get('tails', '').upper()
        composite = data.get('composite', '').upper()
        
        # Part 2: Performance Strength (Volume)
        vol_daily = data.get('volume_daily', '').upper()
        vol_avg = data.get('volume_avg', '').upper()
        va_placement = data.get('va_placement', '').upper()
        va_width = data.get('va_width', '').upper()
        
        results = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Query rotation prediction
        if all([rotation, range_ext, tails, composite]):
            rotation_result = query_rotation_prediction(rotation, range_ext, tails, composite)
            if rotation_result:
                results['rotation'] = {
                    'code': f"{rotation},{range_ext},{tails},{composite}",
                    'score': rotation_result['score'],
                    'direction': rotation_result['direction'],
                    'comments': rotation_result['detailed_comments']
                }
            else:
                results['rotation'] = {
                    'code': f"{rotation},{range_ext},{tails},{composite}",
                    'error': 'No prediction found for this combination'
                }
        
        # Query volume prediction
        if all([vol_daily, vol_avg, va_placement, va_width]):
            volume_result = query_volume_prediction(vol_daily, vol_avg, va_placement, va_width)
            if volume_result:
                results['volume'] = {
                    'code': f"{vol_daily},{vol_avg},{va_placement},{va_width}",
                    'performance_strength': volume_result['performance_strength'],
                    'detailed_comments': volume_result['detailed_comments'],
                    'expected_results': volume_result['expected_results']
                }
            else:
                results['volume'] = {
                    'code': f"{vol_daily},{vol_avg},{va_placement},{va_width}",
                    'error': 'No prediction found for this combination'
                }
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in daily summary query: {error_trace}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/save-analysis', methods=['POST'])
def save_analysis():
    """Save analysis result to Supabase database"""
    try:
        data = request.json
        
        # Extract required fields
        symbol = data.get('symbol')
        coin = data.get('coin') or data.get('asset') or symbol.replace('USDT', '')
        analysis_date = data.get('analysis_date') or data.get('date') or datetime.now().strftime('%Y-%m-%d')
        
        # Extract prediction data
        input_code = data.get('input_code')
        score = data.get('score')
        direction = data.get('direction')
        market_analysis = data.get('market_analysis')
        
        # Extract metadata
        interval = data.get('interval')
        tpo_period = data.get('tpo_period')
        days_analyzed = data.get('days_analyzed') or data.get('days')
        
        # Convert days to integer if possible
        if days_analyzed:
            try:
                days_analyzed = int(days_analyzed)
            except (ValueError, TypeError):
                days_analyzed = None
        
        # Store full data as JSON
        full_analysis_data = {
            'timestamp': data.get('timestamp'),
            'rotation_data': data.get('rotation_data'),
            'volume_data': data.get('volume_data'),
            'additional_metrics': data.get('additional_metrics')
        }
        
        # Validate required fields
        if not symbol or not coin:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: symbol and coin'
            }), 400
        
        # Save to Supabase
        result = save_analysis_result(
            symbol=symbol,
            coin=coin,
            analysis_date=analysis_date,
            input_code=input_code,
            score=score,
            direction=direction,
            market_analysis=market_analysis,
            interval=interval,
            tpo_period=tpo_period,
            days_analyzed=days_analyzed,
            full_analysis_data=full_analysis_data
        )
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error saving analysis: {error_trace}")
        return jsonify({
            'success': False,
            'error': str(e),
            'trace': error_trace
        }), 500


@app.route('/api/analysis-history', methods=['GET'])
def analysis_history():
    """Get analysis history from database"""
    try:
        # Get query parameters
        symbol = request.args.get('symbol')
        coin = request.args.get('coin')
        limit = request.args.get('limit', 50, type=int)
        
        # Get history
        result = get_analysis_history(
            symbol=symbol,
            coin=coin,
            limit=limit
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/recent-analyses', methods=['GET'])
def recent_analyses():
    """Get most recent analyses"""
    try:
        limit = request.args.get('limit', 10, type=int)
        result = get_recent_analyses(limit=limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download-pdf-with-images', methods=['POST'])
def download_pdf_with_images():
    """Generate comprehensive PDF report with screenshots of all analysis results"""
    try:
        data = request.get_json()
        images = data.get('images', [])
        
        print(f"Received PDF generation request with {len(images)} images")
        
        # Get form parameters
        symbol = data.get('symbol', 'N/A')
        asset = data.get('asset', 'N/A')
        interval = data.get('interval', 'N/A')
        tpo_period = data.get('tpo_period', 'N/A')
        days = data.get('days', 'N/A')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        
        # Determine date range description
        if start_date and end_date:
            date_range = f"{start_date} to {end_date}"
        else:
            date_range = f"Last {days} days"
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              rightMargin=36, leftMargin=36,
                              topMargin=36, bottomMargin=36)
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # COVER PAGE
        elements.append(Spacer(1, 2*inch))
        title = Paragraph(f"Cryptocurrency TPO Analysis Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 40))
        
        # Analysis Info Box
        info_data = [
            ['Coin Symbol:', symbol],
            ['Asset:', asset],
            ['Timeframe:', interval],
            ['TPO Period:', tpo_period],
            ['Date Range:', date_range],
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        elements.append(info_table)
        
        elements.append(PageBreak())
        
        # Add each captured image as a separate page
        for idx, img_data in enumerate(images):
            try:
                print(f"Processing image {idx + 1}/{len(images)}")
                # Remove data:image/png;base64, prefix
                img_data = img_data.split(',')[1] if ',' in img_data else img_data
                img_bytes = base64.b64decode(img_data)
                img_buffer = io.BytesIO(img_bytes)
                
                # Open image with PIL to get actual dimensions
                pil_img = PILImage.open(img_buffer)
                img_width, img_height = pil_img.size
                print(f"Original image size: {img_width}x{img_height}")
                
                # Reset buffer for ReportLab
                img_buffer.seek(0)
                
                # Calculate available space (with margins)
                # Letter size: 612x792 points, margins: 36 each side
                # Available: width = 612-72 = 540, height = 792-72 = 720
                # But ReportLab frame has some internal padding, so use slightly less
                max_width = doc.width - 10  # Subtract safety margin
                max_height = doc.height - 10  # Subtract safety margin
                
                print(f"Max dimensions: {max_width:.1f}x{max_height:.1f}")
                
                # Calculate aspect ratio
                aspect = img_height / img_width
                
                # Scale to fit within page dimensions with 10pt padding
                new_width = max_width
                new_height = new_width * aspect
                
                # If too tall, scale to fit height instead
                if new_height > max_height:
                    new_height = max_height
                    new_width = new_height / aspect
                
                print(f"Scaled image size: {new_width:.1f}x{new_height:.1f}")
                
                # Create ReportLab Image with explicit dimensions
                img = RLImage(img_buffer, width=new_width, height=new_height)
                
                elements.append(img)
                if idx < len(images) - 1:  # Don't add page break after last image
                    elements.append(PageBreak())
            except Exception as img_error:
                print(f"Error processing image {idx + 1}: {img_error}")
                import traceback
                traceback.print_exc()
                # Continue with other images
                continue
        
        # Build PDF
        print("Building PDF document...")
        doc.build(elements)
        print("PDF built successfully")
        
        # Prepare for download
        buffer.seek(0)
        pdf_size = len(buffer.getvalue())
        print(f"PDF size: {pdf_size} bytes")
        
        filename = f"TPO_Analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error generating PDF with images: {error_trace}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download-pdf', methods=['GET'])
def download_pdf():
    """Generate and download PDF report"""
    try:
        if 'latest' not in analysis_results:
            return jsonify({'success': False, 'error': 'No analysis results available'}), 400
        
        results = analysis_results['latest']
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        )
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            spaceBefore=8
        )
        
        # COVER PAGE
        title = Paragraph(f"Cryptocurrency TPO Analysis Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 30))
        
        # Analysis Info Box
        info_data = [
            ['Symbol:', results['symbol']],
            ['Asset:', results['asset']],
            ['Interval:', results['interval']],
            ['TPO Period:', results['tpo_period']],
            ['Days Analyzed:', str(results['days'])],
            ['Generated:', results['timestamp']]
        ]
        
        info_table = Table(info_data, colWidths=[2.5*inch, 3.5*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 40))
        
        # Analyses Selected
        analyses_selected = []
        if 'tpo' in results['analyses']:
            analyses_selected.append('TPO Analysis')
        if 'rotation' in results['analyses']:
            analyses_selected.append('Rotation Factor Analysis')
        if 'daily' in results['analyses']:
            analyses_selected.append('Daily Analysis')
        if 'poc' in results['analyses']:
            analyses_selected.append('POC Movement Analysis')
        
        if analyses_selected:
            elements.append(Paragraph("Analyses Performed", heading_style))
            for analysis in analyses_selected:
                elements.append(Paragraph(f"• {analysis}", styles['Normal']))
            elements.append(Spacer(1, 20))
        
        # Table of Contents
        elements.append(Paragraph("Table of Contents", heading_style))
        toc_items = []
        page_num = 2
        if 'tpo' in results['analyses']:
            toc_items.append([f"Page {page_num}", "TPO Analysis"])
            page_num += 1
        if 'rotation' in results['analyses']:
            toc_items.append([f"Page {page_num}", "Auction Rotation Factor Analysis"])
            page_num += 1
        if 'daily' in results['analyses']:
            toc_items.append([f"Page {page_num}", "Daily Analysis"])
            page_num += 1
        if 'poc' in results['analyses']:
            toc_items.append([f"Page {page_num}", "POC Movement Analysis"])
        
        if toc_items:
            toc_table = Table(toc_items, colWidths=[1.5*inch, 4.5*inch])
            toc_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            elements.append(toc_table)
        
        elements.append(PageBreak())
        
        
        # ============================================================
        # PAGE 1: TPO ANALYSIS
        # ============================================================
        if 'tpo' in results['analyses']:
            elements.append(Paragraph("TPO Analysis", title_style))
            elements.append(Spacer(1, 20))
            tpo = results['analyses']['tpo']
            
            # Summary metrics
            elements.append(Paragraph("Analysis Summary", heading_style))
            tpo_data = [
                ['Total TPO Blocks', str(tpo['tpo_blocks'])],
                ['Time Brackets', str(tpo['time_brackets'])],
                ['Daily Sessions', str(tpo['daily_sessions'])]
            ]
            
            tpo_table = Table(tpo_data, colWidths=[3*inch, 3*inch])
            tpo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10)
            ]))
            elements.append(tpo_table)
            elements.append(Spacer(1, 20))
            
            # Long Term Profile if available
            if tpo.get('tpo_density') and len(tpo['tpo_density']) > 0:
                elements.append(Spacer(1, 20))
                elements.append(Paragraph("Long Term Profile", heading_style))
                elements.append(Paragraph("Top 10 Most Traded Price Levels", subheading_style))
                elements.append(Spacer(1, 10))
                
                density_df = pd.DataFrame(tpo['tpo_density'])
                top_density = density_df.head(10)
                
                density_table_data = [['Price', 'Days', 'TPO Count']]
                for _, row in top_density.iterrows():
                    density_parts = row['TPO DENSITY'].split(' ')
                    count = density_parts[0]
                    density_table_data.append([
                        str(row['PRICE']),
                        str(row['DYS TPO']),
                        count
                    ])
                
                density_table = Table(density_table_data)
                density_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8)
                ]))
                elements.append(density_table)
            
            elements.append(PageBreak())
        
        
        # ============================================================
        # PAGE 2: ROTATION FACTOR ANALYSIS
        # ============================================================
        if 'rotation' in results['analyses']:
            elements.append(Paragraph("Auction Rotation Factor Analysis", title_style))
            elements.append(Spacer(1, 20))
            rotation_data = results['analyses']['rotation']
            
            if rotation_data and len(rotation_data) > 0:
                # Calculate summary statistics
                total_net = sum(item['net_rotation'] for item in rotation_data)
                bullish_days = len([r for r in rotation_data if r['net_rotation'] > 0])
                bearish_days = len([r for r in rotation_data if r['net_rotation'] < 0])
                neutral_days = len([r for r in rotation_data if r['net_rotation'] == 0])
                
                # Summary section
                elements.append(Paragraph("Analysis Summary", heading_style))
                summary_data = [
                    ['Total Net Rotation', f"{total_net:.2f}"],
                    ['Bullish Days', str(bullish_days)],
                    ['Bearish Days', str(bearish_days)],
                    ['Neutral Days', str(neutral_days)],
                    ['Total Days Analyzed', str(len(rotation_data))]
                ]
                
                summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e74c3c')),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 10)
                ]))
                elements.append(summary_table)
                elements.append(Spacer(1, 20))
                
                # Daily rotation details
                elements.append(Paragraph("Daily Rotation Factors", heading_style))
                elements.append(Spacer(1, 10))
                
                rotation_table_data = [['Date', 'Net Rotation', 'Up Rotations', 'Down Rotations', 'Bias']]
                for item in rotation_data[-20:]:  # Last 20 days
                    bias = '🟢 BULL' if item['net_rotation'] > 0 else ('🔴 BEAR' if item['net_rotation'] < 0 else '⚪ FLAT')
                    rotation_table_data.append([
                        str(item['date']),
                        f"{item['net_rotation']:+.2f}",
                        f"{item['total_up']:.2f}",
                        f"{item['total_down']:.2f}",
                        bias
                    ])
                
                rotation_table = Table(rotation_table_data, repeatRows=1)
                rotation_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6)
                ]))
                elements.append(rotation_table)
            
            elements.append(PageBreak())
        
        
        # ============================================================
        # PAGE 3: DAILY ANALYSIS
        # ============================================================
        if 'daily' in results['analyses']:
            elements.append(Paragraph("Daily Analysis", title_style))
            elements.append(Spacer(1, 20))
            daily = results['analyses']['daily']
            
            # Display the report if available
            if 'report' in daily and daily['report']:
                report = daily['report']
                
                for row in report:
                    # Timeframe header
                    elements.append(Paragraph(f"{row.get('Timeframe', 'N/A')} Timeframe Analysis", heading_style))
                    elements.append(Spacer(1, 10))
                    
                    # Control and Trend
                    control_trend_data = [
                        ['Market Control', row.get('Control', 'N/A')],
                        ['Trend Direction', row.get('Trend', 'N/A')]
                    ]
                    control_table = Table(control_trend_data, colWidths=[2.5*inch, 3.5*inch])
                    control_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f39c12')),
                        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 11),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                        ('TOPPADDING', (0, 0), (-1, -1), 10)
                    ]))
                    elements.append(control_table)
                    elements.append(Spacer(1, 15))
                    
                    # Volume and Value Area Analysis
                    elements.append(Paragraph("Volume & Value Area Analysis", subheading_style))
                    volume_data = [
                        ['Period', 'Date', 'Total Volume', 'VA Volume', 'VAH', 'VAL'],
                        ['Today', row.get('Date_Today', 'N/A'), row.get('Volume_Today', 'N/A'), row.get('VA_Vol_Today', 'N/A'), 
                         row.get('VAH_Today', 'N/A'), row.get('VAL_Today', 'N/A')],
                        ['Yesterday', row.get('Date_Yesterday', 'N/A'), row.get('Volume_Yesterday', 'N/A'), row.get('VA_Vol_Yesterday', 'N/A'),
                         row.get('VAH_Yesterday', 'N/A'), row.get('VAL_Yesterday', 'N/A')],
                        ['2 Days Ago', row.get('Date_2_Days_Ago', 'N/A'), row.get('Volume_2_Days_Ago', 'N/A'), row.get('VA_Vol_2_Days_Ago', 'N/A'),
                         row.get('VAH_2_Days_Ago', 'N/A'), row.get('VAL_2_Days_Ago', 'N/A')]
                    ]
                    volume_table = Table(volume_data, repeatRows=1)
                    volume_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e3f2fd'), colors.white]),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 8)
                    ]))
                    elements.append(volume_table)
                    elements.append(Spacer(1, 15))
                    
                    # Rotation Analysis
                    elements.append(Paragraph("Rotation Analysis", subheading_style))
                    rotation_data = [
                        ['Period', 'Date', 'Rotation'],
                        ['Today', row.get('Date_Today', 'N/A'), row.get('Rotation_Today', 'N/A')],
                        ['Yesterday', row.get('Date_Yesterday', 'N/A'), row.get('Rotation_Yesterday', 'N/A')],
                        ['2 Days Ago', row.get('Date_2_Days_Ago', 'N/A'), row.get('Rotation_2_Days_Ago', 'N/A')]
                    ]
                    rotation_table = Table(rotation_data, colWidths=[2*inch, 2*inch, 2*inch], repeatRows=1)
                    rotation_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e8f8f5'), colors.white]),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 8)
                    ]))
                    elements.append(rotation_table)
                    elements.append(Spacer(1, 20))
            
            elements.append(PageBreak())
        
        
        # ============================================================
        # PAGE 4: POC MOVEMENT ANALYSIS
        # ============================================================
        if 'poc' in results['analyses']:
            elements.append(Paragraph("POC Movement Analysis", title_style))
            elements.append(Spacer(1, 20))
            poc = results['analyses']['poc']
            
            # Summary section
            if 'bias' in poc:
                elements.append(Paragraph("Analysis Summary", heading_style))
                summary_data = [
                    ['Market Bias', poc.get('bias', 'N/A')],
                    ['Bias Score', str(poc.get('bias_score', 'N/A'))],
                    ['Days Analyzed', str(poc.get('days_analyzed', 'N/A'))],
                    ['Upward Moves', str(poc.get('upward_moves', 'N/A'))],
                    ['Downward Moves', str(poc.get('downward_moves', 'N/A'))]
                ]
                
                summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#9b59b6')),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 10)
                ]))
                elements.append(summary_table)
                elements.append(Spacer(1, 20))
            
            # Daily POC movements
            if 'daily_pocs' in poc and poc['daily_pocs']:
                elements.append(Paragraph("Daily POC Movement", heading_style))
                elements.append(Spacer(1, 10))
                
                poc_table_data = [['Date', 'POC', 'Change', 'Direction']]
                daily_pocs = poc['daily_pocs'][-20:]  # Last 20 days
                
                for i, item in enumerate(daily_pocs):
                    change = 'N/A'
                    direction = '-'
                    if i > 0:
                        prev_poc = daily_pocs[i-1].get('poc', 0)
                        curr_poc = item.get('poc', 0)
                        change_val = curr_poc - prev_poc
                        change = f"{change_val:+.2f}"
                        direction = '↑' if change_val > 0 else ('↓' if change_val < 0 else '→')
                    
                    poc_table_data.append([
                        str(item.get('date', 'N/A')),
                        f"{item.get('poc', 0):.2f}",
                        change,
                        direction
                    ])
                
                poc_table = Table(poc_table_data, repeatRows=1)
                poc_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6)
                ]))
                elements.append(poc_table)
        
        # Build PDF
        doc.build(elements)
        
        # Prepare for download
        buffer.seek(0)
        filename = f"TPO_Analysis_{results['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error generating PDF: {error_trace}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
