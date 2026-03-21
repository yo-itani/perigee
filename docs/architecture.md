# アーキテクチャ設計

## 設計方針

- DDDに基づき、境界コンテキスト単位でコードを分割する
- 各コンテキストはドメイン層・アプリケーション層・インフラ層・プレゼンテーション層の4層構成
- コンテキスト間の参照はIDのみ。他コンテキストのドメインオブジェクトを直接参照しない
- ユビキタス言語は `docs/system_design.md` に定義済み。コード上の命名もこれに従う

## ディレクトリ構成

```
backend/
  scheduling/              # 定期・アドホック1on1のスケジューリング
  preparation/             # 1on1前のアジェンダ・コメント準備
  recording/               # 1on1実施中のメモ・アクションアイテム記録
  publishing/              # 記録の公開・公開先管理
  notification/            # Slack通知
  shared/                  # ドメイン共有（値オブジェクト、イベント基底クラス）
    domain/
      value_objects.py     # OneOnOneId, UserId など
      events.py            # 基底クラス
  platform/                # 技術基盤（ドメイン非依存）
    db/                    # SQLAlchemy async engine/session
    config/                # pydantic-settings
  api/
    register_routers.py    # 各コンテキストのrouterを集約・登録
  main.py                  # FastAPIエントリポイント
```

## コンテキスト内の構成

```
<context_name>/
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
| infrastructure | DBアクセス、外部API呼び出し、リポジトリ実装 | domain, platform |
| presentation | HTTPリクエスト/レスポンス、バリデーション、ルーティング | application |

- **domain層は他のどの層にも依存しない**（テスト容易性の根幹）
- infrastructure層はdomain層のリポジトリインターフェースを実装する（依存性逆転）

## 境界コンテキストの対応

`docs/system_design.md` のドメイン設計との対応：

| コンテキスト | system_design上の対応 |
|---|---|
| scheduling | スケジューリング |
| preparation | 準備（1on1前） |
| recording | 実施・記録（1on1中〜直後）、フォローアップ |
| publishing | 公開管理 |
| notification | 通知（Slack） |
| read_model | 参照（リードモデル） |
| settings | ユーザーごとの通知設定・デフォルト公開先 |

## コンテキスト間連携

- コンテキスト間はドメインイベントで連携する（例：「記録が公開された」→ notification が Slack通知を送信）
- 他コンテキストのエンティティを直接importしない。参照が必要な場合はIDで参照する
- オーガナイザー・カウンターパートの概念は各コンテキストが必要に応じてIDで参照する（専用のidentityコンテキストは設けない）
