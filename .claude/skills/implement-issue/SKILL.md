---
name: implement-issue
description: 指定された Issue を読み込み、feature ブランチ作成から実装・テスト・PR 作成までを一気通貫で行う。
argument-hint: <Issue番号>
disable-model-invocation: true
allowed-tools: Bash(gh *), Bash(git *), Bash(uv *), Bash(pnpm *), Bash(ruff *), Bash(pyright *), Read, Write, Edit, Grep, Glob, mcp__serena__get_symbols_overview, mcp__serena__find_symbol, mcp__serena__find_referencing_symbols, mcp__serena__search_for_pattern, mcp__serena__list_dir, mcp__serena__find_file, mcp__serena__replace_symbol_body, mcp__serena__insert_after_symbol, mcp__serena__insert_before_symbol, mcp__serena__rename_symbol
---

# Issue 実装スキル

指定された GitHub Issue の実装を、ブランチ作成から PR 作成まで一気通貫で行う。

**アーキテクチャを必ず確認すること**: 作業開始前に `docs/architecture.md` を読み、プロジェクトの規約に従う。

## 手順

### 1. アーキテクチャの確認

`docs/architecture.md` を読み、以下を把握する:
- DDD レイヤー構成（domain / application / infrastructure / presentation）
- ディレクトリ構成（`backend/contexts/` 配下の境界コンテキスト）
- レイヤー間の依存ルール

### 2. Issue の取得

`gh issue view $ARGUMENTS` で Issue 内容を取得する。以下を読み取る:
- 概要・背景
- 完了条件
- 技術メモ

### 3. コードベースの調査

Issue の内容をもとにコードベースを調査し、以下を把握する:
- 変更対象のファイル・モジュール
- 既存の設計パターンとの整合性
- テストの書き方（既存テストを参考にする）

### 4. 実装方針の提示と承認

**コード変更を行う前に、必ず以下をユーザーに提示して承認を得る:**

```markdown
## 実装方針: #<Issue番号> <タイトル>

### 変更内容
- 新規作成するファイル
- 変更するファイルと変更内容の概要

### 設計判断
- 採用するアプローチとその理由

### テスト計画
- 追加するテストの概要
```

**ユーザーの承認なしに実装を開始しないこと。**

### 5. feature ブランチの作成

```bash
git checkout develop
git pull origin develop
git checkout -b feature/$ARGUMENTS-<説明>
```

ブランチ名の `<説明>` 部分は Issue のタイトルから簡潔に命名する（英語、kebab-case）。

### 6. 実装

アーキテクチャ設計に従って実装する。特に以下を遵守:

#### Python（バックエンド）
- **命名規約**: 変数・関数・モジュールは `snake_case`、クラスは `PascalCase`、定数は `UPPER_SNAKE_CASE`
- **型ヒント**: すべての関数の引数・戻り値に型ヒントを付ける
- **コメント**: 「何をしているか」は書かない。「なぜそうしたか」が伝わりにくい箇所にだけ書く
- **ドメイン層**: 純粋な Python で書く。FastAPI・SQLAlchemy 等のフレームワーク依存なし
- **ドメイン例外**: ビジネスルール違反には `ValueError` / `PermissionError` ではなくドメイン固有の例外クラスを使う（例: `RecordAlreadyPublishedError`）。コンテキストの `domain/exceptions.py` に配置する
- **フィールドのカプセル化**: 状態遷移や不変条件を持つフィールド、およびドメインメソッド経由でのみ変更すべきフィールドは `_` プレフィックス + read-only `@property` で公開し、直接代入を防ぐ
- **値オブジェクトの配置**: ID型・Enumは `domain/value_objects.py` にまとめる。ドメイン固有のバリデーションを持つ値オブジェクト（`Topic`, `CommentBody` 等）は `domain/<vo_name>.py` として個別ファイルに切り出す
- **ドメインイベント管理**: イベントは `_events` リストに蓄積し、`collect_events()` メソッドで取得＆クリアする
- **datetime の扱い**: ファクトリメソッド（`create()`）では `now: datetime | None = None` で `datetime.now(UTC)` フォールバック可。操作メソッドでは `now: datetime` を必須引数にする

#### TypeScript（フロントエンド）
- **命名規約**: 変数・関数は `camelCase`、コンポーネント・型は `PascalCase`、定数は `UPPER_SNAKE_CASE`
- **型**: `any` の使用は禁止。適切な型を定義する
- **コンポーネント**: 関数コンポーネントで記述

### 7. 静的解析・型チェック

#### バックエンド
```bash
ruff check .
ruff format --check .
pyright
```

#### フロントエンド
```bash
pnpm lint
```

警告がある場合は修正する。やむを得ない場合のみ抑制コメント + 理由を記述。

### 8. テスト実行

#### バックエンド
```bash
uv run pytest
```

- 新機能にはテストを追加する
- ドメイン層を中心にテストする（DB不要、純粋Python）
- API層のテストはテスト用MariaDBコンテナで実行
- 既存テストが壊れていないことを確認する

#### フロントエンド
```bash
pnpm test
```

- コンポーネント単位のテスト（Vitest + Testing Library）

### 9. 機密情報チェック

**コミット前に、ステージング対象のファイルに機密情報が含まれていないことを確認する。**

チェック対象:
- パスワード、API キー、トークン、シークレットのハードコード
- `.env` ファイルや認証情報ファイル（`credentials.json` 等）の混入
- DSN・接続文字列中の認証情報
- 秘密鍵ファイル（`*.pem`, `*.key` 等）

確認手順:
1. `git diff --cached` でステージング済みの差分を確認する
2. 以下のパターンを差分内で検索する:
   ```bash
   git diff --cached | grep -iE '(password|passwd|secret|api_key|apikey|token|credential|private_key|auth)' || true
   ```
3. マッチがあった場合は、それが実際の機密値か変数名・プレースホルダかを判断する
4. 実際の機密値が含まれている場合は **コミットを中止** し、該当箇所を環境変数参照に置き換える

**機密情報が含まれている場合は絶対にコミットしない。**

### 10. コミット・プッシュ

静的解析 / テスト / 機密情報チェック がすべて通ることを確認してからコミットする。

```bash
git add <変更ファイル>
git commit -m "<適切なコミットメッセージ>"
git push -u origin feature/$ARGUMENTS-<説明>
```

### 11. PR 作成

`gh pr create` で `develop` ブランチ向けに PR を作成する。PRは日本語で書くこと。

PR 本文には以下を含める:
- 変更内容の要約
- `Closes #$ARGUMENTS`（Issue の自動クローズ）
- テスト結果の概要

**ヒアドキュメントは `--body-file -` で渡す（`cat` 等を使わない）:**

```bash
gh pr create --base develop --title "<タイトル>" --body-file - <<'EOF'
## 変更内容
...

Closes #$ARGUMENTS
EOF
```

### 12. 完了報告

作成した PR の URL をユーザーに報告する。

## 重要なルール

- **方針承認前にコード変更を行わない**
- **コミット前に機密情報チェックを行う（パスワード、API キー、トークン等のハードコードがないこと）**
- **静的解析 / テスト / 機密情報チェック が全て通ることを確認してからコミット**
- **PR 本文に `Closes #<issue番号>` を含める**
- **`.env` をコミットしない**
- ワーニングは握りつぶさない
