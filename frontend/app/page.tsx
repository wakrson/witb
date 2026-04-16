"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

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
  const [dots, setDots] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  async function runSearch(q: string) {
    const trimmed = q.trim();
    if (!trimmed) {
      abortRef.current?.abort();
      setResults([]);
      setError("");
      setLoading(false);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, top_k: 3 }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error || `Request failed (${res.status})`);
      }

      const data = await res.json();
      if (!controller.signal.aborted) {
        setResults(data.results);
        setLoading(false);
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  useEffect(() => {
    const id = setTimeout(() => runSearch(query), 300);
    return () => clearTimeout(id);
  }, [query]);

  useEffect(() => {
    if (!loading) {
      setDots("");
      return;
    }
    const frames = ["", ".", "..", "..."];
    let i = 0;
    const id = setInterval(() => {
      i = (i + 1) % frames.length;
      setDots(frames[i]);
    }, 400);
    return () => clearInterval(id);
  }, [loading]);

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    runSearch(query);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-black">
      <main className="flex flex-col items-center gap-6 w-full max-w-2xl px-4 sm:px-8">
        <p className="text-zinc-500 text-sm tracking-widest">witb</p>
        <form onSubmit={handleSearch} className="w-full">
          <div className="flex w-full items-center rounded-2xl border border-zinc-700 bg-zinc-900 px-4 py-3 sm:px-6 sm:py-4 shadow-lg focus-within:border-zinc-400 transition-colors">
            <span className="whitespace-nowrap text-zinc-400 text-base sm:text-lg mr-2">
              where in the bible...
            </span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder=""
              autoFocus
              className="flex-1 min-w-0 bg-transparent text-white text-base sm:text-lg outline-none placeholder-zinc-600"
            />
          </div>
        </form>
        {results.length === 0 && !loading && !error && (
          <div className="flex flex-col items-center gap-1 text-zinc-600 text-sm">
            <p>try: "does it talk about forgiveness"</p>
            <p>try: "is there anything about dealing with anxiety"</p>
            <p>try: "are husbands and wives discussed"</p>
          </div>
        )}

        {loading && (
          <p className="text-zinc-500 text-sm">
            searching<span className="inline-block w-4 text-left">{dots}</span>
          </p>
        )}

        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}

        {results.length > 0 && (
          <div className="flex flex-col gap-4 w-full">
            {results.map((r, i) => (
              <div
                key={i}
                className="rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 sm:px-6 sm:py-4 hover:border-zinc-600 transition-colors cursor-default"
              >
                <p className="text-zinc-400 text-sm font-medium mb-1">
                  {r.ref}
                </p>
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