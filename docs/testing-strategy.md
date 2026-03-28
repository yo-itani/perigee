# テスト方針 (Testing Strategy)

本ドキュメントでは、perigee プロジェクトにおけるテストの分類・実行方法・データ生成方針・認証方針・共通 fixture の使い方を定める。

## テスト分類

| 分類 | 対象レイヤー | DB 依存 | pytest マーカー | 実行タイミング |
|---|---|---|---|---|
| Unit | ドメイン層・アプリケーション層 | なし | (なし) | pre-commit, CI |
| Integration | インフラ層・プレゼンテーション層 | あり (MariaDB) | `@pytest.mark.integration` | CI |
| E2E | フロントエンド + バックエンド全体 | あり | - | CI (Playwright) |

### Unit テスト

- ドメインエンティティ・値オブジェクト・ユースケースの振る舞いを検証する
- DB やネットワーク I/O に依存しない
- リポジトリや UoW は In-Memory 実装（テストダブル）に差し替える
- `pre-commit` フックで毎回実行される

### Integration テスト

- SQLAlchemy リポジトリ実装やプレゼンテーション層（FastAPI ルーター）を、テスト用 MariaDB コンテナを使って検証する
- `pytestmark = pytest.mark.integration` をモジュールレベルで付与する
- CI でのみ実行される（pre-commit では除外）

### E2E テスト

- Playwright を使い、フロントエンドからバックエンドまでの主要ユーザーフローを検証する
- CI でのみ実行される

## テスト用 MariaDB コンテナの起動方法

Integration テストの実行には、テスト用 MariaDB コンテナが起動済みである必要がある。

```bash
# コンテナ起動
docker compose up -d mariadb

# ヘルスチェックが通るまで待機
docker compose exec mariadb healthcheck.sh --connect --innodb_initialized
```

`docker/mariadb/initdb.sh` により、初回起動時にテスト用データベース `perigee_test` が自動作成される。テスト用 DB の接続情報は本番用と同じホスト・ポート・ユーザーを使用し、データベース名のみ `perigee_test` に切り替える。

## テストの実行方法

```bash
cd backend

# Unit テストのみ実行（pre-commit で実行されるもの）
uv run pytest -m "not integration"

# Integration テストのみ実行
uv run pytest -m integration

# 全テスト実行
uv run pytest

# 特定のコンテキストのテストを実行
uv run pytest tests/contexts/record/domain/

# 特定のテストファイルを実行
uv run pytest tests/contexts/record/domain/test_record.py

# 特定のテストクラス・メソッドを実行
uv run pytest tests/contexts/record/domain/test_record.py::TestPublish::test_publish_draft
```

## テストデータ生成方針 (polyfactory)

テストデータの生成には [polyfactory](https://github.com/litestar-org/polyfactory) を使用する。ファクトリは `backend/tests/factories.py` に集約する。

### 現在のファクトリ

| ファクトリ | 対象 | 方式 |
|---|---|---|
| `UserTableFactory` | `UserTable` (ORM モデル) | 手動ラッパー (`build()` staticmethod) |
| `SystemSettingsTableFactory` | `SystemSettingsTable` (ORM モデル) | 手動ラッパー (`build()` / `build_completed()` staticmethod) |
| `UserIdFactory` | `UserId` (値オブジェクト) | `DataclassFactory` 継承 |

### 使い分け方針

- **ORM モデル**: polyfactory は SQLAlchemy ORM モデルをネイティブにサポートしないため、`build()` staticmethod による手動ラッパーを作成する
- **データクラス（値オブジェクト等）**: `DataclassFactory` を継承して自動生成する
- **ドメインエンティティ**: ファクトリメソッド（`Entity.create(...)` 等）を直接呼び出してテスト内で構築する

## 認証方針

テストにおける認証は、DI override を使わず、テスト用 JWT トークンの発行またはヘッダー付与で行う。

### Unit テスト（ユースケース層）

ユースケースのテストでは認証は対象外。`user_id` を直接引数として渡す。

### Integration テスト（プレゼンテーション層）

プレゼンテーション層のテストでは、本番と同じ JWT 認証を通す。`tests/helpers.py` の `auth_headers()` / `create_authenticated_client()` を使い、テスト用秘密鍵で署名した Bearer トークンを付与する。DI override による認証差し替えは行わない。

```python
from tests.helpers import auth_headers, create_async_client

pytestmark = pytest.mark.integration

def _create_test_app():
    from fastapi import FastAPI
    app = FastAPI()
    app.state.event_dispatcher = create_event_dispatcher()
    register_exception_handlers(app)
    register_routers(app)
    return app

@pytest.fixture
def app():
    return _create_test_app()

# 認証済みリクエスト
async def test_authenticated_request(app, user_id: str) -> None:
    async with create_async_client(app, headers=auth_headers(user_id)) as client:
        response = await client.post(
            "/some-endpoint",
            json={...},
        )
    assert response.status_code == 201
```

### 認証ルーター自体のテスト

認証ルーターのテスト (`test_auth_router.py`) では、`_FakeSettings` を `unittest.mock.patch` で差し替え、In-Memory リポジトリを DI override で注入する。これは認証機能そのものをテストするための例外的な手法であり、通常のエンドポイントテストでは DI override を使わない。

## 共通 fixture

### ルートレベル (`tests/conftest.py`)

テスト全体で必要な環境変数のデフォルト値と、DB fixture を提供する。

```python
os.environ.setdefault(
    "PERIGEE_JWT_SECRET_KEY",
    "test-secret-key-for-unit-tests-32chars!",
)
```

| fixture | スコープ | 用途 |
|---|---|---|
| `test_engine` | session | テスト用 DB への非同期エンジン。セッション開始時にテーブル作成、終了時に削除 |
| `session` | function | 各テスト後にロールバックする非同期セッション |
| `session_factory` | function | 複数セッションが必要なテスト向けのセッションファクトリ |

`test_engine` fixture はテストセッション開始時に `Base.metadata.create_all` でテーブルを作成し、終了時に `Base.metadata.drop_all` で削除する。各テストは `session` fixture を通じてトランザクション内で実行され、テスト後にロールバックされる。

各コンテキストの `tests/contexts/*/infrastructure/conftest.py` はルートの fixture に委譲する薄いファイルであり、fixture の実体は定義していない。

### Application 層 (`tests/contexts/*/application/conftest.py`)

各コンテキストの application 層テスト用に、In-Memory のテストダブルを提供する。

| テストダブル | 種別 | 用途 |
|---|---|---|
| `InMemory*Repository` | Stub | リポジトリの In-Memory 実装。内部に `dict` を持ち、保存・取得を模倣する |
| `StubUnitOfWork` / `FakeUnitOfWork` | Stub | UoW の模倣。`committed` / `rolled_back` フラグで呼び出しを検証する |
| `InMemoryEventDispatcher` / `SpyEventDispatcher` | Spy | ディスパッチされたイベントを記録する |
| `SpyNotificationSender` | Spy | 送信された通知を記録する。`fail_for` で送信失敗をシミュレート可能 |

これらは pytest fixture として公開され、テスト関数の引数として注入する。

```python
@pytest.fixture
def uow() -> StubUnitOfWork:
    return StubUnitOfWork()

@pytest.fixture
def schedule_group_repo() -> InMemoryScheduleGroupRepository:
    return InMemoryScheduleGroupRepository()
```
