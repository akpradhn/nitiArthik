# NitiArthik - Personal Finance Portal

A secure web portal that allows users to upload multiple bank statements and credit card bills in PDF format, automatically extracts all transactions, and provides a unified, filterable "consolidated transactions" view.

## Features

- **User Authentication**: Secure email/password registration and login
- **PDF Upload**: Upload multiple bank statements and credit card bills
- **Automatic Transaction Extraction**: Parses PDFs and extracts transactions automatically
- **Consolidated View**: View all transactions across all accounts in one place
- **Advanced Filtering**: Filter by date range, account, account type, direction, category, and search descriptions
- **Transaction Management**: Edit transaction categories and descriptions
- **Account Management**: Organize statements by accounts (Bank/Credit Card)
- **Dashboard**: Overview with summary statistics and monthly cash flow chart
- **Statement Tracking**: View all uploaded statements and their parsing status

## Tech Stack

- **Backend**: Python 3, Flask
- **Templating**: Jinja2 with HTML/CSS and vanilla JavaScript
- **Database**: SQLite (development) with SQLAlchemy ORM (easily switchable to PostgreSQL)
- **PDF Parsing**: pdfplumber for table extraction
- **Authentication**: Flask-Login for session management

## Project Structure

```
nitiArthik/
├── app.py                 # Flask application entry point
├── models.py              # SQLAlchemy database models
├── requirements.txt       # Python dependencies
├── routes/                # Route handlers (blueprints)
│   ├── auth.py           # Authentication routes
│   ├── dashboard.py      # Dashboard routes
│   ├── upload.py         # PDF upload routes
│   ├── transactions.py   # Transaction viewing/editing routes
│   ├── accounts.py       # Account management routes
│   └── statements.py     # Statement listing routes
├── services/             # Business logic
│   └── parser.py         # PDF parsing service
├── templates/            # Jinja2 HTML templates
│   ├── base.html         # Base template with navigation
│   ├── auth/            # Login/register templates
│   ├── dashboard/       # Dashboard template
│   ├── upload/          # Upload form template
│   ├── transactions/    # Transaction view template
│   ├── accounts/        # Account listing templates
│   └── statements/       # Statement listing templates
└── uploads/             # Uploaded PDF files (created automatically)
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Quick Setup (Recommended)

**For Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**For Windows:**
```cmd
setup.bat
```

The setup script will:
- Create a virtual environment
- Install all dependencies
- Create necessary directories
- Set up environment variables

### Manual Setup

If you prefer to set up manually:

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd nitiArthik
   ```

2. **Create a virtual environment**:
   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   
   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```bash
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///nitiarthik.db
   ```
   
   For PostgreSQL (optional):
   ```bash
   DATABASE_URL=postgresql://username:password@localhost:5432/nitiarthik
   ```
   
   For Google Gemini API (recommended for better PDF parsing):
   ```bash
   GOOGLE_GEMINI_API_KEY=your-gemini-api-key-here
   ```
   
   **Getting a Gemini API Key:**
   1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   2. Sign in with your Google account
   3. Click "Create API Key"
   4. Copy the key and add it to your `.env` file
   
   **Note:** The app will automatically use Gemini if the API key is set, otherwise it falls back to pdfplumber.

5. **Create necessary directories**:
   ```bash
   mkdir -p uploads
   ```

6. **Initialize the database**:
   The database will be created automatically when you run the application for the first time.

7. **Run the application**:
   ```bash
   python app.py
   ```

   The application will be available at `http://localhost:5000`

### Activating Virtual Environment

After initial setup, activate the virtual environment before running the app:

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

Then run:
```bash
python app.py
```

## Usage

1. **Register/Login**: Create an account or login with existing credentials
2. **Upload Statements**: 
   - Go to "Upload Statements"
   - Select PDF files
   - Choose account type (Bank/Credit Card)
   - Create a new account or select existing one
   - Optionally set statement period dates
   - Upload and wait for parsing (happens in background)
3. **View Transactions**: 
   - Go to "Consolidated Transactions"
   - Use filters to find specific transactions
   - Edit categories inline
4. **Manage Accounts**: View all accounts and their transaction counts
5. **View Statements**: See all uploaded statements and their parsing status

## PDF Parser

### How It Works

The application supports two parsing methods:

#### 1. Google Gemini AI Parser (Recommended)
The primary parser (`services/gemini_parser.py`) uses Google Gemini AI to:
- Understand PDF structure intelligently
- Extract transactions from various PDF formats
- Handle complex layouts and non-standard formats
- Automatically identify transaction details

**Advantages:**
- Works with any PDF format
- Understands context and structure
- Handles scanned documents better
- More accurate extraction

#### 2. pdfplumber Parser (Fallback)
The fallback parser (`services/parser.py`) uses `pdfplumber` to:
- Extract tables from each page of the PDF
- Identify column headers (Date, Description, Debit, Credit, Amount, Balance)
- Parse transaction rows and extract:
  - Date (supports multiple formats)
  - Description
  - Amount and direction (debit/credit)
  - Balance (if available)
- Normalize and store transactions in the database

**The app automatically uses Gemini if `GOOGLE_GEMINI_API_KEY` is set, otherwise falls back to pdfplumber.**

### Supported Formats

The parser attempts to handle various bank statement formats by:
- Detecting header keywords (case-insensitive)
- Supporting both separate Debit/Credit columns and single Amount columns
- Inferring transaction direction from description keywords or amount signs
- Parsing dates in multiple formats (DD-MM-YYYY, DD/MM/YYYY, etc.)

### Limitations

- The parser works best with tabular data (statements with clear table structures)
- Some bank-specific formats may require customization
- Handwritten or scanned PDFs (without text layer) may not work well
- Complex multi-page statements with varying formats may need manual review

### Extending the Parser

To add support for bank-specific formats:

1. **Add custom parsing logic** in `services/parser.py`:
   - Create a new function for the specific bank format
   - Override column detection if needed
   - Add custom date/amount parsing if required

2. **Modify `extract_transactions_from_pdf`**:
   - Add format detection logic
   - Route to appropriate parser function

3. **Update keyword lists**:
   - Add bank-specific keywords to `DATE_KEYWORDS`, `DESCRIPTION_KEYWORDS`, etc.

## Database Schema

### Tables

- **users**: User accounts (id, name, email, password_hash, created_at)
- **accounts**: Bank/Credit Card accounts (id, user_id, account_type, nickname, created_at)
- **uploaded_files**: Uploaded PDF files (id, user_id, account_id, original_file_name, stored_file_path, uploaded_at, parse_status, parse_error, statement_start_date, statement_end_date)
- **transactions**: Extracted transactions (id, user_id, account_id, file_id, date, description, amount, direction, balance_after, currency, category, raw_row_data)

## Configuration

### Environment Variables

- `SECRET_KEY`: Flask secret key for session security (required in production)
- `DATABASE_URL`: Database connection string (defaults to SQLite)

### Switching to PostgreSQL

1. Install PostgreSQL and create a database
2. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/nitiarthik
   ```
3. Install PostgreSQL adapter:
   ```bash
   pip install psycopg2-binary
   ```
4. Run migrations (database tables will be created automatically on first run)

## Development

### Running in Development Mode

```bash
python app.py
```

The app runs with `debug=True` by default for development.

### Production Deployment

For production:
1. Set `debug=False` in `app.py`
2. Use a production WSGI server (e.g., Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
3. Set a strong `SECRET_KEY` in environment variables
4. Use PostgreSQL instead of SQLite
5. Set up proper file storage (consider cloud storage for uploads)
6. Configure HTTPS

## Troubleshooting

### PDF Parsing Fails

- Check that the PDF has extractable text (not just images)
- Verify the statement has a table structure
- Check the `parse_error` field in the Statements page
- Review `raw_row_data` in transaction records for debugging

### Database Issues

- Ensure write permissions in the project directory (for SQLite)
- Check database connection string format
- Verify database exists (for PostgreSQL)

### Upload Issues

- Check file size (max 16MB by default)
- Ensure `uploads/` directory is writable
- Verify PDF file format

## License

This project is provided as-is for personal use.

## Contributing

Feel free to extend the parser for additional bank formats or improve the UI/UX. The code is structured to be easily extensible.
