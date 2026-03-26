# アーキテクチャ設計

## 設計方針

- DDDに基づき、境界コンテキスト単位でコードを分割する
- 各コンテキストはドメイン層・アプリケーション層・インフラ層・プレゼンテーション層の4層構成
- コンテキスト間の参照はIDのみ。他コンテキストのドメインオブジェクトを直接参照しない
- ユビキタス言語は `docs/system_design.md` に定義済み。コード上の命名もこれに従う

## ディレクトリ構成

```
backend/
  contexts/
    workspace/             # ワークスペース：組織・グループの階層管理、所属、Captain / Member ロール
    preparation/           # 事前準備：スケジューリング、アジェンダ、事前コメント
      domain/
        value_objects.py   # ScheduleId, ScheduleGroupId など
    record/                # 記録：アジェンダ確認、メモ、アクションアイテム登録、メモの整理・仕上げ、下書き→公開、コメント・フィードバック、フォローアップ
    notification/          # Slack通知（通知設定も含む）
    # read_model/ は実装時に追加予定
  shared/                  # ドメイン共有（値オブジェクト、エンティティ、イベント基底クラス）
    domain/
      value_objects.py     # UserId など（コンテキスト共通の値オブジェクト）
      user.py              # User エンティティ（名前・メールアドレス・Slack ID を含む）
      user_repository.py   # UserRepository インターフェース
      events.py            # 基底クラス
    infrastructure/
      in_memory_user_repository.py  # UserRepository の固定データ仮実装
  foundation/              # 技術基盤（ドメイン非依存）
    domain/
      base_repository.py   # BaseRepository[TEntity, TId] ABC
      event_dispatcher.py  # EventDispatcher ABC
      exceptions.py        # OptimisticLockError
    application/
      unit_of_work.py      # UnitOfWork ABC
    infrastructure/
      sqlalchemy_unit_of_work.py      # SQLAlchemy UoW 実装
      in_memory_event_dispatcher.py   # インメモリ EventDispatcher 実装
    db/                    # SQLAlchemy async engine/session
    auth/                  # 認証ミドルウェア
    config/                # pydantic-settings
    logging/               # ログ設定
  api/
    register_routers.py    # 各コンテキストのrouterを集約・登録
  main.py                  # FastAPIエントリポイント
```

## コンテキスト内の構成

```
contexts/<context_name>/
  domain/                  # エンティティ、値オブジェクト、ドメインイベント、リポジトリインターフェース
  application/             # ユースケース（サービス層）、DTOなど
  infrastructure/          # リポジトリ実装、外部サービス連携
  presentation/            # FastAPI router、リクエスト/レスポンススキーマ
    router.py
    schemas.py
```

## レイヤーの責務

| レイヤー | 責務 | 依存先 |
|---|---|---|
| domain | ビジネスロジック、エンティティ、値オブジェクト、ドメインイベント | なし（純粋Python） |
| application | ユースケースの実行、トランザクション制御 | domain |
| infrastructure | DBアクセス、外部API呼び出し、リポジトリ実装 | domain, foundation |
| presentation | HTTPリクエスト/レスポンス、バリデーション、ルーティング | application |

- **domain層は他のどの層にも依存しない**（テスト容易性の根幹）
- infrastructure層はdomain層のリポジトリインターフェースを実装する（依存性逆転）

## ドメイン層の設計規約

### ドメイン例外

ビジネスルール違反には `ValueError` や `PermissionError` ではなく、ドメイン固有の例外クラスを使う。

- 例: `RecordAlreadyPublishedError`, `UnauthorizedOperationError`
- 例外クラスはコンテキストの `domain/exceptions.py` に配置する

```
contexts/<context_name>/
  domain/
    exceptions.py          # ドメイン固有の例外クラス
```

### フィールドのカプセル化（read-only プロパティ）

以下に該当するフィールドは `_` プレフィックス + read-only `@property` で公開し、直接代入を防ぐ。

- **状態遷移や不変条件を持つフィールド**: `status`, `is_completed` など
- **ドメインメソッド経由でのみ変更すべきフィールド**: `memo`, `updated_at`, `events` など

```python
class Record:
    def __init__(self, ..., status: RecordStatus) -> None:
        self._status = status

    @property
    def status(self) -> RecordStatus:
        return self._status

    def publish(self, now: datetime) -> None:
        self._status = RecordStatus.PUBLISHED
```

### ドメインイベントの管理

イベントは `_events` リストに蓄積し、`collect_events()` メソッドで取得とクリアを行う。

```python
class Record:
    def __init__(self, ...) -> None:
        self._events: list[DomainEvent] = []

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
```

### 値オブジェクトの配置

値オブジェクトは性質に応じて配置先を分ける。

| 種類 | 配置先 | 例 |
|---|---|---|
| ID型（UUID ラッパー）、Enum | `domain/value_objects.py` | `ScheduleId`, `RecordStatus` |
| ドメイン固有のバリデーションを持つ値オブジェクト | `domain/<vo_name>.py`（個別ファイル） | `Topic`, `CommentBody`, `TemplateName` |

- ID型・Enum はバリデーションロジックが薄く（UUID パース程度）、数が多いため `value_objects.py` にまとめる
- ドメイン固有の不変条件を持つ値オブジェクト（空禁止、最大長、改行禁止等）は関心が独立しているため個別ファイルに切り出す

### datetime の扱い

- **ファクトリメソッド（`create()`）**: `now: datetime | None = None` で受け取り、省略時は `datetime.now(UTC)` をフォールバックとして使用する
- **操作メソッド（`update_memo()`, `publish()` 等）**: `now: datetime` を必須引数にする

```python
class Record:
    @staticmethod
    def create(..., now: datetime | None = None) -> "Record":
        now = now or datetime.now(UTC)
        ...

    def publish(self, now: datetime) -> None:  # 必須
        ...
```

ファクトリメソッドでフォールバックを許容するのは、生成時のタイムスタンプが厳密でなくても実害が少ないため。操作メソッドで必須にするのは、テストでの再現性と、ユースケース層が時刻の責任を持つことを明確にするため。

## 境界コンテキストの対応

`docs/system_design.md` のドメイン設計との対応：

| コンテキスト | system_design上の対応 |
|---|---|
| workspace | ワークスペース（Workspace）：組織・グループの階層管理 + 所属（Membership） + Captain / Member ロール |
| preparation | 事前準備（Preparation）：スケジューリング + アジェンダ + 事前コメント |
| record | 記録（Record）：アジェンダ確認 + メモ + アクションアイテム登録 + メモの整理・仕上げ + 公開・共有 + コメント・フィードバック + フォローアップ + デフォルト公開先管理 |
| notification | 通知（Slack）+ 通知設定（ユーザーごと） |
| read_model | 参照（リードモデル） |

> **Settings コンテキスト廃止の経緯**: 当初はユーザーごとの通知設定・デフォルト公開先を管理する Settings コンテキストを計画していたが、通知設定は Notification コンテキスト内で管理する方が自然であり、デフォルト公開先は Workspace の Captain 提案として Record コンテキストが参照する形で対応できるため、独立コンテキストとしては不要と判断した。

> **統合の経緯**: イベントストーミング v17 の結果、旧 FollowUp コンテキストの責務（公開・共有、コメント、アクションアイテム完了）を Record に統合した。公開は Record の状態遷移であり、コメント等のドメインロジックも薄いため、独立コンテキストとしては不適切と判断した。実コード側の `backend/contexts/followup/`（空パッケージ）は削除済み。
>
> さらに Session（実施）コンテキストも Record に統合した。Session はまだ何も実装されておらず、実施中の操作（アジェンダ確認・メモ・アクションアイテム登録）は Record の責務として扱えるため、独立コンテキストとしては不要と判断した。実コード側の `backend/contexts/session/`（空パッケージ）は削除済み。

## Workspace コンテキストと他コンテキストの関係

Workspace コンテキストは組織・グループの階層と所属を管理する基盤的なコンテキストである。他のコンテキストは Workspace の情報をIDで参照する。

- **Record → Workspace**: 公開画面表示時に、カウンターパートの所属 Workspace を起点に祖先 Workspace の Captain を取得し、デフォルト Viewer として提案する。Viewer の確定は公開実行時にスナップショットとして Record 側に保存される。
- **Notification → Workspace**: 将来的に Workspace 単位の通知設定に対応する場合に参照する。

## ユースケースの呼び出し方針

- **コンテキスト内で完結するユースケース**: application 層のサービスを直接呼び出す。イベントは使わない
- **コンテキストを跨ぐユースケース**: ドメインイベント経由で連携する。呼び出し元のコンテキストがイベントを発行し、相手コンテキストのイベントハンドラが処理する

## コンテキスト間連携

- コンテキスト間はドメインイベントで連携する（例：「記録が公開された」→ notification が Slack通知を送信）
- 他コンテキストのエンティティを直接importしない。参照が必要な場合はIDで参照する
- オーガナイザー・カウンターパートの概念は各コンテキストが必要に応じてIDで参照する（専用のidentityコンテキストは設けない）

### EventDispatcher のハンドラ登録

- アプリケーション起動時（DI 設定）に、イベント型とハンドラの対応を `EventDispatcher` に登録する
- 1つのイベントに複数のハンドラを登録できる（例: `RecordPublished` → Slack 通知送信 + リードモデル更新）

### イベントハンドラのトランザクション境界

- イベントは **commit 後** にディスパッチする（`UnitOfWork + EventDispatcher 統合パターン` 参照）
- 各イベントハンドラは **独立したトランザクション** で実行する
- 発行元のトランザクションは既に確定済みのため、ハンドラの失敗が発行元をロールバックすることはない
- これは **結果整合性（eventual consistency）** の方針であり、ハンドラ失敗時はリトライや補償処理で対応する

## DI パターンの使い分け

本プロジェクトでは3つの DI パターンが混在しているが、それぞれ動作コンテキストが異なるため意図的に使い分けている。いずれも「1操作 = 1セッション」の原則を守っている。

### 1. API 層（リクエストスコープ）

FastAPI の Depends チェーンでセッション・リポジトリ・ユースケースを注入する。

- `api/dependencies.py` の `get_session()` がリクエスト単位で1セッションを提供する
- 各コンテキストの `presentation/dependencies.py` がリポジトリ・ユースケースを提供する
- リクエスト終了時にセッションが自動的にクローズされる

参照: `backend/api/dependencies.py`, `backend/contexts/*/presentation/dependencies.py`

### 2. スケジューラ層（バックグラウンドジョブ）

`_SessionScopedReminderService` がジョブ実行ごとにセッション・リポジトリを直接生成する。

- リクエスト外で動作するため FastAPI の Depends チェーンは使えない
- ジョブ実行単位で1セッションを生成・クローズする

参照: `backend/foundation/scheduler/lifespan.py`

### 3. イベントハンドラー層（ドメインイベント）

`_session_scoped_handler` がイベントごとに独立したセッション・リポジトリを生成する。

- UoW commit 後に非同期で実行されるため、発行元のセッションとは別のトランザクションになる
- ハンドラー失敗が発行元をロールバックしない（結果整合性）
- イベント単位で1セッションを生成・クローズする

参照: `backend/api/event_setup.py`

### 共通原則

| パターン | スコープ | セッション管理 |
|---|---|---|
| API 層 | リクエスト単位 | FastAPI Depends による自動管理 |
| スケジューラ層 | ジョブ実行単位 | ジョブ内で直接生成・クローズ |
| イベントハンドラー層 | イベント単位 | ハンドラー内で直接生成・クローズ |

- 関数内 import は循環 import 防止のため意図的に使用している

## アプリケーション層の設計規約

### ユースケースの Input / Output DTO

- ユースケースの入出力には `@dataclass(frozen=True)` の DTO を使用する
- DTO はユースケースクラスと同一ファイルに定義する（別ファイルに分離しない）
- 命名規則: `<ユースケース名>Input` / `<ユースケース名>Output`
- presentation 層（FastAPI の Pydantic スキーマ）とは分離し、ルーターで変換する

```python
@dataclass(frozen=True)
class CreateRecordFromScheduleInput:
    schedule_id: ScheduleId
    actor_id: UserId
    conducted_at: datetime

@dataclass(frozen=True)
class CreateRecordFromScheduleOutput:
    record_id: RecordId

class CreateRecordFromScheduleUseCase:
    async def execute(self, input_dto: CreateRecordFromScheduleInput) -> CreateRecordFromScheduleOutput:
        ...
```

### アプリケーション例外

ユースケース固有のエラー（リソース未検出、操作前提の不成立など）はアプリケーション例外として、ユースケースクラスと同一ファイルに定義する。

- **ドメイン例外**（ビジネスルール違反）→ `domain/exceptions.py` に配置（既存ルール通り）
- **アプリケーション例外**（ユースケース固有のエラー）→ ユースケースファイルに同居

```python
# ユースケースファイル内に定義
class ScheduleNotFoundError(Exception):
    """指定されたスケジュールが存在しない"""
    ...

class ScheduleCancelledError(Exception):
    """キャンセル済みスケジュールからの記録作成は不可"""
    ...
```

## インフラ層の設計規約

### ORM テーブル定義

- テーブル定義は各コンテキスト（または shared）の `infrastructure/tables.py` に配置し、`foundation/db/base.py` の `Base` を継承する
- 全テーブルに `TimestampMixin` を適用する（`created_at` / `updated_at` を自動付与）
- 新規テーブル追加時は `foundation/db/models.py` に明示 import を追加する（Alembic 自動検出の漏れ防止）

#### 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| ORM クラス名 | `XxxTable` | `WorkspaceTable`, `MembershipTable` |
| テーブル名 | スネークケース複数形 | `workspaces`, `confirmation_requests` |
| FK 制約名 | `fk_{テーブル名}_{カラム名}` | `fk_schedules_organizer_id` |
| UQ 制約名 | `uq_{テーブル名}_{カラム群}` | `uq_memberships_workspace_user` |

#### カラム規約

- UUID は `CHAR(36)` で文字列格納する
- 子エンティティのリレーション: `lazy="selectin"`（N+1 防止）+ `cascade="all, delete-orphan"`（子のライフサイクルを親に委譲）
- `ondelete` の使い分け:
  - 子→親（ライフサイクル連動）: `CASCADE`
  - 参照のみ（削除を防止）: `RESTRICT`
  - 任意参照（参照先が消えても存続）: `SET NULL`
- 順序を持つリスト（AgendaTemplate 等）は `position INTEGER NOT NULL` で順序を保持する

### datetime の扱い（インフラ層）

- DB セッションは `connect_args={"init_command": "SET time_zone='+00:00'"}` で UTC 固定
- `NOW()` / `CURRENT_TIMESTAMP` は常に UTC を返す
- アプリ層で datetime を生成する場合は `datetime.now(UTC)` を使用する
- 表示層で各ユーザーのタイムゾーンに変換する

### リポジトリ

- リポジトリインターフェースは `domain/` に ABC で定義する
- 各コンテキストのリポジトリインターフェースは `foundation/domain/base_repository.py` の `BaseRepository[TEntity, TId]` を継承する
- SQLAlchemy 実装は `infrastructure/` に配置する（依存性逆転）

#### 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| インターフェース | `XxxRepository` | `WorkspaceRepository`, `ScheduleRepository` |
| SQLAlchemy 実装 | `SqlAlchemyXxxRepository` | `SqlAlchemyWorkspaceRepository` |

#### save メソッドのパターン

リポジトリの `save()` は insert/update を自動判別する。

```python
async def save(self, entity: Xxx) -> None:
    existing = await self._session.get(XxxTable, str(entity.id.value))
    if existing is None:
        await self._insert(entity)
    else:
        await self._update(entity, existing)
```

- `_insert`: ORM オブジェクト生成 → 子エンティティを append → `session.add` → `flush()`
- `_update`: 既存 ORM オブジェクトのフィールドを上書き → 子エンティティを reconciliation → `flush()`
- `commit()` はリポジトリでは呼ばない（UnitOfWork が責務を持つ）

#### 子エンティティの reconciliation パターン

`_update` 時に子エンティティのコレクションを同期する:

1. 既存の子エンティティを `{id: ORM_row}` の辞書で保持
2. ドメインエンティティのリストを走査し、辞書に存在すれば更新・なければ追加
3. 辞書に残った未使用の行を削除（orphan 除去）

ID に意味を持たないリスト（AgendaTemplate 等）は reconciliation ではなく全削除→全挿入でもよい。

#### `_to_entity` 変換メソッド

ORM → ドメインモデル変換は `@staticmethod` の `_to_entity` メソッドで行う:

- ORM のスカラー値を値オブジェクト（`XxxId.from_str()`, `XxxName()` 等）に変換する
- プライベートフィールド（`_name`, `_status` 等）はコンストラクタ引数で直接復元する
- 子エンティティは ORM リレーションから同様に変換する

### 競合制御（楽観ロック）

- 楽観ロックはプロジェクト全体の必須規約ではなく、コンテキストごとの要件に応じて個別に判断する
- 競合制御が必要なコンテキストでは楽観ロック（`version` カラム等）を個別に検討する
- `updated_at` はログ用途のみとして扱い、楽観ロックの照合には使用しない
- `OptimisticLockError` は `foundation/domain/exceptions.py` に定義されており、必要に応じて利用できる

### foundation/db/models.py 登録ルール

- 新規テーブルを追加した場合は、必ず `foundation/db/models.py` に明示 import を追加すること
- Alembic の autogenerate は `Base.metadata` を参照するため、import されていないテーブルは検出されない
- import の形式: `from <context>.infrastructure.tables import <TableClass>  # noqa: F401`

```python
# foundation/db/models.py の例
from shared.infrastructure.tables import UserTable  # noqa: F401
from contexts.preparation.infrastructure.tables import ScheduleTable  # noqa: F401
```

### UnitOfWork + EventDispatcher 統合パターン

- `UnitOfWork.commit()` は DB commit のみを行い、イベントディスパッチは含まない
- アプリケーションサービスが commit 後に明示的にイベントをディスパッチする
- これにより、DB コミットとイベント処理の責務を分離し、テスト容易性を確保する

```python
# アプリケーションサービスでの使用例
class PublishRecordService:
    def __init__(
        self,
        uow: UnitOfWork,
        record_repo: RecordRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._record_repo = record_repo
        self._event_dispatcher = event_dispatcher

    async def execute(self, record_id: RecordId, actor_id: UserId) -> None:
        async with self._uow:
            record = await self._record_repo.get_by_id(record_id)
            record.publish(actor_id=actor_id, now=datetime.now(UTC))
            await self._record_repo.save(record)
            events = record.collect_events()
            await self._uow.commit()

        # commit 成功後にイベントをディスパッチ
        await self._event_dispatcher.dispatch(events)
```
