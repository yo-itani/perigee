import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface InviteLinkModalProps {
  link: string;
  onClose: () => void;
}

export function InviteLinkModal({ link, onClose }: InviteLinkModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>招待リンク</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            以下のリンクをユーザーに共有してください。リンクの有効期限は72時間です。
          </p>
          <div className="flex gap-2">
            <Input value={link} readOnly className="font-mono text-xs" />
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleCopy()}
              className="shrink-0"
            >
              {copied ? "コピー済み" : "コピー"}
            </Button>
          </div>
          <div className="flex justify-end">
            <Button variant="ghost" onClick={onClose}>
              閉じる
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
