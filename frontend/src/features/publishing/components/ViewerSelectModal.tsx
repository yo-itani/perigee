import { useState } from "react";
import { Button } from "@/components/ui/button";

interface ViewerSelectModalProps {
  isOpen: boolean;
  onClose: () => void;
  suggestedViewerIds: string[];
  counterpartId: string;
  onPublish: (viewerIds: string[]) => void;
  onSaveDraft: (viewerIds: string[]) => void;
  isPublishing: boolean;
  isSavingDraft: boolean;
  publishError: string | null;
  saveDraftError: string | null;
}

/**
 * Inner modal content, remounted each time the modal opens via key prop.
 * This ensures state is reset on each open without useEffect.
 */
function ViewerSelectModalContent({
  onClose,
  suggestedViewerIds,
  counterpartId,
  onPublish,
  onSaveDraft,
  isPublishing,
  isSavingDraft,
  publishError,
  saveDraftError,
}: Omit<ViewerSelectModalProps, "isOpen">) {
  const [selectedViewerIds, setSelectedViewerIds] = useState<Set<string>>(
    () => new Set(suggestedViewerIds),
  );
  const [timing, setTiming] = useState<"now" | "draft">("now");

  const toggleViewer = (viewerId: string) => {
    setSelectedViewerIds((prev) => {
      const next = new Set(prev);
      if (next.has(viewerId)) {
        next.delete(viewerId);
      } else {
        next.add(viewerId);
      }
      return next;
    });
  };

  // Additional viewers are suggested viewers excluding the counterpart
  const additionalViewerIds = suggestedViewerIds.filter(
    (id) => id !== counterpartId,
  );

  const handleConfirm = () => {
    // Counterpart is always included
    const allViewerIds = [counterpartId, ...selectedViewerIds];
    // Deduplicate
    const uniqueViewerIds = [...new Set(allViewerIds)];

    if (timing === "now") {
      onPublish(uniqueViewerIds);
    } else {
      onSaveDraft(uniqueViewerIds);
    }
  };

  const isBusy = isPublishing || isSavingDraft;
  const error = publishError ?? saveDraftError;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-label="公開設定"
    >
      <div className="w-full max-w-md rounded-xl bg-background p-6 shadow-lg">
        <h2 className="text-lg font-semibold">公開設定</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          この1on1の記録を共有する相手を選んでください。カウンターパートには常に公開されます。
        </p>

        {/* Additional viewers */}
        {additionalViewerIds.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-sm font-medium">追加で共有する相手</p>
            <div className="space-y-2">
              {additionalViewerIds.map((viewerId) => (
                <label
                  key={viewerId}
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 transition-colors ${
                    selectedViewerIds.has(viewerId)
                      ? "border-primary bg-primary/5"
                      : "border-border"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedViewerIds.has(viewerId)}
                    onChange={() => toggleViewer(viewerId)}
                    className="h-4 w-4"
                    aria-label={`${viewerId}を選択`}
                  />
                  <span className="text-sm">{viewerId}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Timing selection */}
        <div className="mt-4 border-t pt-4">
          <p className="mb-2 text-sm font-medium">公開タイミング</p>
          <div className="space-y-2">
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 transition-colors ${
                timing === "now"
                  ? "border-primary bg-primary/5"
                  : "border-border"
              }`}
            >
              <input
                type="radio"
                name="publish-timing"
                value="now"
                checked={timing === "now"}
                onChange={() => setTiming("now")}
                className="h-4 w-4"
              />
              <div>
                <p className="text-sm font-medium">今すぐ公開</p>
                <p className="text-xs text-muted-foreground">
                  保存と同時にSlackで通知されます
                </p>
              </div>
            </label>
            <label
              className={`flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 transition-colors ${
                timing === "draft"
                  ? "border-primary bg-primary/5"
                  : "border-border"
              }`}
            >
              <input
                type="radio"
                name="publish-timing"
                value="draft"
                checked={timing === "draft"}
                onChange={() => setTiming("draft")}
                className="h-4 w-4"
              />
              <div>
                <p className="text-sm font-medium">
                  下書きとして保存（後で公開）
                </p>
                <p className="text-xs text-muted-foreground">
                  記録は保存されますが通知は送られません
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Error display */}
        {error && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={isBusy}>
            キャンセル
          </Button>
          <Button onClick={handleConfirm} disabled={isBusy}>
            {isBusy
              ? "処理中..."
              : timing === "now"
                ? "公開する"
                : "下書き保存"}
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Wrapper that conditionally renders the modal content.
 * Uses key={openCount} to remount and reset state each time the modal opens.
 */
export function ViewerSelectModal(props: ViewerSelectModalProps) {
  if (!props.isOpen) return null;

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { isOpen: _, ...rest } = props;
  return <ViewerSelectModalContent {...rest} />;
}
