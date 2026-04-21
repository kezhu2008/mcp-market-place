"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-[6px] font-medium transition-colors duration-75 disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap rounded-sm focus-visible:outline-none",
  {
    variants: {
      variant: {
        accent: "bg-accent text-white border border-accent hover:bg-[#0fa978]",
        primary: "bg-text text-surface border border-text hover:bg-stone-800",
        secondary: "bg-surface text-text border border-border hover:bg-surface-2 hover:border-border-strong",
        ghost: "bg-transparent text-text-dim hover:bg-surface-2",
        danger: "bg-surface text-red border border-border hover:bg-[#ef444408] hover:border-[#ef444444]",
      },
      size: {
        sm: "h-[26px] px-[10px] text-body-sm",
        md: "h-[32px] px-[12px] text-body",
        lg: "h-[38px] px-[16px] text-[14px]",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
);
Button.displayName = "Button";

export { buttonVariants };
