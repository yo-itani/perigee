import { useParams } from "react-router";

export function RecordingPage() {
  const { recordId } = useParams<{ recordId: string }>();

  return (
    <div>
      <h1 className="text-2xl font-bold">Recording</h1>
      <p className="mt-2 text-muted-foreground">Record ID: {recordId}</p>
    </div>
  );
}
