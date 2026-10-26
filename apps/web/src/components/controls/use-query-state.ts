"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useTransition } from "react";

/** Keeps view state in the URL so every view is shareable and server-rendered. */
export function useQueryState() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [pending, startTransition] = useTransition();

  const set = useCallback(
    (updates: Record<string, string>) => {
      const next = new URLSearchParams(searchParams);
      for (const [key, value] of Object.entries(updates)) next.set(key, value);
      startTransition(() => router.replace(`${pathname}?${next}`, { scroll: false }));
    },
    [pathname, router, searchParams],
  );

  return { set, pending };
}
