import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RecordActionItem } from "@/features/recording/types";
import { formatDateShort } from "@/utils/date";

interface ActionItemSummaryProps {
  actionItems: RecordActionItem[];
}

export function ActionItemSummary({ actionItems }: ActionItemSummaryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>アクションアイテム</CardTitle>
      </CardHeader>
      <CardContent>
        {actionItems.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            アクションアイテムはありません
          </p>
        ) : (
          <ul className="space-y-3">
            {actionItems.map((item) => (
              <li
                key={item.action_item_id}
                className="flex items-center justify-between rounded-lg border px-4 py-3"
              >
                <span className="text-sm">{item.title}</span>
                {item.due_date && (
                  <span className="text-xs text-muted-foreground">
                    期限：{formatDateShort(item.due_date)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
