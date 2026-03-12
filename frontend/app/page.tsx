"use client";

import { useState } from "react";

export default function Home() {
  const [query, setQuery] = useState("");

  return (
    <div className="flex min-h-screen items-center justify-center bg-black">
      <main className="flex flex-col items-center gap-4 w-full max-w-2xl px-8">
        <div className="flex w-full items-center rounded-2xl border border-zinc-700 bg-zinc-900 px-6 py-4 shadow-lg focus-within:border-zinc-400 transition-colors">
          <span className="whitespace-nowrap text-zinc-400 text-lg mr-2">
            where in the bible...
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder=""
            className="flex-1 bg-transparent text-white text-lg outline-none placeholder-zinc-600"
          />
        </div>
      </main>
    </div>
  );
}