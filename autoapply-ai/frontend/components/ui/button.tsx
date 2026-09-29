import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "signature";
  size?: "xs" | "sm" | "md" | "lg";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "secondary", size = "md", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    const baseStyles =
      "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50 select-none";

    const variants = {
      primary: "bg-accent text-white hover:bg-accent-strong shadow-sm active:translate-y-[0.5px]",
      signature:
        "btn-signature font-semibold active:translate-y-[0.5px] border border-white/10",
      secondary:
        "bg-surface-2 hover:bg-surface-3 text-text-primary border border-border hover:border-border-strong",
      outline:
        "border border-border hover:border-border-strong hover:bg-surface-2 text-text-primary",
      ghost: "hover:bg-surface-2 text-text-secondary hover:text-text-primary",
      danger:
        "bg-semantic-red-dim text-semantic-red border border-semantic-red/30 hover:bg-semantic-red/20 active:translate-y-[0.5px]",
    };

    const sizes = {
      xs: "h-7 px-2.5 text-xs rounded",
      sm: "h-8 px-3 text-xs rounded-md",
      md: "h-9 px-4 text-sm rounded-md",
      lg: "h-11 px-6 text-base rounded-lg",
    };

    return (
      <Comp
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
