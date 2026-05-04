"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { Moon, Sun, Star, Github } from "lucide-react";
import { useTheme } from "@/lib/theme-context";

const TICKER_H = 36;

export function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const [docked, setDocked] = useState(false);

  useEffect(() => {
    const onScroll = () => setDocked(window.scrollY >= TICKER_H - 2);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      style={{ top: docked ? 0 : TICKER_H }}
      className="fixed left-0 right-0 z-40 w-full transition-[top] duration-150 ease-out"
    >
      <div
        className={`border-b backdrop-blur-xl transition-all duration-200 ${
          docked
            ? "bg-background/95 border-border shadow-lg shadow-black/10 dark:shadow-black/30"
            : "bg-background/60 border-border/30"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
            <Image
              src="/finora_logo.png"
              alt="Finora"
              width={120}
              height={32}
              className="h-8 w-auto"
              priority
            />
          </Link>

          <div className="flex items-center gap-2 sm:gap-3">
            <a
              href="https://github.com/charan-s108/Finora"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-accent transition-colors text-sm font-medium text-foreground"
            >
              <Github className="w-4 h-4" />
              <span>Star</span>
              <span className="flex items-center gap-1 bg-yellow-400/15 text-yellow-500 dark:text-yellow-400 px-1.5 py-0.5 rounded text-xs font-semibold">
                <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                Star
              </span>
            </a>

            <a
              href="https://github.com/charan-s108/Finora"
              target="_blank"
              rel="noopener noreferrer"
              className="sm:hidden p-2 rounded-lg border border-border bg-card hover:bg-accent transition-colors text-foreground"
              aria-label="GitHub"
            >
              <Github className="w-4 h-4" />
            </a>

            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-border bg-card hover:bg-accent transition-colors text-foreground"
              aria-label="Toggle theme"
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
