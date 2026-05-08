import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Wanderly — AI Trip Planner",
  description:
    "Plan trips dynamically with your preferences, constraints, and real-time updates.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f172a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-ink antialiased font-sans">
        <a href="#main" className="skip-link">
          Skip to main content
        </a>
        <header
          role="banner"
          className="border-b border-slate-200 bg-white sticky top-0 z-10"
        >
          <div className="mx-auto max-w-5xl px-4 py-4 flex items-center justify-between">
            <h1 className="text-xl font-bold tracking-tight">
              <span aria-hidden="true">🧭 </span>Wanderly
            </h1>
            <nav aria-label="Primary">
              <a
                href="/"
                className="text-sm text-muted hover:text-ink underline-offset-4 hover:underline"
              >
                New trip
              </a>
            </nav>
          </div>
        </header>
        <main id="main" tabIndex={-1} className="mx-auto max-w-5xl px-4 py-8">
          {children}
        </main>
        <footer
          role="contentinfo"
          className="border-t border-slate-200 mt-12 py-6 text-sm text-muted text-center"
        >
          Built with Gemini · Deployed on Cloud Run · Open-source MIT.
        </footer>
      </body>
    </html>
  );
}
