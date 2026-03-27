# perigee - 1on1管理システム

1on1を管理するシステム。誰でもオーガナイザー（1on1の設定者）にもカウンターパート（1on1の相手方）にもなれる、固定ロールを持たない設計。

## セットアップ

### 前提条件

- Docker / Docker Compose

### 起動

```bash
cp .env.example .env   # 必要に応じて値を編集
docker compose up -d
```

- フロントエンド: http://localhost:5173
- バックエンド API: http://localhost:8000
- API ドキュメント（Swagger UI）: http://localhost:8000/docs

### データベースマイグレーション

```bash
docker compose exec backend uv run alembic upgrade head
```

その他のコマンド:

```bash
# 現在のリビジョン確認
docker compose exec backend uv run alembic current

# 新規マイグレーション作成
docker compose exec backend uv run alembic revision -m "create_xxx_table"

# 1つ戻す
docker compose exec backend uv run alembic downgrade -1
```

## 環境変数

`.env.example` を `.env` にコピーして使用する。すべての変数に `PERIGEE_` プレフィックスが付く。

### データベース

| 変数 | 説明 | デフォルト |
|---|---|---|
| `PERIGEE_DB_HOST` | MariaDB ホスト | `localhost` |
| `PERIGEE_DB_PORT` | MariaDB ポート | `3306` |
| `PERIGEE_DB_USER` | DB ユーザー | `perigee` |
| `PERIGEE_DB_PASSWORD` | DB パスワード | (空) |
| `PERIGEE_DB_NAME` | DB 名 | `perigee` |

### Web サーバー

| 変数 | 説明 | デフォルト |
|---|---|---|
| `PERIGEE_CORS_ORIGINS` | CORS で許可するオリジン（カンマ区切り） | (空 = CORS 無効) |
| `PERIGEE_TRUSTED_HOSTS` | 許可する Host ヘッダー（カンマ区切り） | (空 = チェックなし) |

- `CORS_ORIGINS` が未設定の場合、フロントエンドからのリクエストはブラウザにブロックされる
- `TRUSTED_HOSTS` は本番環境では必ず設定すること
- Docker Compose 起動時は `docker-compose.yml` に定義されたデフォルト値（`CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`、`TRUSTED_HOSTS=localhost,127.0.0.1`）が使われる

### アプリケーション

| 変数 | 説明 | デフォルト |
|---|---|---|
| `PERIGEE_DEBUG` | デバッグモード | `false` |

### Slack 通知

| 変数 | 説明 | デフォルト |
|---|---|---|
| `PERIGEE_SLACK_WEBHOOK_URL` | Slack Webhook URL | (なし) |
| `PERIGEE_SLACK_ENABLED` | Slack 通知の有効/無効 | `true` |
| `PERIGEE_SLACK_HTTP_TIMEOUT` | HTTP タイムアウト（秒） | `10` |
