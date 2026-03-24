---
name: review-pr
description: 指定された PR の差分を分析し、開発ルールへの準拠・コード品質・テストカバレッジを確認して GitHub にレビューコメントを投稿する。
argument-hint: <PR番号 または URL>
disable-model-invocation: true
allowed-tools: Bash(gh *), Read, Grep, Glob, mcp__serena__get_symbols_overview, mcp__serena__find_symbol, mcp__serena__find_referencing_symbols, mcp__serena__search_for_pattern, mcp__serena__list_dir, mcp__serena__find_file
---

# PR レビュースキル

指定された Pull Request の差分を分析し、開発ルールへの準拠・コード品質・テストカバレッジを確認してレビューを行う。

## 手順

### 1. PR 情報の取得

```bash
gh pr view $ARGUMENTS
gh pr diff $ARGUMENTS
```

以下を把握する:
- PR のタイトル・本文
- 変更されたファイル一覧
- 差分の内容
- 関連する Issue（本文中の `Closes #xxx` / `Fixes #xxx`）

### 2. 関連 Issue の確認

PR 本文に Issue リンクがある場合、`gh issue view` で Issue の完了条件を取得する。
これをレビューの基準として使用する。

### 3. コードベースの調査

差分だけでなく、変更されたファイルの前後のコンテキストを確認する:
- 変更されたモジュールの全体構造を把握する
- 変更が他のモジュールに与える影響を調査する
- 既存の設計パターンとの整合性を確認する

### 4. レビュー観点

以下の観点で差分をレビューする:

#### DDD / アーキテクチャ準拠
- **レイヤー依存**: domain層がinfrastructure/presentation層に依存していないか
- **コンテキスト境界**: 他の境界コンテキストのドメインオブジェクトを直接参照していないか（ID参照のみ許可）
- **ドメイン層**: 純粋な Python で書かれているか（FastAPI・SQLAlchemy 等のフレームワーク依存なし）
- **配置**: ファイルが適切なコンテキスト・レイヤーに配置されているか
- **ユースケース DTO**: Input / Output DTO が `@dataclass(frozen=True)` でユースケースファイルに同居しているか。引数を直接受け取るスタイルになっていないか
- **例外の配置**: ドメイン例外が `domain/exceptions.py` に、アプリケーション例外（リソース未検出等）がユースケースファイルに配置されているか

#### Python コード品質
- **型ヒント**: 関数の引数・戻り値に型ヒントが付いているか
- **命名規約**: 変数・関数は `snake_case`、クラスは `PascalCase`、定数は `UPPER_SNAKE_CASE`
- **不要な `# type: ignore`** や **`noqa`** がないか
- ロジックの正しさ、エッジケースの考慮

#### TypeScript コード品質
- **型安全**: `any` が使われていないか。適切な型が定義されているか
- **命名規約**: 変数・関数は `camelCase`、コンポーネント・型は `PascalCase`
- **コンポーネント設計**: 適切な粒度で分割されているか

#### テスト
- 変更に対するテストが追加されているか
- バックエンド: ドメイン層のユニットテスト、API層のインテグレーションテスト
- フロントエンド: コンポーネントテスト（Vitest + Testing Library）
- 既存テストが壊れていないか

#### セキュリティ
- OWASP Top 10 等の脆弱性がないか（SQLインジェクション、XSS等）
- `.env` やシークレットがコミットされていないか
- 入力値のバリデーションが適切か（特にAPI層）
- 認証・権限チェックが適切か

#### Issue との整合性
- PR が Issue の完了条件を満たしているか
- スコープ外の変更が含まれていないか

### 5. レビュー結果のプレビュー

レビュー結果を以下のフォーマットでユーザーに提示する:

```markdown
## PR レビュー: #<PR番号> <タイトル>

### 総評
全体的な評価（問題なし / 軽微な指摘あり / 要修正）。

### 指摘事項
各指摘について:
- **ファイル**: `path/to/file`
- **行**: L42-L50
- **種別**: [必須修正 / 提案 / 質問]
- **内容**: 具体的な指摘内容

### Good Points
良い点があれば記載する。
```

**ユーザーの承認なしに GitHub にレビューを投稿しない。**

### 6. GitHub へのレビュー投稿

ユーザーの承認後、`gh pr review` でレビューを投稿する。

- **問題なし or 軽微な指摘のみ**: `gh pr review $ARGUMENTS --comment --body "<レビュー内容>"`
- **要修正**: `gh pr review $ARGUMENTS --request-changes --body "<レビュー内容>"`
- **`--approve` は使用しない**（自身の PR には使えないため）

個別のファイル・行へのコメントがある場合は、`gh api` を使用してインラインコメントを投稿する:

```bash
gh api repos/{owner}/{repo}/pulls/<PR番号>/comments \
  -f body="<コメント>" \
  -f path="<ファイルパス>" \
  -F line=<行番号> \
  -f side="RIGHT" \
  -f commit_id="$(gh pr view $ARGUMENTS --json headRefOid -q .headRefOid)"
```

## 注意事項

- レビューは日本語で投稿すること。
- レビューは建設的なトーンで記述する。問題を指摘するだけでなく、改善案を提示する。
- 些末なスタイルの指摘は控え、実質的な問題に焦点を当てる（スタイルは `ruff` / `eslint` に任せる）。
- 不明な点は断定せず質問形式で指摘する。
