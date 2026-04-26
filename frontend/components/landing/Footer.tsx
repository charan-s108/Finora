import Image from "next/image";
import Link from "next/link";
import { Github, Heart } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-border bg-card/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          {/* Logo + tagline */}
          <div className="flex flex-col items-center sm:items-start gap-2">
            <Image
              src="/finora_logo.png"
              alt="Finora"
              width={100}
              height={28}
              className="h-7 w-auto"
            />
            <p className="text-xs text-muted-foreground text-center sm:text-left">
              AI equities intelligence for NRI and global investors.
            </p>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <a
              href="https://github.com/charan-s108/Finora"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 hover:text-foreground transition-colors"
            >
              <Github className="w-4 h-4" />
              GitHub
            </a>
            <Link href="/" className="hover:text-foreground transition-colors">
              Home
            </Link>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-border mt-8 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
          <p>© {new Date().getFullYear()} Finora. All rights reserved.</p>
          <p className="flex items-center gap-1">
            Developed with <Heart className="w-3 h-3 text-red-400 fill-red-400 mx-0.5" /> by{" "}
            <span className="font-medium text-foreground ml-1">Charan</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
