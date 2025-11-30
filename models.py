from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Enum as SQLEnum
import enum
import json

db = SQLAlchemy()

class AccountType(enum.Enum):
    BANK = "BANK"
    CREDIT_CARD = "CREDIT_CARD"

class ParseStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class TransactionDirection(enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    accounts = db.relationship('Account', backref='user', lazy=True, cascade='all, delete-orphan')
    uploaded_files = db.relationship('UploadedFile', backref='user', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        # Use pbkdf2:sha256 instead of scrypt for better compatibility
        # scrypt requires hashlib.scrypt which may not be available in all Python versions
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_type = db.Column(SQLEnum(AccountType), nullable=False)
    nickname = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    uploaded_files = db.relationship('UploadedFile', backref='account', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='account', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Account {self.nickname} ({self.account_type.value})>'

class UploadedFile(db.Model):
    __tablename__ = 'uploaded_files'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    original_file_name = db.Column(db.String(255), nullable=False)
    stored_file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    parse_status = db.Column(SQLEnum(ParseStatus), default=ParseStatus.PENDING, nullable=False)
    parse_error = db.Column(db.Text, nullable=True)
    statement_start_date = db.Column(db.Date, nullable=True)
    statement_end_date = db.Column(db.Date, nullable=True)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='uploaded_file', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UploadedFile {self.original_file_name}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    direction = db.Column(SQLEnum(TransactionDirection), nullable=False)
    balance_after = db.Column(db.Numeric(15, 2), nullable=True)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    category = db.Column(db.String(100), default='Uncategorized', nullable=False)
    raw_row_data = db.Column(db.Text, nullable=True)  # JSON as text
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': float(self.amount),
            'direction': self.direction.value,
            'balance_after': float(self.balance_after) if self.balance_after else None,
            'currency': self.currency,
            'category': self.category,
            'account_nickname': self.account.nickname if self.account else None,
            'account_type': self.account.account_type.value if self.account else None,
        }
    
    def __repr__(self):
        return f'<Transaction {self.date} {self.description[:30]} {self.amount}>'


