import os
from app import create_app, db
from app.models import User, Category, Transaction

app = create_app(os.environ.get('FLASK_CONFIG') or 'default')


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Category=Category, Transaction=Transaction)


@app.cli.command('init-db')
def init_db():
    """データベースを初期化してデフォルトカテゴリを作成する"""
    db.create_all()
    print('データベースを初期化しました。')


if __name__ == '__main__':
    app.run()
