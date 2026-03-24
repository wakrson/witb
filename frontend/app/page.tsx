"use client";

import { useState, type FormEvent } from "react";

interface SearchResult {
  ref: string;
  text: string;
  score: number;
}

const API_URL = "";

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);
    setError("");
    setResults([]);

    try {
      const res = await fetch(`/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, top_k: 5 }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error || `Request failed (${res.status})`);
      }

      const data = await res.json();
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-black">
      <main className="flex flex-col items-center gap-6 w-full max-w-2xl px-8">
        <h1 className="text-white text-4xl font-bold">witb</h1>
        <form onSubmit={handleSearch} className="w-full">
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
              disabled={loading}
            />
          </div>
        </form>

        {loading && (
          <p className="text-zinc-500 text-sm">Searching...</p>
        )}

        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}

        {results.length > 0 && (
          <div className="flex flex-col gap-4 w-full">
            {results.map((r, i) => (
              <div
                key={i}
                className="rounded-xl border border-zinc-800 bg-zinc-900 px-6 py-4"
              >
                <div className="flex items-center justify-between mb-1">
                  <p className="text-zinc-400 text-sm font-medium">
                    {r.ref}
                  </p>
                  <p className="text-zinc-500 text-xs">
                    {r.score.toFixed(2)}
                  </p>
                </div>
                <p className="text-white text-base leading-relaxed">
                  {r.text}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}