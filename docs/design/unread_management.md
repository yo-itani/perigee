# 未読管理モデル設計

> Issue #111 の設計検討結果。Record の未読/既読管理の仕組みを定義する。

---

## 1. 背景と目的

ダッシュボードに「未読記録」セクションを表示するために、ユーザーごとの Record 既読状態を管理する仕組みが必要である。

### 関連する既存方針（#148）

Issue #148 では、**Notification コンテキストの通知レコードに `is_read` フラグを追加する方針**が確定している。これは「通知の既読管理」であり、本 Issue で検討する「Record の未読管理」とは異なる概念である。

| 項目 | #148 通知の既読管理 | #111 Record の未読管理 |
|---|---|---|
| 対象 | 個々の通知メッセージ | Record（1on1記録）そのもの |
| 管理主体 | Notification コンテキスト | Record コンテキスト |
| 判定基準 | 通知を既読にしたか | Record を閲覧したか |
| 未読に戻るトリガー | 新しい通知が発行される | Record に新しいコメント等が追加される |
| ユースケース | 「未読通知バッジ」「ダッシュボード未読一覧」 | Record 詳細画面の閲覧追跡 |

### ダッシュボードでの使い分け

ダッシュボードの「未読の記録・コメント」セクションは **`GET /notifications?unread=true`（#148）を参照元とする**。Record 側の `ReadStatus` はダッシュボード一覧には使用しない。

`ReadStatus` の役割は Record 詳細画面での閲覧追跡に限定する:
- ユーザーが Record 詳細画面を開いた → `POST /records/{id}/viewed` で既読マーク
- Record 詳細画面上で「未読のコンテンツがある」かどうかの判定に使用

両者は独立した仕組みである。通知を既読にしても Record 本文を開くまでは ReadStatus 上は「未閲覧」のままであり、逆に Record を直接開いても対応する通知は自動既読にはならない。この分離は意図的であり、通知と Record 閲覧はそれぞれ独立した行為として扱う。

---

## 2. 決定事項

### 管理方式: 案A（最終閲覧日時方式）

ユーザー × Record ごとに `last_viewed_at` を記録し、Record の `latest_activity_at` と比較して未読判定する。

### コンテキスト配置: Record コンテキスト内

`ReadStatus` を Record コンテキスト内のエンティティとして配置する。将来 `read_model` モジュールへ切り出せる構造にする（リポジトリインターフェースで分離）。

---

## 3. 管理方式の比較（検討経緯）

### 案A: 最終閲覧日時方式（採用）

ユーザー × Record ごとに `last_viewed_at` を記録し、Record の `latest_activity_at` と比較して未読判定する。

**メリット:**
- 「未読に戻す」ロジックが暗黙的に解決される。Record に新しいコメントが追加されると `last_viewed_at` < `latest_activity_at` となり自動的に未読になる
- 既読→未読の状態遷移を明示的に管理する必要がない
- 「何がいつ更新されたか」をタイムスタンプ比較で柔軟に判定できる

**デメリット:**
- 未読判定のクエリが複雑になる（Record の最新更新日時を算出する必要がある）
- 「最新更新日時」の定義が曖昧になりやすい → `latest_activity_at` として明確に定義して解消

### 案B: 既読フラグ方式（不採用）

ユーザー × Record ごとに `is_read: bool` を保持する。

**不採用理由:**
- 「未読に戻す」を明示的に実装する必要がある（コメント追加時に `is_read = FALSE` に戻す処理）
- 未読に戻す条件のルール定義と、それを発火させるイベントハンドラが必要
- #148 の Notification 側も `is_read` フラグ方式のため、概念が混同しやすい

### 案C: 既読イベント方式（不採用）

`RecordViewed` イベントを発行し、未読一覧はイベント有無で判定する。

**不採用理由:**
- データ量が膨大になる（閲覧するたびにイベントが増加）
- 未読判定クエリが複雑
- 本システムの規模感に対して過剰設計

---

## 4. 未読判定ルール

### 判定式

```
判定キー: user_id × record_id
保持項目: last_viewed_at
未読判定: last_viewed_at < latest_activity_at
```

### `latest_activity_at` の定義

Record の以下のタイムスタンプの最大値:

| イベント | タイムスタンプ |
|---|---|
| 記録公開（`RecordPublished`） | `published_at` |
| コメント追加（`RecordCommentAdded`） | コメントの `created_at` |

**`latest_activity_at` が更新されないケース:**
- Viewer の追加・削除（閲覧権限の変更は「コンテンツの更新」ではない）
- 下書き中のメモ更新（下書きは公開前であり、未読管理の対象外）

---

## 5. 未読に「戻す」条件の定義

| イベント | 未読に戻るか | 対象ユーザー | 備考 |
|---|---|---|---|
| Record が公開された | はい | カウンターパート + Viewer | 初回公開で未読状態になる |
| コメントが追加された | はい | 閲覧可能ユーザー全員（**投稿者本人を除く**） | 投稿者本人は自動既読扱い |
| Viewer が追加された | 条件付き | 追加された Viewer のみ | 追加時点以降のイベントのみ未読対象（過去分は遡及しない） |
| Viewer が削除された | — | — | 削除された Viewer の `read_status` レコードを削除する |

### コメント投稿者の自動既読

コメント追加時に `latest_activity_at` が更新されるが、投稿者本人については `last_viewed_at` も同時刻に更新する。これにより投稿者本人は自分のコメントで未読にならない。

### Viewer 追加時の挙動

Viewer 追加時に `ReadStatus` を作成し、`last_viewed_at` を追加時点のタイムスタンプに設定する。これにより:
- 追加時点より前の `latest_activity_at` は `last_viewed_at` 以下となり、既読扱いになる
- 追加時点より後のイベント（新しいコメント等）で `latest_activity_at` が更新されると未読になる

### Viewer 削除時の挙動

Viewer が削除された場合、該当ユーザーの `record_read_statuses` レコードを削除する。閲覧権限がなくなった時点で既読状態を保持する意味がない。

---

## 6. コンテキスト配置の決定

### Record コンテキスト内に配置

理由:

1. **ReadStatus は Record の閲覧に密結合**: 未読判定に必要な `latest_activity_at` は Record エンティティの属性であり、`is_visible_to()` も Record のドメインロジックである。別コンテキストに配置すると Record の内部状態に依存するクエリが発生し、コンテキスト間の結合度が上がる

2. **リードモデルとの区別**: `architecture.md` の `read_model/` は「全フェーズの結果を蓄積」する参照系リードモデルを想定している（例: 1on1履歴一覧、前回サマリー）。ReadStatus は特定の Record に対するユーザーの閲覧状態であり、複数コンテキストのデータを集約するリードモデルとは性質が異なる

3. **Record コンテキストの既存パターンとの整合**: Record コンテキストには既に `RecordViewerTable`（ユーザー × Record の関連）が存在する。`ReadStatusTable` も同様の構造であり、同一コンテキスト内で自然に共存できる

### 将来の `read_model` 切り出し

リポジトリインターフェース（`ReadStatusRepository`）を介してアクセスするため、将来的にデータの配置先を変更する場合もインフラ層の差し替えのみで対応できる。

---

## 7. データモデル

### テーブル設計

#### `record_read_statuses` テーブル

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| `id` | CHAR(36) | PK | ReadStatus の ID（UUID） |
| `record_id` | CHAR(36) | FK → records.id, NOT NULL | 対象 Record |
| `user_id` | CHAR(36) | FK → users.id, NOT NULL | 閲覧ユーザー |
| `last_viewed_at` | DATETIME(6) | NOT NULL | 最終閲覧日時（UTC） |
| `created_at` | DATETIME(6) | NOT NULL | レコード作成日時 |
| `updated_at` | DATETIME(6) | NOT NULL | レコード更新日時 |

**制約:**
- `UNIQUE(record_id, user_id)` — ユーザー × Record の組み合わせは一意
- `FK record_id → records.id ON DELETE CASCADE` — Record 削除時に連動削除
- `FK user_id → users.id ON DELETE CASCADE` — ユーザー削除時に連動削除

#### `records` テーブルへの追加カラム

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| `latest_activity_at` | DATETIME(6) | NULL | コンテンツ最終更新日時。公開前は NULL |

- 公開時に `latest_activity_at = published_at` で初期化
- コメント追加時に `latest_activity_at = comment.created_at` で更新

### 既存データのバックフィル方針

マイグレーションで `latest_activity_at` カラムを追加する際、既存の公開済み Record に対して以下のルールでバックフィルする:

```sql
-- Step 1: 公開済み Record に published_at をベースに設定
UPDATE records
SET latest_activity_at = published_at
WHERE status = 'published' AND latest_activity_at IS NULL;

-- Step 2: コメントがある Record は最新コメントの created_at で上書き
UPDATE records r
SET latest_activity_at = (
    SELECT MAX(rc.created_at)
    FROM record_comments rc
    WHERE rc.record_id = r.id
)
WHERE r.status = 'published'
  AND EXISTS (
    SELECT 1 FROM record_comments rc
    WHERE rc.record_id = r.id AND rc.created_at > r.latest_activity_at
  );
```

- 未公開（下書き）の Record は `latest_activity_at = NULL` のまま（公開時に設定される）
- バックフィルはマイグレーションファイル内の `data_migrations` ステップとして実行する
- バックフィル完了後も `latest_activity_at` は NULL 許容のまま（新規作成→公開前の Record のため）

### インデックス戦略

```sql
-- 未読一覧取得の主要クエリ用
CREATE INDEX idx_record_read_statuses_user_id ON record_read_statuses (user_id);

-- ユーザー × Record の一意制約（UNIQUE 制約がインデックスを兼ねる）
-- record_id での検索は UNIQUE 制約のインデックスで対応
```

### 主要クエリパターン

```sql
-- 特定 Record の未読判定（Record 詳細画面用）
SELECT
  CASE
    WHEN rs.id IS NULL THEN TRUE
    WHEN rs.last_viewed_at < r.latest_activity_at THEN TRUE
    ELSE FALSE
  END AS is_unread
FROM records r
LEFT JOIN record_read_statuses rs
  ON rs.record_id = r.id AND rs.user_id = :user_id
WHERE r.id = :record_id;

-- 閲覧時の ReadStatus 更新（UPSERT）
INSERT INTO record_read_statuses (id, record_id, user_id, last_viewed_at, created_at, updated_at)
VALUES (:id, :record_id, :user_id, :now, :now, :now)
ON DUPLICATE KEY UPDATE last_viewed_at = :now, updated_at = :now;
```

> **Note**: ダッシュボードの「未読の記録・コメント」一覧は `GET /notifications?unread=true`（#148）を使用する。Record 側での未読一覧クエリは不要。

### パフォーマンス考慮

- **データ量見積もり**: ユーザー数 × 閲覧済み Record 数。初期想定では数千〜数万行程度（1on1管理ツールの規模）
- **未閲覧の Record は行が存在しない**: `LEFT JOIN` + `IS NULL` で未読判定するため、閲覧していない Record のぶんの行は不要。データ量はユーザーが実際に閲覧した Record 数に比例する
- **UPSERT パターン**: `ON DUPLICATE KEY UPDATE` で挿入と更新を一文で処理。閲覧のたびに `last_viewed_at` を更新するだけなので書き込み負荷は低い

---

## 8. ドメインモデル設計

### ReadStatus エンティティ

```python
@dataclass
class ReadStatus:
    """ユーザーの Record 閲覧状態を管理するエンティティ。

    Record コンテキスト内に配置する。
    Aggregate root ではなく、Record の閲覧操作に付随するエンティティ。
    """
    id: ReadStatusId
    record_id: RecordId
    user_id: UserId
    _last_viewed_at: datetime

    @property
    def last_viewed_at(self) -> datetime:
        return self._last_viewed_at

    @staticmethod
    def create(
        *,
        record_id: RecordId,
        user_id: UserId,
        now: datetime | None = None,
    ) -> ReadStatus:
        ts = now or datetime.now(UTC)
        return ReadStatus(
            id=ReadStatusId.generate(),
            record_id=record_id,
            user_id=user_id,
            _last_viewed_at=ts,
        )

    def mark_viewed(self, now: datetime) -> None:
        """閲覧日時を更新する。"""
        self._last_viewed_at = now
```

### Record エンティティへの追加

```python
class Record:
    # 既存フィールド...
    _latest_activity_at: datetime | None  # 公開前は None

    @property
    def latest_activity_at(self) -> datetime | None:
        return self._latest_activity_at

    def publish(self, *, actor_id: UserId, now: datetime) -> None:
        # 既存の処理...
        self._latest_activity_at = now  # 追加

    def notify_comment_added(self, now: datetime) -> None:
        """コメント追加時にコンテンツ更新日時を更新する。"""
        self._latest_activity_at = now
        self._updated_at = now
```

### ReadStatusRepository インターフェース

```python
class ReadStatusRepository(ABC):
    @abstractmethod
    async def find_by_record_and_user(
        self, record_id: RecordId, user_id: UserId
    ) -> ReadStatus | None:
        ...

    @abstractmethod
    async def save(self, read_status: ReadStatus) -> None:
        ...

    @abstractmethod
    async def delete_by_record_and_user(
        self, record_id: RecordId, user_id: UserId
    ) -> None:
        """Viewer 削除時に既読状態を削除する。"""
        ...
```

### 値オブジェクト

```python
@dataclass(frozen=True)
class ReadStatusId:
    value: uuid.UUID

    @staticmethod
    def generate() -> ReadStatusId:
        return ReadStatusId(value=uuid.uuid4())

    @staticmethod
    def from_str(raw: str) -> ReadStatusId:
        return ReadStatusId(value=uuid.UUID(raw))
```

---

## 9. ユースケース

### Record 閲覧時の既読マーク

```
MarkRecordAsViewed
  Input: record_id, actor_id (閲覧者)
  処理:
    1. Record を取得し、actor が閲覧権限を持つことを確認 (is_visible_to)
    2. ReadStatus を取得（存在しなければ新規作成）
    3. last_viewed_at を現在時刻に更新
    4. 保存
```

**推奨**: `POST /records/{id}/viewed` を明示的に呼び出す方式。GET リクエストに副作用（既読マーク）を持たせるのは RESTful でなく、キャッシュやプリフェッチで意図しない既読が発生するリスクがある。

### コメント追加時の自動既読（投稿者本人）

```
AddComment ユースケース内:
  1. コメントを追加
  2. Record.notify_comment_added(now) で latest_activity_at を更新
  3. 投稿者本人の ReadStatus.last_viewed_at を now に更新（自動既読）
```

---

## 10. API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `POST` | `/records/{record_id}/viewed` | Record を閲覧済みにする |

> ダッシュボードの未読一覧は `GET /notifications?unread=true`（#148）を使用するため、`GET /records/unread` は設けない。

---

## 11. イベントフローまとめ

```
RecordPublished
  → Record.latest_activity_at = published_at（Record コンテキスト内）
  → Notification 送信（Notification コンテキスト — 既存の RecordPublishedHandler）
  → カウンターパート・Viewer にとって「未読記録」になる

RecordCommentAdded
  → Record.notify_comment_added(now)（Record コンテキスト内、ユースケースで直接呼び出し）
  → Record.latest_activity_at = comment.created_at
  → 投稿者本人の ReadStatus.last_viewed_at = comment.created_at（自動既読）
  → 投稿者以外の閲覧可能ユーザーにとって「未読記録」に戻る
  → Notification 送信（Notification コンテキスト — 既存の RecordCommentAddedHandler）

ViewerAdded
  → ReadStatus を作成（last_viewed_at = 追加時点のタイムスタンプ）
  → 追加時点より前のイベントは既読扱い

ViewerRemoved
  → 該当ユーザーの ReadStatus を削除

ユーザーが Record 詳細画面を開く
  → POST /records/{record_id}/viewed
  → ReadStatus.last_viewed_at = now
  → 当該 Record が閲覧済みになる
```

---

## 12. 実装 Issue（後続）

本設計に基づき、以下の実装 Issue を作成する:

1. **Record エンティティに `latest_activity_at` を追加** — ドメインモデル変更 + マイグレーション（既存データのバックフィル含む）
2. **ReadStatus ドメインモデル・リポジトリ実装** — エンティティ、テーブル、リポジトリ
3. **既読マークユースケース + API** — `MarkRecordAsViewed` + `POST /records/{id}/viewed`
4. **コメント追加時の `latest_activity_at` 更新 + 投稿者自動既読** — 既存の `AddComment` ユースケースに追加
5. **Viewer 追加/削除時の ReadStatus 管理** — Viewer 操作に連動した ReadStatus の作成・削除
