"use client";

import { useEffect, useState } from "react";
import { getJSON, type ApiResult } from "./api";

/**
 * Fetch a resource keyed by its URL.
 *
 * The URL is the request and the identity at once. Data is stored together with
 * the URL it came from and only returned when that URL is still the current one,
 * so a slow response for an old date can never be rendered against a newer date.
 *
 * This also removes the need to clear state inside an effect when the key
 * changes: a mismatch simply reports as loading, which avoids the cascading
 * renders that synchronously calling setState in an effect would cause.
 */
export function useResource<T>(url: string | null): {
  data: T | null;
  loading: boolean;
  error: string | null;
  status: number | null;
} {
  const [entry, setEntry] = useState<{ url: string; result: ApiResult<T> } | null>(null);

  useEffect(() => {
    if (!url) return;
    let alive = true;
    const controller = new AbortController();
    void getJSON<T>(url, { signal: controller.signal }).then(result => {
      // A superseded request resolves as "aborted"; it must not overwrite state.
      if (!alive || result.error === "aborted") return;
      setEntry({ url, result });
    });
    return () => { alive = false; controller.abort(); };
  }, [url]);

  if (!url) return { data: null, loading: false, error: null, status: null };
  const current = entry?.url === url ? entry.result : null;
  return {
    data: current?.data ?? null,
    loading: current === null,
    error: current?.error ?? null,
    status: current?.status ?? null,
  };
}
