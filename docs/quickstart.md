# Quickstart

## 前提条件

- Docker / Docker Compose
- Git

## 1. リポジトリをクローン

```bash
git clone https://github.com/yo-itani/perigee.git
cd perigee
```

## 2. 環境変数を設定

```bash
cp .env.example .env
```

デフォルト値でローカル開発環境が動作します。必要に応じて `.env` を編集してください。

| 変数 | 説明 | デフォルト |
|---|---|---|
| `PERIGEE_DB_HOST` | MariaDB ホスト | `mariadb` |
| `PERIGEE_DB_PORT` | MariaDB ポート | `3306` |
| `PERIGEE_DB_USER` | DB ユーザー | `perigee` |
| `PERIGEE_DB_PASSWORD` | DB パスワード | `perigee` |
| `PERIGEE_DB_NAME` | DB 名 | `perigee` |
| `PERIGEE_DB_ROOT_PASSWORD` | MariaDB root パスワード | `rootpassword` |
| `PERIGEE_SLACK_WEBHOOK_URL` | Slack Webhook URL（空欄でログのみ） | _(空)_ |
| `PERIGEE_SLACK_ENABLED` | Slack 通知の有効/無効 | `true` |
| `PERIGEE_SLACK_HTTP_TIMEOUT` | Slack HTTP タイムアウト（秒） | `10` |

## 3. 起動

```bash
docker compose up -d
```

3つのサービスが起動します:

| サービス | URL | 説明 |
|---|---|---|
| frontend | http://localhost:5173 | React アプリ |
| backend | http://localhost:8000 | FastAPI アプリ |
| backend (Swagger UI) | http://localhost:8000/docs | API ドキュメント |
| mariadb | localhost:3306 | データベース |

DB マイグレーションはバックエンド起動時に自動適用されます。

## 4. 認証（開発モード）

現在は開発用の簡易認証です。リクエストヘッダー `X-User-Id` に UUID を渡すことでユーザーを識別します。

フロントエンドは `00000000-0000-0000-0000-000000000001`（Dev User）として固定で動作します。

### API を直接呼ぶ場合

```bash
curl -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
     http://localhost:8000/schedules/upcoming
```

## 5. 初期データの投入

起動直後はユーザーデータがありません。1on1 を試すには最低2人のユーザーが必要です。

```bash
# MariaDB に接続
docker compose exec mariadb mysql -u perigee -pperigee perigee

# ユーザーを追加
INSERT INTO users (id) VALUES ('00000000-0000-0000-0000-000000000001');
INSERT INTO users (id) VALUES ('00000000-0000-0000-0000-000000000002');
```

## 6. 停止

```bash
docker compose down
```

データを含めて完全にリセットする場合:

```bash
docker compose down -v
```

## テストの実行

### バックエンド

```bash
# ユニットテスト（DB不要）
cd backend
uv run pytest -m "not integration"

# インテグレーションテスト（テスト用MariaDBコンテナが必要）
docker compose up -d mariadb
uv run pytest
```

### フロントエンド

```bash
cd frontend
pnpm test
```

## トラブルシューティング

### バックエンドのビルドが失敗する（asyncmy）

`python:3.13-slim` に C コンパイラが必要です。Dockerfile に `gcc` と `libmariadb-dev` が含まれていることを確認してください。

### フロントエンドが `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY` で停止する

Dockerfile に `ENV CI=true` が設定されていることを確認してください。
