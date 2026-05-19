# KaiRA Event Reminder Slack App

KaiRA の connpass グループで本日開催されるイベントを取得し、Slack Incoming Webhook に当日リマインドを送信します。

投稿例:

```text
<!channel>
こちら本日開催です！
- イベント名: KaiRA 論文読み会
- 場所: オンライン
- connpass: https://kaira-thesis-reading.connpass.com/event/123456/
- Google Meet: https://meet.google.com/abc-defg-hij
```

connpass の公開されているイベント本文に Google Meet のリンクが含まれている場合は、投稿に `Google Meet` の行も追加します。参加者限定情報など API の本文に含まれないリンクは取得できません。

## 必要な Secrets

GitHub リポジトリの `Settings` -> `Secrets and variables` -> `Actions` に次を登録してください。

- `CONNPASS_API_KEY`: connpass API v2 の API キー
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL

## GitHub Actions

[`.github/workflows/remind-today.yml`](.github/workflows/remind-today.yml) が毎日 08:00 JST に実行されます。

当日の KaiRA イベントがない場合は Slack には何も投稿せず、Actions のログに `No KaiRA events today (...)` を出して正常終了します。

手動実行もできます。

1. GitHub の `Actions` タブを開く
2. `Remind today's KaiRA events` を選ぶ
3. `Run workflow` を押す

## ローカル実行

```bash
cp .env.example .env
uv run kaira-event-reminder --dry-run
```

`--dry-run` は Slack に投稿せず、投稿予定の内容だけを標準出力に表示します。

実際に Slack へ投稿する場合:

```bash
uv run kaira-event-reminder
```

## 設定

- `CONNPASS_SUBDOMAIN`: デフォルトは `kaira-thesis-reading`
- `TZ`: デフォルトは `Asia/Tokyo`
