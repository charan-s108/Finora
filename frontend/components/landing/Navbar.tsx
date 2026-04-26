"use client";

import Image from "next/image";
import Link from "next/link";
import { Moon, Sun, Star, Github } from "lucide-react";
import { useTheme } from "@/lib/theme-context";

export function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <header className="fixed top-9 left-0 right-0 z-40 w-full border-b border-white/10 dark:border-white/5 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
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

        {/* Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* GitHub Star */}
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

          {/* Mobile GitHub icon only */}
          <a
            href="https://github.com/charan-s108/Finora"
            target="_blank"
            rel="noopener noreferrer"
            className="sm:hidden p-2 rounded-lg border border-border bg-card hover:bg-accent transition-colors text-foreground"
            aria-label="GitHub"
          >
            <Github className="w-4 h-4" />
          </a>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg border border-border bg-card hover:bg-accent transition-colors text-foreground"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
}
