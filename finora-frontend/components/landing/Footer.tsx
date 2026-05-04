"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Github, Heart, ExternalLink } from "lucide-react";

interface FooterLink { label: string; href: string; external?: boolean }
interface FooterSection { heading: string; items: FooterLink[] }

const LINKS: FooterSection[] = [
  {
    heading: "Product",
    items: [
      { label: "Dashboard", href: "/dashboard" },
      { label: "Finora AI", href: "/dashboard" },
      { label: "Market Pulse", href: "#" },
    ],
  },
  {
    heading: "Stack",
    items: [
      { label: "LangGraph", href: "https://langchain-ai.github.io/langgraph/", external: true },
      { label: "Qdrant", href: "https://qdrant.tech", external: true },
      { label: "Groq", href: "https://groq.com", external: true },
    ],
  },
  {
    heading: "Open Source",
    items: [
      { label: "GitHub", href: "https://github.com/charan-s108/Finora", external: true },
      { label: "Report Issue", href: "https://github.com/charan-s108/Finora/issues", external: true },
    ],
  },
];

export function Footer() {
  const router = useRouter();

  return (
    <footer className="border-t border-border bg-card/30 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-14">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          {/* Brand column */}
          <div className="md:col-span-1 flex flex-col gap-4">
            <Image
              src="/finora_logo.png"
              alt="Finora"
              width={110}
              height={40}
              className="h-14 w-auto"
            />
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
              AI-powered equities intelligence for NRI and Expats. 555+ US & Indian stocks, real-time.
            </p>
            <a
              href="https://github.com/charan-s108/Finora"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
            >
              <Github className="w-4 h-4" />
              charan-s108/Finora
            </a>
          </div>

          {/* Link columns */}
          {LINKS.map(({ heading, items }) => (
            <div key={heading} className="flex flex-col gap-3">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-muted-foreground/60">
                {heading}
              </p>
              <ul className="space-y-2.5">
                {items.map(({ label, href, external }) => (
                  <li key={label}>
                    {external ? (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors group"
                      >
                        {label}
                        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-50 transition-opacity" />
                      </a>
                    ) : (
                      <button
                        onClick={() => router.push(href)}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors text-left"
                      >
                        {label}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="border-t border-border pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
          <p>© {new Date().getFullYear()} Finora. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <p className="text-muted-foreground/50 italic text-[11px]">
              For informational purposes only. Not financial advice.
            </p>
            <p className="flex items-center gap-1">
              Built with <Heart className="w-3 h-3 text-rose-400 fill-rose-400 mx-0.5" /> by{" "}
              <span className="font-semibold text-foreground ml-0.5">Charan</span>
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
