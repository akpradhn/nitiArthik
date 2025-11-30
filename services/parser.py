"""
PDF Transaction Parser Service

This module handles parsing of bank statements and credit card bills from PDF files.
It uses pdfplumber to extract tables and attempts to identify transaction rows.
"""

import pdfplumber
from datetime import datetime
from decimal import Decimal
import re
import json
from typing import List, Dict, Optional, Tuple
from models import TransactionDirection

# Keywords to identify relevant columns (expanded for Indian banks)
DATE_KEYWORDS = ['date', 'transaction date', 'value date', 'tran date', 'tdate', 'posting date', 'post date', 'tran. date', 'value date', 'val date']
DESCRIPTION_KEYWORDS = ['description', 'narration', 'particulars', 'details', 'transaction details', 'remarks', 'narration/particulars', 'transaction', 'transaction description', 'particulars of transaction', 'narration of transaction']
DEBIT_KEYWORDS = ['debit', 'withdrawal', 'dr', 'paid', 'out', 'debit amount', 'withdrawal amount', 'dr.', 'debit (dr)']
CREDIT_KEYWORDS = ['credit', 'deposit', 'cr', 'received', 'in', 'credit amount', 'deposit amount', 'cr.', 'credit (cr)']
AMOUNT_KEYWORDS = ['amount', 'transaction amount', 'value', 'transaction value', 'amt', 'amount (inr)', 'amount(inr)']
BALANCE_KEYWORDS = ['balance', 'closing balance', 'running balance', 'available balance', 'balance amount', 'closing bal', 'balance (inr)', 'balance(inr)']

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    # Replace newlines and multiple spaces with single space
    text = str(text).replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
    return text.lower().strip()

def find_column_indices(headers: List[str]) -> Dict[str, Optional[int]]:
    """
    Identify column indices for date, description, debit, credit, amount, and balance.
    
    Returns a dict with keys: date_idx, desc_idx, debit_idx, credit_idx, amount_idx, balance_idx
    """
    indices = {
        'date_idx': None,
        'desc_idx': None,
        'debit_idx': None,
        'credit_idx': None,
        'amount_idx': None,
        'balance_idx': None
    }
    
    for i, header in enumerate(headers):
        if header is None:
            continue
            
        header_norm = normalize_text(str(header))
        # Also check if any keyword appears anywhere in the header (for multi-line headers)
        header_words = header_norm.split()
        
        # Date column
        if indices['date_idx'] is None:
            # Check if any date keyword is in the header or header words
            if any(kw in header_norm for kw in DATE_KEYWORDS) or \
               any(kw in word for word in header_words for kw in DATE_KEYWORDS):
                indices['date_idx'] = i
        
        # Description column - be more flexible with "Transaction Details" etc.
        if indices['desc_idx'] is None:
            # Check if any description keyword is in the header
            if any(kw in header_norm for kw in DESCRIPTION_KEYWORDS) or \
               any(kw in word for word in header_words for kw in DESCRIPTION_KEYWORDS) or \
               'transaction' in header_norm and 'detail' in header_norm:
                indices['desc_idx'] = i
        
        # Debit column
        if indices['debit_idx'] is None and any(kw in header_norm for kw in DEBIT_KEYWORDS):
            indices['debit_idx'] = i
        
        # Credit column
        if indices['credit_idx'] is None and any(kw in header_norm for kw in CREDIT_KEYWORDS):
            indices['credit_idx'] = i
        
        # Amount column (generic)
        if indices['amount_idx'] is None and any(kw in header_norm for kw in AMOUNT_KEYWORDS):
            indices['amount_idx'] = i
        
        # Balance column
        if indices['balance_idx'] is None and any(kw in header_norm for kw in BALANCE_KEYWORDS):
            indices['balance_idx'] = i
    
    return indices

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string in various formats."""
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Common date formats
    formats = [
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y-%m-%d',
        '%d-%b-%Y',
        '%d %b %Y',
        '%d-%m-%y',
        '%d/%m/%y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    # Try regex for formats like "01-Jan-2024"
    date_patterns = [
        r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})',
        r'(\d{1,2})[-/](\d{1,2})[-/](\d{2})',
        r'(\d{1,2})\s+(\w{3})\s+(\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                parts = match.groups()
                if len(parts) == 3:
                    # Try to construct date
                    day, month, year = parts
                    if len(year) == 2:
                        year = '20' + year
                    return datetime.strptime(f"{day}-{month}-{year}", '%d-%m-%Y').date()
            except:
                continue
    
    return None

def parse_amount(amount_str: str) -> Optional[Decimal]:
    """Parse amount string, handling commas, currency symbols, etc."""
    if not amount_str:
        return None
    
    amount_str = str(amount_str).strip()
    
    # Handle empty or dash/blank indicators
    if amount_str in ['-', '--', '', ' ', 'NIL', 'Nil', 'nil']:
        return None
    
    # Remove currency symbols (₹, Rs, Rs., INR, etc.)
    amount_str = re.sub(r'[₹RsRs\.INR\s]', '', amount_str, flags=re.IGNORECASE)
    
    # Remove commas (Indian number format uses commas)
    amount_str = amount_str.replace(',', '')
    
    # Extract number (including negative)
    # Match patterns like: -1234.56, 1234.56, 1234, -1234
    match = re.search(r'(-?\d+\.?\d*)', amount_str)
    if match:
        try:
            value = Decimal(match.group(1))
            # Return None for zero amounts (they're usually placeholders)
            if value == 0:
                return None
            return value
        except:
            pass
    
    return None

def infer_direction_from_description(description: str, amount: Decimal) -> TransactionDirection:
    """
    Infer transaction direction from description keywords or amount sign.
    This is a heuristic and may need customization per bank.
    """
    desc_lower = normalize_text(description)
    
    # Credit indicators
    credit_keywords = ['credit', 'deposit', 'salary', 'interest', 'refund', 'reversal', 'transfer in']
    if any(kw in desc_lower for kw in credit_keywords):
        return TransactionDirection.CREDIT
    
    # Debit indicators
    debit_keywords = ['debit', 'withdrawal', 'payment', 'pos', 'atm', 'neft', 'imps', 'upi', 'emi', 'charges']
    if any(kw in desc_lower for kw in debit_keywords):
        return TransactionDirection.DEBIT
    
    # If amount is negative, likely debit
    if amount < 0:
        return TransactionDirection.DEBIT
    
    # Default: assume debit for expenses (can be customized)
    return TransactionDirection.DEBIT

def extract_transactions_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extract transactions from a PDF file.
    
    Returns a list of transaction dictionaries with keys:
    - date, description, amount, direction, balance_after, raw_row_data
    """
    transactions = []
    pages_processed = 0
    tables_found = 0
    tables_with_headers = 0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Processing PDF with {total_pages} pages: {pdf_path}")
            
            for page_num, page in enumerate(pdf.pages):
                # Try multiple extraction strategies
                tables = page.extract_tables()
                pages_processed += 1
                
                # If no tables found with default method, try with different settings
                if not tables:
                    print(f"  Page {page_num + 1}: No tables found with default extraction. Trying alternative methods...")
                    # Try with explicit table settings
                    try:
                        tables = page.extract_tables({
                            "vertical_strategy": "lines_strict",
                            "horizontal_strategy": "lines_strict"
                        })
                    except:
                        try:
                            tables = page.extract_tables({
                                "vertical_strategy": "text",
                                "horizontal_strategy": "text"
                            })
                        except:
                            pass
                
                # If still no tables, try to extract text and look for patterns
                if not tables:
                    print(f"  Page {page_num + 1}: Trying text-based extraction...")
                    text = page.extract_text()
                    if text:
                        # Try to find transaction-like patterns in text
                        # This is a fallback for non-tabular PDFs
                        print(f"  Page {page_num + 1}: Found text content ({len(text)} chars), but table extraction failed")
                        # Try alternative table extraction with different strategies
                        try:
                            # Try with explicit lines
                            tables = page.extract_tables({
                                "vertical_strategy": "explicit",
                                "horizontal_strategy": "explicit"
                            })
                            if tables:
                                print(f"  Page {page_num + 1}: Found {len(tables)} tables with explicit strategy")
                        except:
                            pass
                        
                        if not tables:
                            # Try with text-based strategy
                            try:
                                tables = page.extract_tables({
                                    "vertical_strategy": "text",
                                    "horizontal_strategy": "text"
                                })
                                if tables:
                                    print(f"  Page {page_num + 1}: Found {len(tables)} tables with text strategy")
                            except:
                                pass
                        
                        if not tables:
                            print(f"  Page {page_num + 1}: First 500 chars of text: {text[:500]}")
                    
                    if not tables:
                        continue
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    tables_found += 1
                    
                    # First row is likely headers
                    headers = table[0]
                    indices = find_column_indices(headers)
                    
                    # Debug: Print headers to see what we're working with
                    # Clean headers for display (remove newlines)
                    clean_headers = [str(h).replace('\n', ' ') if h else None for h in headers]
                    print(f"  Page {page_num + 1}: Found table with {len(table)} rows. Headers: {clean_headers}")
                    
                    # Also print first few data rows for debugging
                    if len(table) > 1:
                        print(f"  Page {page_num + 1}: First data row: {table[1]}")
                        if len(table) > 2:
                            print(f"  Page {page_num + 1}: Second data row: {table[2]}")
                    
                    # Skip if we don't have essential columns
                    if indices['date_idx'] is None or indices['desc_idx'] is None:
                        print(f"  Page {page_num + 1}: Table found but missing date or description columns.")
                        print(f"    Date index: {indices['date_idx']}, Desc index: {indices['desc_idx']}")
                        print(f"    All indices: {indices}")
                        
                        # Try to be more flexible - maybe first column is date, second is description
                        if len(headers) >= 2:
                            print(f"  Page {page_num + 1}: Attempting fallback - assuming first column is date, second is description")
                            if indices['date_idx'] is None:
                                indices['date_idx'] = 0
                            if indices['desc_idx'] is None:
                                indices['desc_idx'] = 1
                            # Try to find amount in remaining columns
                            for i in range(2, len(headers)):
                                if headers[i] is None:
                                    continue
                                header_norm = normalize_text(str(headers[i]))
                                if any(kw in header_norm for kw in AMOUNT_KEYWORDS + DEBIT_KEYWORDS + CREDIT_KEYWORDS):
                                    if indices['amount_idx'] is None:
                                        indices['amount_idx'] = i
                                    if indices['debit_idx'] is None and any(kw in header_norm for kw in DEBIT_KEYWORDS):
                                        indices['debit_idx'] = i
                                    if indices['credit_idx'] is None and any(kw in header_norm for kw in CREDIT_KEYWORDS):
                                        indices['credit_idx'] = i
                        else:
                            continue
                    
                    # Final check - we must have date and description
                    if indices['date_idx'] is None or indices['desc_idx'] is None:
                        print(f"  Page {page_num + 1}: Still missing required columns after fallback. Skipping table.")
                        continue
                    
                    tables_with_headers += 1
                    rows_processed = 0
                    
                    # Process data rows
                    for row in table[1:]:
                        if not row:
                            continue
                        
                        # Check if row has enough columns
                        max_idx = max(i for i in indices.values() if i is not None)
                        if len(row) <= max_idx:
                            continue
                        
                        # Extract date - handle None values in cells
                        date_str = None
                        if indices['date_idx'] is not None and indices['date_idx'] < len(row):
                            date_cell = row[indices['date_idx']]
                            if date_cell is not None:
                                date_str = str(date_cell).strip()
                        
                        date = parse_date(date_str) if date_str else None
                        
                        if not date:
                            # Try to parse date from description if date column failed
                            if indices['desc_idx'] is not None and indices['desc_idx'] < len(row):
                                desc_cell = row[indices['desc_idx']]
                                if desc_cell:
                                    # Look for date pattern in description
                                    date_match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})', str(desc_cell))
                                    if date_match:
                                        date = parse_date(date_match.group(0))
                            
                            if not date:
                                continue  # Skip rows without valid date
                        
                        # Extract description - handle None values
                        desc = ""
                        if indices['desc_idx'] is not None and indices['desc_idx'] < len(row):
                            desc_cell = row[indices['desc_idx']]
                            if desc_cell is not None:
                                desc = str(desc_cell).strip()
                        
                        if not desc or len(desc) < 3:
                            continue  # Skip empty descriptions
                        
                        # Extract amount and direction
                        amount = None
                        direction = None
                        
                        # Case 1: Separate debit and credit columns
                        if indices['debit_idx'] is not None and indices['credit_idx'] is not None:
                            debit_str = None
                            credit_str = None
                            
                            if indices['debit_idx'] < len(row) and row[indices['debit_idx']] is not None:
                                debit_str = str(row[indices['debit_idx']]).strip()
                            if indices['credit_idx'] < len(row) and row[indices['credit_idx']] is not None:
                                credit_str = str(row[indices['credit_idx']]).strip()
                            
                            debit_amt = parse_amount(debit_str) if debit_str else None
                            credit_amt = parse_amount(credit_str) if credit_str else None
                            
                            if debit_amt and debit_amt > 0:
                                amount = abs(debit_amt)
                                direction = TransactionDirection.DEBIT
                            elif credit_amt and credit_amt > 0:
                                amount = abs(credit_amt)
                                direction = TransactionDirection.CREDIT
                        
                        # Case 2: Single amount column
                        elif indices['amount_idx'] is not None:
                            amount_str = None
                            if indices['amount_idx'] < len(row) and row[indices['amount_idx']] is not None:
                                amount_str = str(row[indices['amount_idx']]).strip()
                            
                            amount = parse_amount(amount_str) if amount_str else None
                            
                            if amount:
                                amount = abs(amount)
                                # Infer direction from description or amount sign
                                direction = infer_direction_from_description(desc, amount)
                        
                        # Case 3: Try to find amount in any numeric column if not found yet
                        if not amount or amount == 0:
                            # Look through all columns for a numeric value that could be an amount
                            for col_idx in range(len(row)):
                                if col_idx in [indices.get('date_idx'), indices.get('desc_idx')]:
                                    continue
                                if col_idx < len(row) and row[col_idx] is not None:
                                    cell_value = str(row[col_idx]).strip()
                                    potential_amount = parse_amount(cell_value)
                                    if potential_amount and potential_amount > 0:
                                        amount = abs(potential_amount)
                                        direction = infer_direction_from_description(desc, amount)
                                        break
                        
                        if not amount or amount == 0:
                            continue
                        
                        # Extract balance - handle None values
                        balance_after = None
                        if indices['balance_idx'] is not None and indices['balance_idx'] < len(row):
                            balance_cell = row[indices['balance_idx']]
                            if balance_cell is not None:
                                balance_str = str(balance_cell).strip()
                                balance_after = parse_amount(balance_str) if balance_str else None
                        
                        # Store raw row data for debugging
                        raw_row_data = json.dumps({
                            'row': row,
                            'page': page_num + 1
                        })
                        
                        transactions.append({
                            'date': date,
                            'description': desc,
                            'amount': amount,
                            'direction': direction,
                            'balance_after': balance_after,
                            'raw_row_data': raw_row_data
                        })
                        rows_processed += 1
                    
                    if rows_processed > 0:
                        print(f"  Page {page_num + 1}: Extracted {rows_processed} transactions from table")
            
            print(f"Parsing complete: {pages_processed} pages, {tables_found} tables found, {tables_with_headers} tables with valid headers, {len(transactions)} transactions extracted")
    
    except Exception as e:
        error_msg = f"Error parsing PDF: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)
    
    if len(transactions) == 0:
        print("WARNING: No transactions extracted from PDF. This could mean:")
        print("  - The PDF doesn't contain tabular data")
        print("  - The table structure doesn't match expected format")
        print("  - The PDF is image-based (scanned) without text layer")
    
    return transactions


