# perigee - 1on1管理システム

1on1を管理するシステム。誰でもオーガナイザー（1on1の設定者）にもカウンターパート（1on1の相手方）にもなれる、固定ロールを持たない設計。スケジューリング・記録・共有・フォローアップまでの一連の流れをサポートし、Slack通知によるコミュニケーション連携を含む。

## 技術スタック

| レイヤー | 候補 |
|---|---|
| フロントエンド | React + TypeScript |
| バックエンド | FastAPI（Python） |
| データベース | MariaDB（TDE による暗号化有効） |
| 通知 | Slack API（Incoming Webhooks or Bot） |
| インフラ | Docker Compose |

### 開発ツール

| 用途 | ツール |
|---|---|
| Python パッケージ管理 | uv |
| Python リンター / フォーマッター | ruff |
| Python 型チェック | pyright |
| フロントエンド パッケージ管理 | pnpm |
| フロントエンド リンター | ESLint |
| フロントエンド フォーマッター | Prettier |

## 開発ルール

- `.env` や秘密情報はコミットしない
- DDDで設計・実装する（詳細は `docs/architecture.md`）

## 環境変数

- **pydantic-settings** で管理（`backend/shared/config/settings.py`）
- `.env` ファイルから読み込む（`env_file=".env"`）
- OS 環境変数が `.env` より優先される
- すべての変数に `PERIGEE_` プレフィックスを付ける（例: `PERIGEE_DB_HOST`）

## データベースマイグレーション

Alembic（async対応）を使用。DB接続情報は `pydantic-settings` 経由で `.env` から取得される（`alembic.ini` の `sqlalchemy.url` は使用しない）。

```bash
# backend ディレクトリで実行
cd backend

# マイグレーション適用（最新まで）
uv run alembic upgrade head

# 現在のリビジョン確認
uv run alembic current

# マイグレーション履歴
uv run alembic history

# 新規マイグレーション作成
uv run alembic revision -m "create_xxx_table"

# 1つ戻す
uv run alembic downgrade -1
```

- マイグレーションファイルは `backend/migrations/versions/` に連番プレフィックス付きで配置（例: `0001_create_users_table.py`）
- `migrations/env.py` で `Base.metadata` を参照しており、モデル定義から自動検出される

## Git / GitHub ルール

- **デフォルトブランチ**: `develop`
- **ブランチ戦略**: `develop` から派生 → 実装 → `develop` へPR
- **ブランチ命名**: `feature/xxx`, `fix/xxx`, `refactor/xxx`, `docs/xxx`
- **コミットメッセージ**: 英語（Conventional Commits）
- **Issue / PR**: 日本語で記述

## テスト戦略

| レイヤー | ツール | 方針 |
|---|---|---|
| ドメイン層（Python） | pytest | DB不要。純粋なビジネスロジックのユニットテスト |
| API層（FastAPI） | pytest + httpx | テスト用MariaDBコンテナで実行。認証・権限系を重点的にテスト |
| フロントエンド | Vitest + Testing Library | コンポーネント単位のテスト |
| E2E | Playwright | 主要ユーザーフローの結合テスト |

- テスト用DBはDocker Composeでテスト用MariaDBコンテナを使用（SQLiteモックは使わない）
- ドメイン層テストはDB非依存で高速に回す
- API層テストには `@pytest.mark.integration` を付与（DB依存）
- **pre-commit**: ユニットテスト（`pytest -m "not integration"`）+ リンター + 型チェック
- **CI**: 全テスト（integration含む）+ E2E（Playwright）

## ドキュメント

- APIドキュメント: FastAPI自動生成のSwagger UI（`/docs`）
- 設計ドキュメント: `docs/` 配下に配置

## 詳細ドキュメント

必要に応じて下記ドキュメントを参考にしてください

- `docs/system_design.md` # システム設計書（ユビキタス言語、ドメインイベント、ビジネスルール等）
- `docs/architecture.md` # アーキテクチャ設計（DDD構成、ディレクトリ構造、レイヤー責務）
- `docs/coding-standards.md` # コーディング規約（命名規則、カラートークン、レイヤー依存ルール等）
- `docs/wireframes.html` # 主要画面の画面イメージ。デザイン的なことより画面要素的な部分を参照する
