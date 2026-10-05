# =============================================================
# PythonAnywhere 用 WSGI 設定ファイル
#
# 使い方:
#   PythonAnywhere の Web タブ → WSGI configuration file を
#   このファイルの内容に置き換えるか、パスを指定してください。
#
#   USERNAME と PROJECT_DIR を自分の環境に合わせて変更してください。
# =============================================================

import sys
import os

# ── プロジェクトのルートパスを追加 ──
# 例: /home/yourusername/kakeibo
PROJECT_DIR = '/home/USERNAME/kakeibo'

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# ── 環境変数の設定 ──
os.environ['FLASK_CONFIG'] = 'production'
os.environ['SECRET_KEY'] = 'your-production-secret-key-change-this'

# ── アプリケーションの生成 ──
from app import create_app, db  # noqa: E402

application = create_app('production')

# ── DB の初期化（初回のみ実行される）──
with application.app_context():
    db.create_all()
