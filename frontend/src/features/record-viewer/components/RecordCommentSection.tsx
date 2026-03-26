import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { RecordComment } from "../types";
import { formatCommentDate } from "../utils";

interface RecordCommentSectionProps {
  comments: RecordComment[];
  isLoading: boolean;
  error: string | null;
  onAddComment: (body: string) => Promise<boolean>;
  isSubmitting: boolean;
  addCommentError: string | null;
}

export function RecordCommentSection({
  comments,
  isLoading,
  error,
  onAddComment,
  isSubmitting,
  addCommentError,
}: RecordCommentSectionProps) {
  const [commentBody, setCommentBody] = useState("");

  const handleSubmit = async () => {
    if (!commentBody.trim()) return;
    const success = await onAddComment(commentBody);
    if (success) {
      setCommentBody("");
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>コメント</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[0, 1].map((i) => (
              <div key={i} className="animate-pulse flex gap-3">
                <div className="h-7 w-7 rounded-full bg-muted shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-32 rounded bg-muted" />
                  <div className="h-4 w-full rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>コメント</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>コメント</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Comment list */}
        {comments.length > 0 && (
          <div className="space-y-4 mb-4">
            {comments.map((comment) => (
              <div key={comment.comment_id} className="flex gap-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">
                  {comment.author_id.slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{comment.author_id}</span>
                    <span>{formatCommentDate(comment.created_at)}</span>
                  </div>
                  <div className="mt-1 text-sm whitespace-pre-line">
                    {comment.body}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Comment input */}
        <div className="border-t pt-4">
          {addCommentError && (
            <p className="text-sm text-destructive mb-2">{addCommentError}</p>
          )}
          <div className="flex gap-3 items-start">
            <textarea
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 min-h-[70px] resize-none"
              placeholder="コメントを追加..."
              value={commentBody}
              onChange={(e) => setCommentBody(e.target.value)}
            />
            <Button
              onClick={() => void handleSubmit()}
              disabled={isSubmitting || !commentBody.trim()}
              className="self-end"
            >
              {isSubmitting ? "送信中..." : "送信"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
