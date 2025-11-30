from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Transaction, Account, TransactionDirection, AccountType
from sqlalchemy import or_, and_, func
from datetime import datetime

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/transactions')
@login_required
def index():
    # Get filter parameters
    account_ids = request.args.getlist('account_id', type=int)
    account_type = request.args.get('account_type', '')
    direction = request.args.get('direction', '')
    category = request.args.get('category', '')
    search = request.args.get('search', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Build query
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if account_ids:
        query = query.filter(Transaction.account_id.in_(account_ids))
    
    if account_type:
        try:
            account_type_enum = AccountType[account_type]
            query = query.join(Account).filter(Account.account_type == account_type_enum)
        except KeyError:
            pass
    
    if direction:
        if direction == 'credit':
            query = query.filter(Transaction.direction == TransactionDirection.CREDIT)
        elif direction == 'debit':
            query = query.filter(Transaction.direction == TransactionDirection.DEBIT)
    
    if category:
        query = query.filter(Transaction.category == category)
    
    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Transaction.date >= date_from_obj)
        except:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Transaction.date <= date_to_obj)
        except:
            pass
    
    # Get summary for current filter
    total_credits = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.direction == TransactionDirection.CREDIT
    )
    total_debits = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.direction == TransactionDirection.DEBIT
    )
    
    # Apply same filters to summary
    if account_ids:
        total_credits = total_credits.filter(Transaction.account_id.in_(account_ids))
        total_debits = total_debits.filter(Transaction.account_id.in_(account_ids))
    if account_type:
        try:
            account_type_enum = AccountType[account_type]
            total_credits = total_credits.join(Account).filter(Account.account_type == account_type_enum)
            total_debits = total_debits.join(Account).filter(Account.account_type == account_type_enum)
        except KeyError:
            pass
    if direction:
        if direction == 'credit':
            total_debits = total_debits.filter(False)  # No debits
        elif direction == 'debit':
            total_credits = total_credits.filter(False)  # No credits
    if category:
        total_credits = total_credits.filter(Transaction.category == category)
        total_debits = total_debits.filter(Transaction.category == category)
    if search:
        total_credits = total_credits.filter(Transaction.description.ilike(f'%{search}%'))
        total_debits = total_debits.filter(Transaction.description.ilike(f'%{search}%'))
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            total_credits = total_credits.filter(Transaction.date >= date_from_obj)
            total_debits = total_debits.filter(Transaction.date >= date_from_obj)
        except:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            total_credits = total_credits.filter(Transaction.date <= date_to_obj)
            total_debits = total_debits.filter(Transaction.date <= date_to_obj)
        except:
            pass
    
    credits_sum = float(total_credits.scalar() or 0)
    debits_sum = float(total_debits.scalar() or 0)
    net = credits_sum - debits_sum
    
    # Order and paginate
    query = query.order_by(Transaction.date.desc(), Transaction.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items
    
    # Get filter options
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.nickname).all()
    categories = db.session.query(Transaction.category).filter_by(
        user_id=current_user.id
    ).distinct().order_by(Transaction.category).all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('transactions/index.html',
                         transactions=transactions,
                         pagination=pagination,
                         accounts=accounts,
                         categories=categories,
                         filters={
                             'account_ids': account_ids,
                             'account_type': account_type,
                             'direction': direction,
                             'category': category,
                             'search': search,
                             'date_from': date_from,
                             'date_to': date_to
                         },
                         summary={
                             'credits': credits_sum,
                             'debits': debits_sum,
                             'net': net,
                             'count': pagination.total
                         })

@transactions_bp.route('/transactions/<int:transaction_id>/edit', methods=['POST'])
@login_required
def edit(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first_or_404()
    
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    
    if category:
        transaction.category = category
    if description:
        transaction.description = description
    
    db.session.commit()
    flash('Transaction updated successfully.', 'success')
    
    return redirect(request.referrer or url_for('transactions.index'))

