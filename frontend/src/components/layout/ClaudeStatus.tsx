"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function ClaudeStatus() {
  const [state, setState] = useState<{ model: string; credential: string } | "no-credentials" | "down" | null>(null);
  useEffect(() => {
    api
      .health()
      .then((h) => setState(h.credential ? { model: h.model, credential: h.credential } : "no-credentials"))
      .catch(() => setState("down"));
  }, []);
  if (state === null) return null;
  if (state === "down")
    return (
      <span
        className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700"
        title="The API isn't running. It refuses to start without Claude credentials: run `ant auth login` or set ANTHROPIC_API_KEY, then start it."
      >
        API offline
      </span>
    );
  if (state === "no-credentials")
    return (
      <span
        className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700"
        title="Claude credentials disappeared (signed out or expired). Run `ant auth login` again and restart the API."
      >
        Claude not connected
      </span>
    );
  return (
    <span
      className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700"
      title={`${state.model} via ${state.credential}`}
    >
      Claude connected
    </span>
  );
}
