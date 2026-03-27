import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const statusBarVariants = cva(
  "flex items-center gap-2 rounded-lg px-3.5 py-2.5 text-sm",
  {
    variants: {
      variant: {
        info: "bg-info-bg text-info-text",
        success: "bg-success-bg text-success-text",
      },
    },
    defaultVariants: {
      variant: "info",
    },
  },
);

export type StatusBarProps = React.ComponentProps<"div"> &
  VariantProps<typeof statusBarVariants>;

function StatusBar({
  className,
  variant = "info",
  children,
  ...props
}: StatusBarProps) {
  return (
    <div
      data-slot="status-bar"
      className={cn(statusBarVariants({ variant, className }))}
      {...props}
    >
      <span className="size-2 shrink-0 rounded-full bg-current" />
      {children}
    </div>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export { StatusBar, statusBarVariants };
