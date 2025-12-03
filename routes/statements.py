from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, UploadedFile, Transaction
import os

statements_bp = Blueprint('statements', __name__)

@statements_bp.route('/statements')
@login_required
def index():
    statements = UploadedFile.query.filter_by(
        user_id=current_user.id
    ).order_by(UploadedFile.uploaded_at.desc()).all()
    
    # Get transaction counts for each statement
    statements_with_counts = []
    for statement in statements:
        transaction_count = Transaction.query.filter_by(file_id=statement.id).count()
        statements_with_counts.append({
            'statement': statement,
            'transaction_count': transaction_count
        })
    
    return render_template('statements/index.html', statements_with_counts=statements_with_counts)

@statements_bp.route('/statements/<int:file_id>/transactions')
@login_required
def view_transactions(file_id):
    statement = UploadedFile.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first_or_404()
    
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        file_id=file_id
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    
    return render_template('statements/transactions.html',
                         statement=statement,
                         transactions=transactions)


@statements_bp.route('/statements/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_statement(file_id):
    """Delete an uploaded statement and all its transactions for the current user."""
    statement = UploadedFile.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first_or_404()

    # Delete associated transactions first
    Transaction.query.filter_by(
        user_id=current_user.id,
        file_id=file_id
    ).delete()

    # Delete PDF file from disk if it exists
    if statement.stored_file_path and os.path.exists(statement.stored_file_path):
        try:
            os.remove(statement.stored_file_path)
        except OSError:
            # Ignore file system errors, we still delete DB record
            pass

    db.session.delete(statement)
    db.session.commit()

    flash('Statement and its transactions deleted successfully.', 'success')

    # Redirect back to statements list or referrer
    return redirect(request.referrer or url_for('statements.index'))







