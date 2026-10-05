# PythonAnywhere デプロイ手順

## 1. PythonAnywhere にアップロード

### 方法 A: Git を使う（推奨）
PythonAnywhere の Bash コンソールで:
```bash
git clone https://github.com/あなたのリポジトリ/kakeibo.git
```

### 方法 B: ZIP でアップロード
- ローカルでプロジェクトを ZIP 圧縮
- PythonAnywhere の Files タブからアップロード
- Bash コンソールで解凍:
  ```bash
  unzip kakeibo.zip -d ~/kakeibo
  ```

---

## 2. 仮想環境の作成とパッケージインストール

```bash
cd ~/kakeibo
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. データベースの初期化

```bash
cd ~/kakeibo
source venv/bin/activate
python -c "from app import create_app, db; app = create_app('production'); app.app_context().push(); db.create_all(); print('DB初期化完了')"
```

---

## 4. Web アプリの設定

1. PythonAnywhere の **Web** タブを開く
2. **Add a new web app** → **Manual configuration** → **Python 3.10**（または最新）
3. **Virtualenv** セクションで仮想環境のパスを設定:
   ```
   /home/USERNAME/kakeibo/venv
   ```
4. **WSGI configuration file** をクリックして編集:
   - `pythonanywhere_wsgi.py` の内容を貼り付け
   - `USERNAME` を自分のユーザー名に変更
   - `SECRET_KEY` を安全なランダム文字列に変更

5. **Static files** セクションで以下を追加:
   | URL          | Directory                              |
   |--------------|----------------------------------------|
   | /static/     | /home/USERNAME/kakeibo/app/static/     |

6. **Reload** ボタンをクリック

---

## 5. SECRET_KEY の生成方法

Python で安全なキーを生成:
```python
import secrets
print(secrets.token_hex(32))
```

---

## 6. 動作確認

`https://USERNAME.pythonanywhere.com` にアクセスしてログイン画面が表示されれば完了です。
