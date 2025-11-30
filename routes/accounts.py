from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import db, Account, Transaction, UploadedFile, TransactionDirection
from sqlalchemy import func

accounts_bp = Blueprint('accounts', __name__)

@accounts_bp.route('/accounts')
@login_required
def index():
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.created_at.desc()).all()
    
    # Get stats for each account
    accounts_with_stats = []
    for account in accounts:
        statement_count = UploadedFile.query.filter_by(account_id=account.id).count()
        transaction_count = Transaction.query.filter_by(account_id=account.id).count()
        
        accounts_with_stats.append({
            'account': account,
            'statement_count': statement_count,
            'transaction_count': transaction_count
        })
    
    return render_template('accounts/index.html', accounts_with_stats=accounts_with_stats)

@accounts_bp.route('/accounts/<int:account_id>')
@login_required
def view(account_id):
    account = Account.query.filter_by(
        id=account_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Get transactions for this account
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    query = Transaction.query.filter_by(
        user_id=current_user.id,
        account_id=account_id
    ).order_by(Transaction.date.desc(), Transaction.id.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items
    
    # Get summary
    total_credits = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.account_id == account_id,
        Transaction.direction == TransactionDirection.CREDIT
    ).scalar() or 0
    
    total_debits = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.account_id == account_id,
        Transaction.direction == TransactionDirection.DEBIT
    ).scalar() or 0
    
    return render_template('accounts/view.html',
                         account=account,
                         transactions=transactions,
                         pagination=pagination,
                         total_credits=float(total_credits),
                         total_debits=float(total_debits),
                         net=float(total_credits) - float(total_debits))

