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
    preparation/           # 事前準備：スケジューリング、アジェンダ、事前コメント
      domain/
        value_objects.py   # ScheduleId, ScheduleGroupId など
    session/               # 実施：アジェンダ確認、メモ、アクションアイテム登録
    record/                # 記録：メモの整理・仕上げ、下書き
    followup/              # フォローアップ：記録の公開・共有、コメント、フォローアップ
    notification/          # Slack通知
    # read_model/, settings/ は実装時に追加予定
  shared/                  # ドメイン共有（値オブジェクト、エンティティ、イベント基底クラス）
    domain/
      value_objects.py     # UserId など（コンテキスト共通の値オブジェクト）
      user.py              # User エンティティ（最小構成）
      user_repository.py   # UserRepository インターフェース
      events.py            # 基底クラス
    infrastructure/
      in_memory_user_repository.py  # UserRepository の固定データ仮実装
  foundation/              # 技術基盤（ドメイン非依存）
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
| preparation | 事前準備（Preparation）：スケジューリング + アジェンダ + 事前コメント |
| session | 実施（Session） |
| record | 記録（Record） |
| followup | フォローアップ（FollowUp）：公開・共有・コメント・フォローアップ |
| notification | 通知（Slack） |
| read_model | 参照（リードモデル） |
| settings | ユーザーごとの通知設定・デフォルト公開先 |

## コンテキスト間連携

- コンテキスト間はドメインイベントで連携する（例：「記録が公開された」→ notification が Slack通知を送信）
- 他コンテキストのエンティティを直接importしない。参照が必要な場合はIDで参照する
- オーガナイザー・カウンターパートの概念は各コンテキストが必要に応じてIDで参照する（専用のidentityコンテキストは設けない）
