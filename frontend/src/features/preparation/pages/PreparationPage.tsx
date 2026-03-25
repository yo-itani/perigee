import { useParams } from "react-router";

export function PreparationPage() {
  const { scheduleId } = useParams<{ scheduleId: string }>();

  return (
    <div>
      <h1 className="text-2xl font-bold">Preparation</h1>
      <p className="mt-2 text-muted-foreground">Schedule ID: {scheduleId}</p>
    </div>
  );
}
