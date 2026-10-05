from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.auth import auth
from app.models import User, Category


DEFAULT_EXPENSE_CATEGORIES = ['食費', '交通費', '住居費', '光熱費', '通信費',
                               '医療費', '衣服・美容', '娯楽・趣味', '教育費', 'その他']
DEFAULT_INCOME_CATEGORIES = ['給与', 'ボーナス', '副収入', 'その他']


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('expenses.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        error = None
        if not username:
            error = 'ユーザー名を入力してください。'
        elif not email:
            error = 'メールアドレスを入力してください。'
        elif not password:
            error = 'パスワードを入力してください。'
        elif password != password2:
            error = 'パスワードが一致しません。'
        elif User.query.filter_by(username=username).first():
            error = 'このユーザー名はすでに使用されています。'
        elif User.query.filter_by(email=email).first():
            error = 'このメールアドレスはすでに登録されています。'

        if error:
            flash(error, 'danger')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # user.id を取得するためにflush

            # デフォルトカテゴリを作成
            for name in DEFAULT_EXPENSE_CATEGORIES:
                db.session.add(Category(name=name, type='expense', user_id=user.id))
            for name in DEFAULT_INCOME_CATEGORIES:
                db.session.add(Category(name=name, type='income', user_id=user.id))

            db.session.commit()
            flash('登録が完了しました。ログインしてください。', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('expenses.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('ユーザー名またはパスワードが正しくありません。', 'danger')
        else:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('expenses.index'))

    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('auth.login'))
