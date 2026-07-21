// Standard shadcn/ui helper: merges conditional Tailwind class lists
// (clsx) then dedupes conflicting Tailwind classes (twMerge) — e.g.
// cn("px-2", isActive && "px-4") correctly ends up as just "px-4".
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
