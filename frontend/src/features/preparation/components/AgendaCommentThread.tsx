import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AgendaComment } from "../types";
import { formatCommentDate } from "../utils";

interface AgendaCommentThreadProps {
  comments: AgendaComment[];
  onAddComment: (body: string) => Promise<void>;
  isSubmitting: boolean;
}

export function AgendaCommentThread({
  comments,
  onAddComment,
  isSubmitting,
}: AgendaCommentThreadProps) {
  const [commentText, setCommentText] = useState("");

  const handleSubmit = async () => {
    const trimmed = commentText.trim();
    if (!trimmed) return;
    await onAddComment(trimmed);
    setCommentText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  };

  return (
    <div className="mt-2 space-y-2 border-t pt-2">
      {comments.map((comment) => (
        <div key={comment.comment_id} className="flex items-start gap-2">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium">
            {comment.author_id.slice(0, 1).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs text-muted-foreground">
              {comment.author_id.slice(0, 8)}{" "}
              {formatCommentDate(comment.created_at)}
            </div>
            <div className="text-sm">{comment.body}</div>
          </div>
        </div>
      ))}
      <div className="flex gap-2">
        <Input
          value={commentText}
          onChange={(e) => setCommentText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="コメントを追加..."
          className="flex-1"
          disabled={isSubmitting}
        />
        <Button
          variant="outline"
          size="sm"
          onClick={() => void handleSubmit()}
          disabled={isSubmitting || !commentText.trim()}
        >
          送信
        </Button>
      </div>
    </div>
  );
}
