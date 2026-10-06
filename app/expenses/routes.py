from datetime import date, datetime
from calendar import monthrange
from collections import defaultdict
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import extract, func
from app import db
from app.expenses import expenses
from app.models import Transaction, Category


# ─────────────────────────────────────────────
# ホーム／ダッシュボード
# ─────────────────────────────────────────────
@expenses.route('/')
@login_required
def index():
    today = date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))

    # 月の開始・終了日
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # 今月の取引
    transactions = (Transaction.query
                    .filter_by(user_id=current_user.id)
                    .filter(Transaction.date >= first_day,
                            Transaction.date <= last_day)
                    .order_by(Transaction.date.desc())
                    .all())

    # 集計
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')
    balance = total_income - total_expense

    # カテゴリ別支出（グラフ用）
    category_data = (db.session.query(Category.name, func.sum(Transaction.amount))
                     .join(Transaction, Transaction.category_id == Category.id)
                     .filter(Transaction.user_id == current_user.id,
                             Transaction.type == 'expense',
                             Transaction.date >= first_day,
                             Transaction.date <= last_day)
                     .group_by(Category.name)
                     .all())

    # 月別推移（過去6か月・グラフ用）
    monthly_data = []
    for i in range(5, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        fd = date(y, m, 1)
        ld = date(y, m, monthrange(y, m)[1])
        inc = (db.session.query(func.sum(Transaction.amount))
               .filter_by(user_id=current_user.id)
               .filter(Transaction.type == 'income',
                       Transaction.date >= fd, Transaction.date <= ld)
               .scalar() or 0)
        exp = (db.session.query(func.sum(Transaction.amount))
               .filter_by(user_id=current_user.id)
               .filter(Transaction.type == 'expense',
                       Transaction.date >= fd, Transaction.date <= ld)
               .scalar() or 0)
        monthly_data.append({'label': f'{y}/{m:02d}', 'income': inc, 'expense': exp})

    # 日別グラフ用データ（当月の全日分、取引がない日は0）
    daily_chart_data = []
    for day in range(1, monthrange(year, month)[1] + 1):
        d = date(year, month, day)
        day_transactions = [t for t in transactions if t.date == d]
        daily_chart_data.append({
            'label': f'{day}',
            'income': sum(t.amount for t in day_transactions if t.type == 'income'),
            'expense': sum(t.amount for t in day_transactions if t.type == 'expense'),
        })

    # カテゴリ別収入（グラフ用）
    income_category_data = (db.session.query(Category.name, func.sum(Transaction.amount))
                            .join(Transaction, Transaction.category_id == Category.id)
                            .filter(Transaction.user_id == current_user.id,
                                    Transaction.type == 'income',
                                    Transaction.date >= first_day,
                                    Transaction.date <= last_day)
                            .group_by(Category.name)
                            .all())

    # 日付ごとにグループ化
    # daily_groups: [{ date, transactions, income, expense, balance }, ...]  新しい日順
    groups = defaultdict(list)
    for t in transactions:
        groups[t.date].append(t)

    daily_groups = []
    for d in sorted(groups.keys(), reverse=True):
        day_transactions = groups[d]
        day_income = sum(t.amount for t in day_transactions if t.type == 'income')
        day_expense = sum(t.amount for t in day_transactions if t.type == 'expense')
        daily_groups.append({
            'date': d,
            'transactions': day_transactions,
            'income': day_income,
            'expense': day_expense,
            'balance': day_income - day_expense,
        })

    # 前後月ナビ用
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template('expenses/index.html',
                           transactions=transactions,
                           daily_groups=daily_groups,
                           total_income=total_income,
                           total_expense=total_expense,
                           balance=balance,
                           category_data=category_data,
                           income_category_data=income_category_data,
                           daily_chart_data=daily_chart_data,
                           monthly_data=monthly_data,
                           year=year, month=month,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month)


# ─────────────────────────────────────────────
# 取引の追加
# ─────────────────────────────────────────────
@expenses.route('/transaction/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    income_categories = (Category.query
                         .filter_by(user_id=current_user.id, type='income')
                         .order_by(Category.name).all())
    expense_categories = (Category.query
                          .filter_by(user_id=current_user.id, type='expense')
                          .order_by(Category.name).all())

    if request.method == 'POST':
        t_type = request.form.get('type')
        amount_str = request.form.get('amount', '').strip()
        category_id = request.form.get('category_id')
        date_str = request.form.get('date', '').strip()
        memo = request.form.get('memo', '').strip()

        error = None
        if t_type not in ('income', 'expense'):
            error = '種別が不正です。'
        elif not amount_str or not amount_str.isdigit() or int(amount_str) <= 0:
            error = '金額は1以上の整数で入力してください。'
        elif not category_id:
            error = 'カテゴリを選択してください。'
        elif not date_str:
            error = '日付を入力してください。'

        if not error:
            try:
                t_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                error = '日付の形式が正しくありません。'

        if not error:
            cat = Category.query.filter_by(id=category_id,
                                           user_id=current_user.id).first()
            if cat is None:
                error = '無効なカテゴリです。'

        if error:
            flash(error, 'danger')
        else:
            transaction = Transaction(
                date=t_date,
                type=t_type,
                amount=int(amount_str),
                category_id=int(category_id),
                memo=memo,
                user_id=current_user.id,
            )
            db.session.add(transaction)
            db.session.commit()
            flash('記録しました。', 'success')
            return redirect(url_for('expenses.index',
                                    year=t_date.year, month=t_date.month))

    today_str = date.today().strftime('%Y-%m-%d')
    return render_template('expenses/form.html',
                           income_categories=income_categories,
                           expense_categories=expense_categories,
                           today=today_str,
                           action='add',
                           transaction=None)


# ─────────────────────────────────────────────
# 取引の編集
# ─────────────────────────────────────────────
@expenses.route('/transaction/edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id, user_id=current_user.id).first_or_404()

    income_categories = (Category.query
                         .filter_by(user_id=current_user.id, type='income')
                         .order_by(Category.name).all())
    expense_categories = (Category.query
                          .filter_by(user_id=current_user.id, type='expense')
                          .order_by(Category.name).all())

    if request.method == 'POST':
        t_type = request.form.get('type')
        amount_str = request.form.get('amount', '').strip()
        category_id = request.form.get('category_id')
        date_str = request.form.get('date', '').strip()
        memo = request.form.get('memo', '').strip()

        error = None
        if t_type not in ('income', 'expense'):
            error = '種別が不正です。'
        elif not amount_str or not amount_str.isdigit() or int(amount_str) <= 0:
            error = '金額は1以上の整数で入力してください。'
        elif not category_id:
            error = 'カテゴリを選択してください。'
        elif not date_str:
            error = '日付を入力してください。'

        if not error:
            try:
                t_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                error = '日付の形式が正しくありません。'

        if not error:
            cat = Category.query.filter_by(id=category_id,
                                           user_id=current_user.id).first()
            if cat is None:
                error = '無効なカテゴリです。'

        if error:
            flash(error, 'danger')
        else:
            transaction.date = t_date
            transaction.type = t_type
            transaction.amount = int(amount_str)
            transaction.category_id = int(category_id)
            transaction.memo = memo
            db.session.commit()
            flash('更新しました。', 'success')
            return redirect(url_for('expenses.index',
                                    year=t_date.year, month=t_date.month))

    return render_template('expenses/form.html',
                           income_categories=income_categories,
                           expense_categories=expense_categories,
                           today=transaction.date.strftime('%Y-%m-%d'),
                           action='edit',
                           transaction=transaction)


# ─────────────────────────────────────────────
# 取引の削除
# ─────────────────────────────────────────────
@expenses.route('/transaction/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id, user_id=current_user.id).first_or_404()
    year = transaction.date.year
    month = transaction.date.month
    db.session.delete(transaction)
    db.session.commit()
    flash('削除しました。', 'info')
    return redirect(url_for('expenses.index', year=year, month=month))


# ─────────────────────────────────────────────
# カテゴリ管理
# ─────────────────────────────────────────────
@expenses.route('/categories')
@login_required
def categories():
    income_cats = (Category.query
                   .filter_by(user_id=current_user.id, type='income')
                   .order_by(Category.name).all())
    expense_cats = (Category.query
                    .filter_by(user_id=current_user.id, type='expense')
                    .order_by(Category.name).all())
    return render_template('expenses/categories.html',
                           income_cats=income_cats,
                           expense_cats=expense_cats)


@expenses.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name', '').strip()
    cat_type = request.form.get('type')

    if not name:
        flash('カテゴリ名を入力してください。', 'danger')
    elif cat_type not in ('income', 'expense'):
        flash('種別が不正です。', 'danger')
    elif Category.query.filter_by(user_id=current_user.id,
                                  name=name, type=cat_type).first():
        flash('同じカテゴリがすでに存在します。', 'warning')
    else:
        db.session.add(Category(name=name, type=cat_type, user_id=current_user.id))
        db.session.commit()
        flash(f'カテゴリ「{name}」を追加しました。', 'success')

    return redirect(url_for('expenses.categories'))


@expenses.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    cat = Category.query.filter_by(id=category_id,
                                   user_id=current_user.id).first_or_404()
    if cat.transactions.count() > 0:
        flash('このカテゴリには取引が紐付いているため削除できません。', 'danger')
    else:
        db.session.delete(cat)
        db.session.commit()
        flash(f'カテゴリ「{cat.name}」を削除しました。', 'info')
    return redirect(url_for('expenses.categories'))
