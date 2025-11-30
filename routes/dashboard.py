from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import db, Transaction, Account, UploadedFile
from sqlalchemy import func, case
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def index():
    # Get summary statistics
    from models import TransactionDirection
    
    total_credits = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.direction == TransactionDirection.CREDIT
    ).scalar() or 0
    
    total_debits = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.direction == TransactionDirection.DEBIT
    ).scalar() or 0
    
    net = float(total_credits) - float(total_debits)
    
    # Transaction count
    total_transactions = Transaction.query.filter_by(user_id=current_user.id).count()
    
    # Account counts
    total_accounts = Account.query.filter_by(user_id=current_user.id).count()
    total_statements = UploadedFile.query.filter_by(user_id=current_user.id).count()
    
    # Monthly data for chart (last 12 months)
    monthly_data = []
    for i in range(11, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_credits = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.direction == TransactionDirection.CREDIT,
            Transaction.date >= month_start.date(),
            Transaction.date <= month_end.date()
        ).scalar() or 0
        
        month_debits = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.direction == TransactionDirection.DEBIT,
            Transaction.date >= month_start.date(),
            Transaction.date <= month_end.date()
        ).scalar() or 0
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'credits': float(month_credits),
            'debits': float(month_debits),
            'net': float(month_credits) - float(month_debits)
        })
    
    # Latest transactions
    latest_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).limit(10).all()
    
    return render_template('dashboard/index.html',
                         total_credits=total_credits,
                         total_debits=total_debits,
                         net=net,
                         total_transactions=total_transactions,
                         total_accounts=total_accounts,
                         total_statements=total_statements,
                         monthly_data=monthly_data,
                         latest_transactions=latest_transactions)

