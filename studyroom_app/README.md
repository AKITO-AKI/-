# StudyRoom App (v0.2.0)
自主室向け：**1台で運用できる**「入退室打刻 + 上位ランキング」＋「個人ダッシュボード（推移・順位推移）」。

## 画面
- `/` ホーム：入室/退室 + 上位ランキング（入口端末とランキングを統合）
- `/login` 個人ログイン
- `/dashboard` 個人：累計/期間内/推移/順位推移
- `/admin` 管理：ユーザー追加 / PIN再発行 / 強制退室

## 起動（1コマンド推奨）
1) Python 3.10+ を入れる  
2) このフォルダで仮想環境
```bash
python -m venv .venv
.venv\Scripts\activate
```

3) 依存を入れる
```bash
pip install -r backend/requirements.txt
```

4) 管理パスワードを設定（必須）
```bash
set STUDYROOM_ADMIN_PASSWORD=your_admin_password
set STUDYROOM_SECRET_KEY=some_long_random_string
```

5) 起動
```bash
uvicorn backend.main:app --reload --port 8000
```

6) アクセス
- Home: http://localhost:8000/
- 個人: http://localhost:8000/login
- 管理: http://localhost:8000/admin

## 仕様メモ（運用で強いポイント）
- **日付またぎ**のセッション（23:50入室→翌0:20退室）でも、ランキング集計が破綻しないように **時間の重なり（overlap）で集計**しています。
- ランキングは本名禁止推奨。ニックネーム表示が前提です。

## DB
デフォルトは `backend/studyroom.sqlite3` に保存。`STUDYROOM_DB_PATH` で変更可能。

## 1コマンド起動（推奨・CodespacesでもOK）
この方式なら **venvの有効化不要**・パスの違いで詰まりません。

```bash
python run.py
```

- 初回起動で `.venv` を作成し、依存関係を自動インストールします。
- `.env` が無い場合は自動生成します（管理パスワードは必ず変更）。

### 管理パスワードの変更
起動後でもOKなので、`./.env` を編集して

```
STUDYROOM_ADMIN_PASSWORD=強いパスワード
```

にしてください。

## よくあるエラー（今回の原因）
- `bash: .venvScriptsactivate: command not found`
  - Bash(Linux)でWindows用コマンドを打ったのが原因。`run.py`方式なら発生しません。
- `backend/requirements.txt が無い`
  - `cd studyroom_app` など、プロジェクト直下で実行できていない可能性。
