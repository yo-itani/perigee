import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="mt-2 text-muted-foreground">Page not found</p>
      <Link to="/" className="mt-4 text-sm text-primary underline">
        Back to Dashboard
      </Link>
    </div>
  );
}
