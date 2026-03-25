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
| 管理主体 | Notification コンテキスト | 本設計で決定 |
| 判定基準 | 通知を既読にしたか | Record を閲覧したか |
| 未読に戻るトリガー | 新しい通知が発行される | Record に新しいコメント等が追加される |
| ユースケース | 「未読通知バッジ」 | 「未読記録一覧」（ダッシュボード） |

両者は独立した仕組みだが、ユーザー体験上は連動する場面がある。例えば `RecordPublished` の通知が送信されると未読通知が増え、同時にその Record はユーザーにとって「未読記録」でもある。通知を既読にしても Record 本文を開くまでは「未読記録」のままであり、逆に Record を直接開いても対応する通知は自動既読にはならない。この分離は意図的であり、通知と Record 閲覧はそれぞれ独立した行為として扱う。

---

## 2. 管理方式の比較

### 案A: 最終閲覧日時方式

ユーザー x Record ごとに `last_viewed_at` を記録し、Record の更新日時（`updated_at` や `published_at`、最新コメントの `created_at`）と比較して未読判定する。

**メリット:**
- 「未読に戻す」ロジックが暗黙的に解決される。Record に新しいコメントが追加されると `last_viewed_at` < コメント `created_at` となり自動的に未読になる
- 既読→未読の状態遷移を明示的に管理する必要がない
- 「何がいつ更新されたか」をタイムスタンプ比較で柔軟に判定できる

**デメリット:**
- 未読判定のクエリが複雑になる（Record の最新更新日時を算出する必要がある）
- 「最新更新日時」の定義が曖昧になりやすい（メモ更新？コメント追加？Viewer 変更？）
- パフォーマンス面で、Record ごとに最新コメント日時を集計する JOIN が必要

### 案B: 既読フラグ方式

ユーザー x Record ごとに `is_read: bool` を保持する。

**メリット:**
- 実装がシンプル。未読一覧の取得は `WHERE is_read = FALSE` のみ
- クエリが高速（単純なフラグ検索）
- 判定ロジックが明確

**デメリット:**
- 「未読に戻す」を明示的に実装する必要がある（コメント追加時に `is_read = FALSE` に戻す処理）
- 未読に戻す条件のルール定義と、それを発火させるイベントハンドラが必要
- フラグの更新漏れが起きると不整合になる

### 案C: 既読イベント方式

`RecordViewed` イベントを発行し、未読一覧はイベント有無で判定する。

**メリット:**
- 閲覧履歴が残る（監査ログ的な用途にも対応可能）
- イベントソーシング的なアプローチで拡張性が高い

**デメリット:**
- データ量が膨大になる（閲覧するたびにイベントが増加）
- 未読判定クエリが複雑（最新の RecordViewed イベントと Record 更新日時の比較）
- 過剰設計。本システムの規模感に対して不釣り合い

---

## 3. 推奨案: 案A（最終閲覧日時方式）

### 選定理由

1. **未読に戻す条件の自然な表現**: 案B の既読フラグ方式では「コメント追加時に `is_read = FALSE` に戻す」処理を明示的に実装する必要があり、条件の追加・変更のたびにイベントハンドラの修正が必要になる。案A では Record 側の更新日時が閲覧日時を超えれば自動的に未読となるため、未読に戻す条件の拡張が容易である

2. **#148 との役割分離の明確化**: #148 の Notification 側が `is_read` フラグ方式を採用するため、Record 側も同じ `is_read` フラグ方式にすると概念が混同しやすい。最終閲覧日時方式にすることで、通知の既読管理（フラグ）と Record の未読管理（タイムスタンプ比較）が設計レベルで区別される

3. **コメント追加以外の「更新」への対応力**: 将来的に Record に新しい種類の更新（例: メモの追記、Viewer 変更通知）が加わった場合も、更新日時の比較だけで未読判定が成立する。フラグ方式ではその都度「未読に戻す」ハンドラを追加しなければならない

4. **案C は過剰**: 本システムの規模感（1on1管理ツール）では閲覧イベントの蓄積は不要。データ量とクエリ複雑性のコストに見合わない

### 「最新更新日時」の定義

案A のデメリットである「最新更新日時の定義の曖昧さ」を解消するため、Record 側に `content_updated_at` を導入する。

**`content_updated_at` が更新されるタイミング:**
- Record が公開された時（`RecordPublished` → `published_at` を `content_updated_at` に設定）
- Record にコメントが追加された時（`RecordCommentAdded` → コメントの `created_at` を `content_updated_at` に設定）

**`content_updated_at` が更新されないタイミング:**
- Viewer の追加・削除（閲覧権限の変更は「コンテンツの更新」ではない）
- 下書き中のメモ更新（下書きは公開前であり、未読管理の対象外）

未読判定式:

```
未読 = (read_status が存在しない) OR (read_status.last_viewed_at < record.content_updated_at)
```

---

## 4. 未読に「戻す」条件の定義

| イベント | 未読に戻るか | 理由 |
|---|---|---|
| Record が公開された | 対象: カウンターパート + Viewer。初回公開で未読状態になる（`content_updated_at` = `published_at`） | コンテンツが初めて閲覧可能になる |
| コメントが追加された | 対象: コメント投稿者以外の閲覧可能ユーザー全員（`content_updated_at` がコメント日時で更新される） | 新しいコンテンツが追加された |
| Viewer が追加された | 新しい Viewer は未読（`read_status` が存在しないため自動的に未読）。既存ユーザーの未読状態は変わらない | 権限変更はコンテンツ更新ではない |
| Viewer が削除された | 削除された Viewer の `read_status` は残存するが、`is_visible_to` が `false` になるため未読一覧に表示されない | 閲覧権限がなくなった時点で未読管理の対象外 |

### コメント追加時の `content_updated_at` 更新

コメント追加時に Record の `content_updated_at` を更新する必要がある。これは以下の方法で実現する:

- `RecordCommentAdded` イベントのハンドラとして、Record の `content_updated_at` を更新するサービスを用意する
- あるいは、Record エンティティに `notify_comment_added(now: datetime)` のようなメソッドを追加し、コメント追加ユースケース内で呼び出す

後者のアプローチを推奨する。コメント追加は Record コンテキスト内の操作であり、コンテキスト内で完結するユースケースはイベントではなく直接呼び出しで連携する方針（`docs/architecture.md`）に合致する。

---

## 5. コンテキスト配置

### 選択肢

| 選択肢 | 説明 |
|---|---|
| A: Record コンテキスト内に配置 | `ReadStatus` を Record コンテキストのエンティティとして追加 |
| B: 独立した Read Model（read_model モジュール）に配置 | `docs/architecture.md` の `# read_model/ は実装時に追加予定` に対応 |

### 決定: Record コンテキスト内に配置

理由:

1. **ReadStatus は Record の閲覧に密結合**: 未読判定に必要な `content_updated_at` は Record エンティティの属性であり、`is_visible_to()` も Record のドメインロジックである。別コンテキストに配置すると Record の内部状態に依存するクエリが発生し、コンテキスト間の結合度が上がる

2. **リードモデルとの区別**: `architecture.md` の `read_model/` は「全フェーズの結果を蓄積」する参照系リードモデルを想定している（例: 1on1履歴一覧、前回サマリー）。ReadStatus は特定の Record に対するユーザーの閲覧状態であり、複数コンテキストのデータを集約するリードモデルとは性質が異なる

3. **Record コンテキストの既存パターンとの整合**: Record コンテキストには既に `RecordViewerTable`（ユーザー x Record の関連）が存在する。`ReadStatusTable` も同様の構造であり、同一コンテキスト内で自然に共存できる

---

## 6. データモデル

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
- `UNIQUE(record_id, user_id)` — ユーザー x Record の組み合わせは一意
- `FK record_id → records.id ON DELETE CASCADE` — Record 削除時に連動削除
- `FK user_id → users.id ON DELETE CASCADE` — ユーザー削除時に連動削除

#### `records` テーブルへの追加カラム

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| `content_updated_at` | DATETIME(6) | NOT NULL | コンテンツ最終更新日時（公開日時 or 最新コメント日時） |

- 公開時に `content_updated_at = published_at` で初期化
- コメント追加時に `content_updated_at = comment.created_at` で更新

### インデックス戦略

```sql
-- 未読一覧取得の主要クエリ用
CREATE INDEX idx_record_read_statuses_user_id ON record_read_statuses (user_id);

-- ユーザー x Record の一意制約（UNIQUE制約がインデックスを兼ねる）
-- uq_record_read_statuses_record_id_user_id

-- Record 単位の閲覧状態取得用（UNIQUE制約でカバー）
-- record_id での検索は UNIQUE 制約のインデックスで対応
```

主要クエリパターン:

```sql
-- 未読記録一覧（ダッシュボード）
SELECT r.*
FROM records r
JOIN record_viewers rv ON rv.record_id = r.id  -- Viewer として閲覧権限あり
LEFT JOIN record_read_statuses rs
  ON rs.record_id = r.id AND rs.user_id = :user_id
WHERE r.status = 'published'
  AND (
    r.organizer_id = :user_id
    OR r.counterpart_id = :user_id
    OR rv.user_id = :user_id
  )
  AND (
    rs.id IS NULL  -- 一度も閲覧していない
    OR rs.last_viewed_at < r.content_updated_at  -- 閲覧後にコンテンツが更新された
  )
ORDER BY r.content_updated_at DESC;

-- 閲覧時の ReadStatus 更新（UPSERT）
INSERT INTO record_read_statuses (id, record_id, user_id, last_viewed_at, created_at, updated_at)
VALUES (:id, :record_id, :user_id, :now, :now, :now)
ON DUPLICATE KEY UPDATE last_viewed_at = :now, updated_at = :now;
```

### パフォーマンス考慮

- **データ量見積もり**: ユーザー数 x 閲覧済み Record 数。初期想定では数千〜数万行程度（1on1管理ツールの規模）
- **未閲覧の Record は行が存在しない**: `LEFT JOIN` + `IS NULL` で未読判定するため、閲覧していない Record のぶんの行は不要。データ量はユーザーが実際に閲覧した Record 数に比例する
- **UPSERT パターン**: `ON DUPLICATE KEY UPDATE` で挿入と更新を一文で処理。閲覧のたびに `last_viewed_at` を更新するだけなので書き込み負荷は低い

---

## 7. ドメインモデル設計

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
# Record に content_updated_at を追加
class Record:
    # 既存フィールド...
    _content_updated_at: datetime | None  # 公開前は None

    @property
    def content_updated_at(self) -> datetime | None:
        return self._content_updated_at

    def publish(self, *, actor_id: UserId, now: datetime) -> None:
        # 既存の処理...
        self._content_updated_at = now  # 追加

    def notify_comment_added(self, now: datetime) -> None:
        """コメント追加時にコンテンツ更新日時を更新する。"""
        self._content_updated_at = now
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
```

### 値オブジェクト

```python
# domain/value_objects.py に追加
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

## 8. ユースケース

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

このユースケースはフロントエンドが Record 詳細画面を表示する際に呼び出す。`GET /records/{id}` のレスポンスを返すと同時にバックグラウンドで既読マークを行う、または `POST /records/{id}/viewed` を別途呼び出す設計が考えられる。

**推奨**: `POST /records/{id}/viewed` を明示的に呼び出す方式。GET リクエストに副作用（既読マーク）を持たせるのは RESTful でなく、キャッシュやプリフェッチで意図しない既読が発生するリスクがある。

### 未読記録一覧の取得

```
ListUnreadRecords
  Input: user_id
  Output: 未読の Record 一覧（content_updated_at の降順）
  処理:
    1. user_id が閲覧権限を持つ公開済み Record のうち、
       ReadStatus が存在しない OR last_viewed_at < content_updated_at のものを取得
```

---

## 9. API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `POST` | `/records/{record_id}/viewed` | Record を閲覧済みにする |
| `GET` | `/records/unread` | 未読記録一覧を取得（ダッシュボード用） |

---

## 10. イベントフローまとめ

```
RecordPublished
  → Record.content_updated_at = published_at（Record コンテキスト内）
  → Notification 送信（Notification コンテキスト — 既存の RecordPublishedHandler）
  → カウンターパート・Viewer にとって「未読記録」になる

RecordCommentAdded
  → Record.notify_comment_added(now)（Record コンテキスト内、ユースケースで直接呼び出し）
  → Record.content_updated_at = comment.created_at
  → コメント投稿者以外にとって「未読記録」に戻る
  → Notification 送信（Notification コンテキスト — 既存の RecordCommentAddedHandler）

ユーザーが Record 詳細画面を開く
  → POST /records/{record_id}/viewed
  → ReadStatus.last_viewed_at = now
  → 「未読記録」から消える
```

---

## 11. 実装 Issue（後続）

本設計に基づき、以下の実装 Issue を作成する:

1. **Record エンティティに `content_updated_at` を追加** — ドメインモデル変更 + マイグレーション
2. **ReadStatus ドメインモデル・リポジトリ実装** — エンティティ、テーブル、リポジトリ
3. **既読マークユースケース** — `MarkRecordAsViewed` ユースケース + `POST /records/{id}/viewed` API
4. **未読記録一覧ユースケース** — `ListUnreadRecords` ユースケース + `GET /records/unread` API
5. **コメント追加時の `content_updated_at` 更新** — 既存の `AddComment` ユースケースに `notify_comment_added()` 呼び出しを追加
