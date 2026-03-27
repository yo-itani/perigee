import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const avatarCircleVariants = cva(
  "inline-flex shrink-0 items-center justify-center rounded-full font-medium",
  {
    variants: {
      variant: {
        info: "bg-info-bg text-info-text",
        warn: "bg-warning-bg text-warning-text",
        success: "bg-success-bg text-success-text",
      },
      size: {
        default: "size-7 text-xs",
        lg: "size-8 text-sm",
      },
    },
    defaultVariants: {
      variant: "info",
      size: "default",
    },
  },
);

export type AvatarCircleProps = React.ComponentProps<"span"> &
  VariantProps<typeof avatarCircleVariants> & {
    initials: string;
  };

function AvatarCircle({
  className,
  variant = "info",
  size = "default",
  initials,
  ...props
}: AvatarCircleProps) {
  return (
    <span
      data-slot="avatar-circle"
      className={cn(avatarCircleVariants({ variant, size, className }))}
      {...props}
    >
      {initials}
    </span>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export { AvatarCircle, avatarCircleVariants };
