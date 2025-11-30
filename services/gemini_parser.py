"""
Google Gemini-based PDF Transaction Parser Service

This module uses Google Gemini AI to parse bank statements and credit card bills from PDF files.
It's more flexible than table-based parsing and can handle various PDF formats.
"""

import google.generativeai as genai
from datetime import datetime
from decimal import Decimal
import json
import os
from typing import List, Dict, Optional
from models import TransactionDirection
import base64

def setup_gemini(api_key: Optional[str] = None):
    """Configure Gemini API with API key."""
    if not api_key:
        api_key = os.environ.get('GOOGLE_GEMINI_API_KEY')
    
    if not api_key:
        raise ValueError("Google Gemini API key not found. Set GOOGLE_GEMINI_API_KEY environment variable.")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash-lite')

def extract_transactions_with_gemini(pdf_path: str, api_key: Optional[str] = None) -> List[Dict]:
    """
    Extract transactions from a PDF file using Google Gemini AI.
    
    Args:
        pdf_path: Path to the PDF file
        api_key: Optional Gemini API key (uses env var if not provided)
    
    Returns:
        List of transaction dictionaries with keys:
        - date, description, amount, direction, balance_after, raw_row_data
    """
    try:
        model = setup_gemini(api_key)
        
        print(f"Using Gemini to parse PDF: {pdf_path}")
        
        # Read PDF file
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        
        # Create prompt for Gemini
        prompt = """You are a financial document parser. Extract all transactions from this bank statement or credit card bill PDF.

For each transaction, extract:
1. Date (in YYYY-MM-DD format)
2. Description/Narration (full transaction description)
3. Amount (as a positive number)
4. Direction (either "credit" or "debit")
   - Credit: Money coming in (deposits, refunds, credits)
   - Debit: Money going out (payments, purchases, withdrawals)
5. Balance After (if available, the balance after this transaction)

Return the transactions as a JSON array. Each transaction should be an object with these fields:
- date: string in YYYY-MM-DD format
- description: string
- amount: number (positive)
- direction: "credit" or "debit"
- balance_after: number or null

Example format:
[
  {
    "date": "2024-10-15",
    "description": "UPI Payment to Merchant ABC",
    "amount": 1500.00,
    "direction": "debit",
    "balance_after": 8500.00
  },
  {
    "date": "2024-10-16",
    "description": "Salary Credit",
    "amount": 50000.00,
    "direction": "credit",
    "balance_after": 13500.00
  }
]

Extract ALL transactions from the document. Return ONLY the JSON array, no other text."""

        # Upload PDF to Gemini
        print("Uploading PDF to Gemini...")
        pdf_part = {
            "mime_type": "application/pdf",
            "data": pdf_data
        }
        
        # Generate response
        print("Sending request to Gemini...")
        response = model.generate_content([prompt, pdf_part])
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        print(f"Gemini response received ({len(response_text)} chars)")
        print(f"First 500 chars: {response_text[:500]}")
        
        # Parse JSON response
        try:
            transactions_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response text: {response_text}")
            raise Exception(f"Failed to parse Gemini response as JSON: {str(e)}")
        
        if not isinstance(transactions_data, list):
            raise Exception(f"Expected list of transactions, got {type(transactions_data)}")
        
        # Validate and normalize transactions
        normalized_transactions = []
        for i, txn in enumerate(transactions_data):
            try:
                # Validate required fields
                if 'date' not in txn or 'description' not in txn or 'amount' not in txn or 'direction' not in txn:
                    print(f"Warning: Transaction {i+1} missing required fields: {txn}")
                    continue
                
                # Parse date
                try:
                    date_obj = datetime.strptime(txn['date'], '%Y-%m-%d').date()
                except ValueError:
                    # Try other formats
                    try:
                        date_obj = datetime.strptime(txn['date'], '%d-%m-%Y').date()
                    except:
                        print(f"Warning: Could not parse date '{txn['date']}' in transaction {i+1}")
                        continue
                
                # Validate amount
                try:
                    amount = Decimal(str(txn['amount']))
                    if amount <= 0:
                        print(f"Warning: Invalid amount {amount} in transaction {i+1}")
                        continue
                except (ValueError, TypeError):
                    print(f"Warning: Could not parse amount '{txn['amount']}' in transaction {i+1}")
                    continue
                
                # Validate direction
                direction_str = str(txn['direction']).lower()
                if direction_str not in ['credit', 'debit']:
                    print(f"Warning: Invalid direction '{txn['direction']}' in transaction {i+1}, defaulting to debit")
                    direction = TransactionDirection.DEBIT
                else:
                    direction = TransactionDirection.CREDIT if direction_str == 'credit' else TransactionDirection.DEBIT
                
                # Parse balance if available
                balance_after = None
                if 'balance_after' in txn and txn['balance_after'] is not None:
                    try:
                        balance_after = Decimal(str(txn['balance_after']))
                    except (ValueError, TypeError):
                        pass
                
                normalized_transactions.append({
                    'date': date_obj,
                    'description': str(txn['description']).strip(),
                    'amount': amount,
                    'direction': direction,
                    'balance_after': balance_after,
                    'raw_row_data': json.dumps(txn)  # Store original for debugging
                })
                
            except Exception as e:
                print(f"Error processing transaction {i+1}: {e}")
                print(f"Transaction data: {txn}")
                continue
        
        print(f"Successfully extracted {len(normalized_transactions)} transactions from {len(transactions_data)} found")
        return normalized_transactions
        
    except Exception as e:
        error_msg = f"Error parsing PDF with Gemini: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)




