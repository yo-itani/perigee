---
name: dev-cycle
description: Issue の実装→PRレビュー→修正のサイクルを自動実行し、レビュー通過まで繰り返す。
argument-hint: <Issue番号>
disable-model-invocation: true
allowed-tools: Task(implementer, reviewer), Bash(gh *), Read, AskUserQuestion
---

# Dev Cycle スキル

Issue の実装から PR レビュー通過まで、`implementer` と `reviewer` の2つの subagent で自動実行する。

## アーキテクチャ

```
Orchestrator (このスキル / メインの Claude)
  │
  ├─ implementer (persistent subagent)
  │    ├─ 初回: Issue を実装して PR 作成
  │    └─ resume: レビュー指摘を修正
  │
  └─ reviewer (persistent subagent)
       ├─ 初回: PR をレビュー
       └─ resume: 修正後の差分を再レビュー
```

## フロー

```
Phase 1: implementer 起動 → 実装 → PR 作成 (agent_id 保存)
Phase 2: reviewer 起動 → レビュー → PASS / FAIL (agent_id 保存)
  ├─ PASS → Phase 5: 完了
  └─ FAIL → Phase 3: implementer を resume → 修正
             → Phase 4: reviewer を resume → 再レビュー
             → (最大3回ループ)
```

## 手順

### Phase 1: 実装

Task ツールで implementer を起動する。

```
Task(
  subagent_type: "implementer",
  description: "Implement issue #$ARGUMENTS",
  prompt: "Issue #$ARGUMENTS を実装して PR を作成してください。"
)
```

結果から:
- **agent_id** を保存する（以降の resume に使用）
- **PR_NUMBER** を抽出する

PR 番号が取得できない場合は `gh pr list --head feature/$ARGUMENTS` で探す。

### Phase 2: レビュー

**初回**: Task ツールで reviewer を新規起動する。

```
Task(
  subagent_type: "reviewer",
  description: "Review PR #<PR番号>",
  prompt: "PR #<PR番号> をレビューしてください。"
)
```

**2回目以降**: reviewer の agent_id で resume する。

```
Task(
  resume: <reviewer の agent_id>,
  prompt: "修正がプッシュされました。PR #<PR番号> を再レビューしてください。"
)
```

初回は agent_id を保存する。

### Phase 3: 判定

レビュー結果の `REVIEW_RESULT:` を確認:

- **PASS** → Phase 5 へ
- **FAIL** → Phase 4 へ
- ループ上限（3回）到達 → ユーザーに残りの指摘を提示して手動対応を依頼

各ループの結果をユーザーに簡潔に報告する（例:「レビュー 1/3: FAIL — 必須修正 2件」）。

### Phase 4: 修正

implementer の agent_id で resume する。

```
Task(
  resume: <implementer の agent_id>,
  prompt: "Reviewer から以下の指摘を受けました。修正してください。\n\n<指摘事項セクションを貼り付ける>"
)
```

修正完了後、Phase 2（reviewer を resume）に戻る。

### Phase 5: 完了

ユーザーに報告:
- PR URL
- レビューサイクル回数
- 最終レビュー結果の要約

## ループ制限

修正サイクルは **最大 3 回**。超過時はユーザーに手動対応を依頼する。
