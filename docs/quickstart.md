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

## 4. 認証

Cookie + JWT 認証方式を使用しています。

### 初期セットアップ

初回起動時にブラウザで http://localhost:5173 にアクセスすると、セットアップ画面が表示されます。管理者ユーザー（名前・メールアドレス・パスワード）を登録してください。

### ログイン

セットアップ完了後、ログイン画面でメールアドレスとパスワードを入力します。

- アクセストークン（JWT）はメモリ内のみで管理（localStorage には保存しない）
- リフレッシュトークンは HttpOnly Cookie として自動管理
- ページリロード時は Cookie 内のリフレッシュトークンでアクセストークンを再取得

### API を直接呼ぶ場合

```bash
# ログイン（アクセストークン取得 + リフレッシュトークン Cookie 設定）
curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "your-password"}'

# 認証付きリクエスト
curl -H "Authorization: Bearer <access_token>" \
     http://localhost:8000/users/me

# トークンリフレッシュ
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/auth/refresh
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

### E2E テスト（Playwright）

E2E テストは Docker Compose の `e2e` プロファイルで専用のバックエンド・DB・フロントエンドを起動し、Playwright で実行します。

```bash
# 1. E2E 用コンテナを起動
docker compose --profile e2e up -d

# 2. Playwright テストを実行
pnpm exec playwright test

# 3. テスト終了後にコンテナを停止
docker compose --profile e2e down
```

E2E 環境のポートマッピング:

| サービス | URL | 説明 |
|---|---|---|
| frontend-e2e | http://localhost:5174 | E2E 用フロントエンド |
| backend-e2e | http://localhost:8001 | E2E 用バックエンド |
| mariadb-e2e | localhost:3307 | E2E 用データベース |

環境変数で接続先を変更できます:

| 変数 | デフォルト | 説明 |
|---|---|---|
| `E2E_BASE_URL` | `http://localhost:5174` | Playwright がアクセスするフロントエンド URL |
| `E2E_API_BASE_URL` | `http://localhost:8001` | テストヘルパーがアクセスするバックエンド URL |

## トラブルシューティング

### バックエンドのビルドが失敗する（asyncmy）

`python:3.13-slim` に C コンパイラが必要です。Dockerfile に `gcc` と `libmariadb-dev` が含まれていることを確認してください。

### フロントエンドが `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY` で停止する

Dockerfile に `ENV CI=true` が設定されていることを確認してください。
