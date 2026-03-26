# コーディング規約

## バックエンド

### アプリケーション層の命名規則

| 分類 | クラス名 | ファイル名 | 例 |
|---|---|---|---|
| コマンド（状態変更） | `*UseCase` | `*_use_case.py` | `CreateScheduleUseCase` |
| クエリ（読み取り専用） | `*QueryService` | `*_query_service.py` | `GetTemplateQueryService` |

- **UseCase**: 状態変更を伴うアプリケーション操作は `*UseCase`（UoW やイベント発行の有無は結果であり、判定基準ではない）
- **QueryService**: リポジトリから読み取るだけで状態を変更しないものは `*QueryService`
- `*_usecase.py` は採用しない（`*_use_case.py` に統一）
- 既存の動詞ベースファイル名（例: `get_captains_for_user.py`）はそのまま維持し、クラス名のみリネーム

### ORM / テーブル命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| ORM クラス名 | `XxxTable` | `WorkspaceTable`, `MembershipTable` |
| テーブル名 | スネークケース複数形 | `workspaces`, `confirmation_requests` |
| FK 制約名 | `fk_{テーブル名}_{カラム名}` | `fk_schedules_organizer_id` |
| UQ 制約名 | `uq_{テーブル名}_{カラム群}` | `uq_memberships_workspace_user` |

### リポジトリ命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| インターフェース | `XxxRepository` | `WorkspaceRepository` |
| SQLAlchemy 実装 | `SqlAlchemyXxxRepository` | `SqlAlchemyWorkspaceRepository` |

### ユースケースの Input / Output DTO

- ユースケースの入出力には `@dataclass(frozen=True)` の DTO を使用する
- DTO はユースケースクラスと同一ファイルに定義する（別ファイルに分離しない）
- 命名規則: `<ユースケース名>Input` / `<ユースケース名>Output`
- presentation 層（FastAPI の Pydantic スキーマ）とは分離し、ルーターで変換する

### DDD レイヤー依存ルール

- **ユースケース・ルーター・認証依存で、インフラ層の具象実装（`SqlAlchemy*Repository` 等）を直接 import してはいけない**
- 具象実装への依存は `dependencies.py`（DI プロバイダー）に集約し、`Depends` 経由で抽象インターフェースとして注入する
- 関数内 import で具象実装を使うのも NG（循環回避が理由でも、DI プロバイダーに移す）
- 例外: `event_setup.py` / `lifespan.py`（リクエスト外コンテキスト、`docs/architecture.md` に記載済み）、テストコード

### datetime の扱い

- DB セッションは `connect_args={"init_command": "SET time_zone='+00:00'"}` で UTC 固定
- `NOW()` / `CURRENT_TIMESTAMP` は常に UTC を返す
- アプリ層で datetime を生成する場合は `datetime.now(UTC)` を使用する
- 表示層で各ユーザーのタイムゾーンに変換する

### カラム規約

- UUID は `CHAR(36)` で文字列格納する
- 子エンティティのリレーション: `lazy="selectin"`（N+1 防止）+ `cascade="all, delete-orphan"`
- `ondelete` の使い分け:
  - 子→親（ライフサイクル連動）: `CASCADE`
  - 参照のみ（削除を防止）: `RESTRICT`
  - 任意参照（参照先が消えても存続）: `SET NULL`
- 順序を持つリスト（AgendaTemplate 等）は `position INTEGER NOT NULL` で順序を保持する

## フロントエンド

### カラートークン規約

#### 原則

- ハードコード色（`bg-white`, `text-[#6b6b67]`, `border-black/[0.22]` 等）は使わない
- `index.css` の `:root` / `.dark` に CSS 変数を定義し、Tailwind トークンクラス（`bg-surface`, `text-text-subtle` 等）で参照する
- **新しいカラートークンを `:root` に追加したら、必ず `.dark` にも対応値を定義する**

#### カスタムトークン一覧

| トークン | ライト | ダーク | Tailwind クラス | 用途 |
|---|---|---|---|---|
| `--surface` | `#f0efea` | `oklch(0.205 0 0)` | `bg-surface` | メインコンテンツ背景 |
| `--surface-secondary` | `#f5f5f3` | `oklch(0.269 0 0)` | `bg-surface-secondary` | アクティブメニュー、Input 背景 |
| `--surface-tertiary` | `#eeede8` | `oklch(0.235 0 0)` | `bg-surface-tertiary` | 予備 |
| `--text-subtle` | `#6b6b67` | `oklch(0.708 0 0)` | `text-text-subtle` | メニュー項目、副テキスト |
| `--text-muted` | `#9e9e9a` | `oklch(0.556 0 0)` | `text-text-muted` | グループラベル、プレースホルダー |
| `--border-subtle` | `rgba(0,0,0,0.12)` | `oklch(1 0 0 / 10%)` | `border-border-subtle` | サイドバー境界、Input ボーダー |

shadcn/ui 既存トークン（`--background`, `--foreground`, `--muted` 等）も引き続き使用可能。

### react-refresh 警告の回避

- コンポーネントファイル（`.tsx`）から非コンポーネント export（ユーティリティ関数、定数等）を分離する
- ユーティリティは `utils.ts`、型定義は `types.ts` に配置する
- 共通ユーティリティは `src/utils/` に配置し、feature の `utils.ts` から re-export する
