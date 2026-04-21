"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  mono?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, mono, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-[34px] w-full bg-surface border border-border rounded-sm px-[10px] text-body text-text",
        "placeholder:text-text-mute",
        "focus-visible:border-accent focus-visible:outline-none",
        "disabled:bg-surface-2 disabled:text-text-mute",
        mono && "font-mono text-mono",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement> & { mono?: boolean }
>(({ className, mono, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full bg-surface border border-border rounded-sm px-[10px] py-[8px] text-body text-text",
      "placeholder:text-text-mute resize-y",
      "focus-visible:border-accent focus-visible:outline-none",
      mono && "font-mono text-mono",
      className
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export const Label = React.forwardRef<
  HTMLLabelElement,
  React.LabelHTMLAttributes<HTMLLabelElement>
>(({ className, ...props }, ref) => (
  <label
    ref={ref}
    className={cn("overline block mb-[6px]", className)}
    {...props}
  />
));
Label.displayName = "Label";
