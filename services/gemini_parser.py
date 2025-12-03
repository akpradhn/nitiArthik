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
import re
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

CRITICAL FIRST STEP - FIND THE LEGEND/DEFINITION TABLE:
Before extracting any transactions, you MUST:
1. Scan the ENTIRE PDF (all pages) for any legend, footnote, definition table, or explanatory text
2. Look specifically for patterns like:
   - "C=Credit; D=Debit; M=Monthly Installments"
   - "C=Credit ; D=Debit; EN=Encash; FP=Flexipay; EMD=Easy Money Draft; BT=Balance Transfer; M=Monthly Installments; TAD=Total Amount Due; T=Temporary Credit"
   - "C=Credit ; D=Debit; EN=Encash; FP=Flexipay; EMD=Easy Money Draft; BT=Balance Transfer; M=Monthly Installments; TAD=Total Amount Due; T=Temporary Credit" (SBI Card format)
   - Any table or text that explains what codes mean (e.g., "C/Cr=Credit", "D/Dr=Debit")
   - Footnotes or legends that define transaction type abbreviations
   - Look for explanatory text like "Transactions highlighted in grey color" sections that may contain definitions
3. IMPORTANT: Look for instructions about transaction formatting, such as:
   - "Transactions highlighted in grey color, if any, do not form part of Purchases & Other Debits"
   - "#Transactions fully/partially converted to Flexipay/Encash/Merchant EMI"
   - These are important context but still extract these transactions (they are valid transactions, just categorized differently)
4. Document these definitions clearly in your analysis
5. Use these document-specific definitions as the ABSOLUTE PRIMARY source when determining transaction direction
6. If you find such a legend, apply it consistently to ALL transactions in the document

For each transaction, extract:
1. Date (in YYYY-MM-DD format)
2. Description/Narration (full transaction description)
3. Amount (as a positive number)
4. Direction (either "credit" or "debit")
   - FIRST: Check the amount column for codes like "D", "C", "M", "EN", "FP", etc.
   - Use the legend/definition table you found to map these codes:
     * If legend says "C=Credit", then "C" means "credit"
     * If legend says "D=Debit", then "D" means "debit"
     * If legend says "M=Monthly Installments", then "M" means "debit" (money going out)
     * If legend says "EN=Encash", "FP=Flexipay", "BT=Balance Transfer", these are typically "debit"
   - Common patterns (use ONLY if no legend found):
     * C, Cr, Credit = "credit"
     * D, Dr, Debit = "debit"
     * M, EMI, Monthly Installments = "debit"
   - Credit: Money coming in (deposits, refunds, credits, payments received)
   - Debit: Money going out (payments, purchases, withdrawals, EMIs, charges, installments)
   - ALWAYS return the full word "credit" or "debit" in the direction field (never single letters)
   - NOTE: Extract ALL transactions, even if they are highlighted in grey or marked as "not part of Purchases & Other Debits" - these are still valid transactions that should be included
5. Balance After (if available, the balance after this transaction)

Return the transactions as a JSON array. Each transaction should be an object with these fields:\n
- date: string in YYYY-MM-DD format\n
- description: string\n
- amount: number (positive)\n
- direction: \"credit\" or \"debit\" (never use single-letter codes here; always expand to the full word)\n
- balance_after: number or null\n

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

CRITICAL INSTRUCTIONS FOR LEGEND/DEFINITION TABLES:
- ALWAYS search the ENTIRE PDF for legend/definition tables that explain abbreviations
- Look for patterns like:
  * "C=Credit; D=Debit; M=Monthly Installments"
  * "C=Credit ; D=Debit; EN=Encash; FP=Flexipay; EMD=Easy Money Draft; BT=Balance Transfer; M=Monthly Installments; TAD=Total Amount Due; T=Temporary Credit"
  * Any text explaining what codes mean (e.g., "C/Cr=Credit", "D/Dr=Debit")
  * Look in footnotes, legends, or explanatory sections (e.g., "Transactions highlighted in grey color" sections)
- IMPORTANT: Look for and interpret instructions like:
  * "Transactions highlighted in grey color, if any, do not form part of Purchases & Other Debits"
  * "#Transactions fully/partially converted to Flexipay/Encash/Merchant EMI"
  * These are informational notes - STILL EXTRACT these transactions (they are valid transactions, just categorized differently by the bank)
- These legends are the ABSOLUTE PRIMARY source - use them for ALL transactions
- Look for codes in the amount column (e.g., "99.00 D", "5,184.37 M", "1,93,290.00 D")
- Map codes using the legend you found:
  * If legend says "D=Debit", then "D" = Debit (money going out)
  * If legend says "C=Credit", then "C" = Credit (money coming in)  
  * If legend says "M=Monthly Installments", then "M" = Debit (money going out)
  * If legend says "EN=Encash", "FP=Flexipay", "BT=Balance Transfer", these are typically Debit (money going out)
- Always return direction as full words: "credit" or "debit" (never single letters like "C", "D", "M")
- Extract ALL transactions regardless of highlighting or special notes - they are all valid financial transactions

CRITICAL: You MUST return ONLY a valid JSON array. Do not include any explanatory text, comments, or markdown formatting.
The response must start with "[" and end with "]". No other text before or after the JSON array.

Extract ALL transactions from the document. Return ONLY the JSON array, no other text."""

        # Upload PDF to Gemini
        print("Uploading PDF to Gemini...")
        pdf_part = {
            "mime_type": "application/pdf",
            "data": pdf_data
        }
        
        # Generate response with JSON mode if available
        print("Sending request to Gemini...")
        try:
            # Try with JSON response mode (Gemini 1.5 Pro supports this)
            response = model.generate_content(
                [prompt, pdf_part],
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
        except (AttributeError, TypeError, Exception) as e:
            # Fallback for older API versions or if JSON mode not supported
            print(f"JSON mode not available or error occurred, using standard mode: {e}")
            try:
                response = model.generate_content([prompt, pdf_part])
            except Exception as e2:
                raise Exception(f"Failed to call Gemini API: {str(e2)}")
        
        # Check if response is valid
        if not response:
            raise Exception("Gemini returned None response")
        
        if not hasattr(response, 'text') or not response.text:
            # Check for blocked content or other issues
            if hasattr(response, 'prompt_feedback'):
                print(f"Prompt feedback: {response.prompt_feedback}")
            raise Exception("Gemini returned an empty response. The content may have been blocked or filtered.")
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Check if response is empty after stripping
        if not response_text:
            raise Exception("Gemini returned an empty response after processing")
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        print(f"Gemini response received ({len(response_text)} chars)")
        print(f"First 500 chars: {response_text[:500]}")
        
        # Try to find JSON array in the response if it's not pure JSON
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        
        if json_start != -1 and json_end > json_start:
            # Extract just the JSON array part
            response_text = response_text[json_start:json_end]
            print(f"Extracted JSON array from response (chars {json_start} to {json_end})")
        
        # Parse JSON response
        try:
            transactions_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Full response text (first 1000 chars): {response_text[:1000]}")
            if len(response_text) > 1000:
                print(f"Full response text (last 500 chars): {response_text[-500:]}")
            
            # Try to extract JSON more aggressively using regex
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                try:
                    extracted_json = json_match.group(0)
                    transactions_data = json.loads(extracted_json)
                    print("Successfully extracted JSON using regex fallback")
                except json.JSONDecodeError as e2:
                    print(f"Regex extraction also failed: {e2}")
                    raise Exception(f"Failed to parse Gemini response as JSON. Response preview: {response_text[:200]}")
            else:
                raise Exception(f"Failed to parse Gemini response as JSON. No JSON array found. Response preview: {response_text[:200]}")
        
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
                
                # Validate direction (handle various abbreviations / legends)
                direction_str = str(txn['direction']).strip().lower()

                # Many Indian statements use single-letter codes in the legend:
                # C = Credit, D = Debit, M = Monthly installment (treated as debit)
                if direction_str in ['c', 'cr', 'credit']:
                    direction = TransactionDirection.CREDIT
                elif direction_str in ['d', 'dr', 'debit', 'm', 'emi', 'installment']:
                    direction = TransactionDirection.DEBIT
                else:
                    # Fallback: expect "credit" or "debit", default to debit if unknown
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






