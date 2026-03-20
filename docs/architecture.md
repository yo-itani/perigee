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
    identity/              # ユーザー・上司部下ペア管理（初期は固定データ）
    scheduling/            # 定期・アドホック1on1のスケジューリング
    preparation/           # 1on1前のアジェンダ・コメント準備
    recording/             # 1on1実施中のメモ・アクションアイテム記録
    publication/           # 記録の公開・公開先管理
    notification/          # Slack通知
  platform/                # 技術基盤（ドメイン非依存）
    db/                    # DB接続・セッション管理
    auth/                  # 認証ミドルウェア
    config/                # 環境設定
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
| infrastructure | DBアクセス、外部API呼び出し、リポジトリ実装 | domain, platform |
| presentation | HTTPリクエスト/レスポンス、バリデーション、ルーティング | application |

- **domain層は他のどの層にも依存しない**（テスト容易性の根幹）
- infrastructure層はdomain層のリポジトリインターフェースを実装する（依存性逆転）

## 境界コンテキストの対応

`docs/system_design.md` のドメイン設計との対応：

| コンテキスト | system_design上の対応 |
|---|---|
| identity | アクター（上司・部下・閲覧者）、設定の一部 |
| scheduling | スケジューリング |
| preparation | 準備（1on1前） |
| recording | 実施・記録（1on1中〜直後）、フォローアップ |
| publication | 公開管理 |
| notification | 通知（Slack） |

## コンテキスト間連携

- コンテキスト間はドメインイベントで連携する（例：「記録が公開された」→ notification が Slack通知を送信）
- 他コンテキストのエンティティを直接importしない。参照が必要な場合はIDで参照する
