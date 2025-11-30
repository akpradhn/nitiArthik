from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Account, UploadedFile, AccountType, ParseStatus, Transaction, TransactionDirection
from services.parser import extract_transactions_from_pdf
from services.gemini_parser import extract_transactions_with_gemini
import os
from datetime import datetime
import threading

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_pdf_file(file_record_id):
    """Background task to parse PDF and extract transactions."""
    # Import here to avoid circular import - by the time this runs, modules are loaded
    from app import app
    from models import db, UploadedFile, Transaction, ParseStatus
    import traceback
    
    with app.app_context():
        # Reload file_record in this context
        file_record = UploadedFile.query.get(file_record_id)
        if not file_record:
            return
        
        try:
            # Update status to PROCESSING
            file_record.parse_status = ParseStatus.PROCESSING
            db.session.commit()
            
            # Check if file exists
            if not os.path.exists(file_record.stored_file_path):
                raise FileNotFoundError(f"PDF file not found at: {file_record.stored_file_path}")
            
            # Try Gemini parser first (if API key is available), fallback to pdfplumber
            transactions_data = []
            use_gemini = os.environ.get('GOOGLE_GEMINI_API_KEY') is not None
            
            if use_gemini:
                try:
                    print(f"Attempting to parse with Gemini AI...")
                    transactions_data = extract_transactions_with_gemini(file_record.stored_file_path)
                    print(f"Gemini extracted {len(transactions_data)} transactions")
                except Exception as gemini_error:
                    print(f"Gemini parsing failed: {gemini_error}")
                    print("Falling back to pdfplumber parser...")
                    # Fallback to pdfplumber
                    transactions_data = extract_transactions_from_pdf(file_record.stored_file_path)
            else:
                print("Using pdfplumber parser (Gemini API key not configured)...")
                transactions_data = extract_transactions_from_pdf(file_record.stored_file_path)
            
            if not transactions_data:
                raise Exception("No transactions found in PDF. The PDF may not contain a recognizable table structure.")
            
            # Save transactions
            transaction_count = 0
            for txn_data in transactions_data:
                transaction = Transaction(
                    user_id=file_record.user_id,
                    account_id=file_record.account_id,
                    file_id=file_record.id,
                    date=txn_data['date'],
                    description=txn_data['description'],
                    amount=txn_data['amount'],
                    direction=txn_data['direction'],
                    balance_after=txn_data.get('balance_after'),
                    currency='INR',
                    category='Uncategorized',
                    raw_row_data=txn_data.get('raw_row_data')
                )
                db.session.add(transaction)
                transaction_count += 1
            
            # Update status to SUCCESS
            file_record.parse_status = ParseStatus.SUCCESS
            file_record.parse_error = None
            db.session.commit()
            
            print(f"Successfully parsed {transaction_count} transactions from {file_record.original_file_name}")
            
        except Exception as e:
            # Update status to FAILED with detailed error
            error_msg = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            file_record.parse_status = ParseStatus.FAILED
            file_record.parse_error = error_msg[:1000]  # Limit error message length
            db.session.commit()
            print(f"Error parsing {file_record.original_file_name}: {str(e)}")

@upload_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # Get form data
        account_type_str = request.form.get('account_type')
        account_nickname = request.form.get('account_nickname', '').strip()
        existing_account_id = request.form.get('existing_account_id')
        statement_start = request.form.get('statement_start')
        statement_end = request.form.get('statement_end')
        
        # Parse dates
        start_date = None
        end_date = None
        if statement_start:
            try:
                start_date = datetime.strptime(statement_start, '%Y-%m-%d').date()
            except:
                pass
        if statement_end:
            try:
                end_date = datetime.strptime(statement_end, '%Y-%m-%d').date()
            except:
                pass
        
        # Validate
        if not account_type_str or account_type_str not in ['BANK', 'CREDIT_CARD']:
            flash('Please select a valid account type.', 'error')
            return redirect(url_for('upload.index'))
        
        # Get or create account
        if existing_account_id:
            account = Account.query.filter_by(
                id=int(existing_account_id),
                user_id=current_user.id
            ).first()
            if not account:
                flash('Selected account not found.', 'error')
                return redirect(url_for('upload.index'))
        else:
            if not account_nickname:
                flash('Please provide an account nickname.', 'error')
                return redirect(url_for('upload.index'))
            
            # Check if account with same nickname exists
            account = Account.query.filter_by(
                user_id=current_user.id,
                nickname=account_nickname,
                account_type=AccountType[account_type_str]
            ).first()
            
            if not account:
                account = Account(
                    user_id=current_user.id,
                    account_type=AccountType[account_type_str],
                    nickname=account_nickname
                )
                db.session.add(account)
                db.session.commit()
        
        # Handle file uploads
        if 'files' not in request.files:
            flash('No files selected.', 'error')
            return redirect(url_for('upload.index'))
        
        files = request.files.getlist('files')
        uploaded_count = 0
        
        for file in files:
            if file.filename == '':
                continue
            
            if not allowed_file(file.filename):
                flash(f'{file.filename} is not a PDF file.', 'error')
                continue
            
            # Save file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            unique_filename = f"{current_user.id}_{timestamp}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Create UploadedFile record
            uploaded_file = UploadedFile(
                user_id=current_user.id,
                account_id=account.id,
                original_file_name=filename,
                stored_file_path=file_path,
                parse_status=ParseStatus.PENDING,
                statement_start_date=start_date,
                statement_end_date=end_date
            )
            db.session.add(uploaded_file)
            db.session.commit()
            
            # Start background processing (pass ID to avoid issues with SQLAlchemy objects across threads)
            thread = threading.Thread(target=process_pdf_file, args=(uploaded_file.id,))
            thread.daemon = True
            thread.start()
            
            uploaded_count += 1
        
        if uploaded_count > 0:
            flash(f'Successfully uploaded {uploaded_count} file(s). Processing in background...', 'success')
        else:
            flash('No valid files were uploaded.', 'error')
        
        return redirect(url_for('upload.index'))
    
    # GET request - show upload form
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.created_at.desc()).all()
    uploaded_files = UploadedFile.query.filter_by(
        user_id=current_user.id
    ).order_by(UploadedFile.uploaded_at.desc()).limit(20).all()
    
    return render_template('upload/index.html', accounts=accounts, uploaded_files=uploaded_files)

@upload_bp.route('/upload/status/<int:file_id>')
@login_required
def file_status(file_id):
    """API endpoint to check file parsing status."""
    file_record = UploadedFile.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first_or_404()
    
    transaction_count = Transaction.query.filter_by(file_id=file_id).count()
    
    return jsonify({
        'status': file_record.parse_status.value,
        'error': file_record.parse_error,
        'transaction_count': transaction_count,
        'file_path': file_record.stored_file_path,
        'file_exists': os.path.exists(file_record.stored_file_path) if file_record.stored_file_path else False
    })

@upload_bp.route('/upload/retry/<int:file_id>', methods=['POST'])
@login_required
def retry_parse(file_id):
    """Retry parsing a failed file."""
    file_record = UploadedFile.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first_or_404()
    
    if file_record.parse_status == ParseStatus.PROCESSING:
        flash('File is already being processed.', 'info')
        return redirect(url_for('upload.index'))
    
    # Reset status and retry
    file_record.parse_status = ParseStatus.PENDING
    file_record.parse_error = None
    db.session.commit()
    
    # Start background processing
    thread = threading.Thread(target=process_pdf_file, args=(file_record.id,))
    thread.daemon = True
    thread.start()
    
    flash('Parsing restarted. Please check back in a moment.', 'success')
    return redirect(url_for('upload.index'))

@upload_bp.route('/upload/debug/<int:file_id>')
@login_required
def debug_pdf(file_id):
    """Debug endpoint to see PDF structure."""
    file_record = UploadedFile.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first_or_404()
    
    import pdfplumber
    debug_info = {
        'file_path': file_record.stored_file_path,
        'file_exists': os.path.exists(file_record.stored_file_path),
        'pages': [],
        'tables_found': 0
    }
    
    if os.path.exists(file_record.stored_file_path):
        try:
            with pdfplumber.open(file_record.stored_file_path) as pdf:
                debug_info['total_pages'] = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    text = page.extract_text()
                    debug_info['pages'].append({
                        'page_num': page_num + 1,
                        'tables_count': len(tables) if tables else 0,
                        'text_length': len(text) if text else 0,
                        'text_preview': text[:500] if text else None,
                        'table_headers': []
                    })
                    
                    if tables:
                        debug_info['tables_found'] += len(tables)
                        for table in tables[:3]:  # First 3 tables
                            if table and len(table) > 0:
                                debug_info['pages'][-1]['table_headers'].append(table[0])
        except Exception as e:
            debug_info['error'] = str(e)
    
    from flask import jsonify
    return jsonify(debug_info)

