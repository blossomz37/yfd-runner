import type { ReactNode } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { loadRuns } from "../lib/api";
import { NavLink } from "./_components/nav-link";

export const metadata: Metadata = {
  title: "YFD Studio",
  description: "Local-first editorial console for yfd-runner"
};

const NAV_ITEMS = [
  { href: "/", label: "Runs" },
  { href: "/intake", label: "Intake" },
  { href: "/templates", label: "Templates" },
  { href: "/models", label: "Models" },
  { href: "/worksheets", label: "Worksheets" },
  { href: "/outputs", label: "Outputs" },
  { href: "/settings", label: "Settings" }
];

export default async function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  const runs = await loadRuns();

  return (
    <html lang="en">
      <body>
        <div className="studio-shell">
          <div className="studio-frame">
            <aside className="panel sidebar">
              <div className="brand-row">
                <div className="brand-mark">YFD Studio</div>
                <span className="kbd">⌘K</span>
              </div>
              <div className="nav-group">
                {NAV_ITEMS.map((item) => (
                  <NavLink key={item.href} href={item.href} label={item.label} />
                ))}
              </div>
              <div className="stack">
                <div className="section-head">
                  <h3>Quick Resume</h3>
                  <span className="pill">{runs.length} runs</span>
                </div>
                {runs.slice(0, 4).map((run, index) => (
                  <Link
                    key={run.run_id}
                    className={`resume-item${index === 0 ? " active" : ""}`}
                    href={`/runs/${run.run_id}`}
                  >
                    <div className="list-title">{run.run_id}</div>
                    <div className="list-copy">
                      ch{String(run.current_chapter ?? 0).padStart(2, "0")} · {run.latest_step ?? "idle"}
                    </div>
                  </Link>
                ))}
              </div>
            </aside>
            <main className="panel main-pane">{children}</main>
            <aside className="panel right-rail">
              <div className="rail-head">
                <h3>Command Surface</h3>
                <span className="pill">local-first</span>
              </div>
              <div className="rail-list">
                <div className="list-item">
                  <div className="list-title">Open run</div>
                  <div className="list-copy mono">{runs[0]?.run_id ?? "partial_ch2_20260319"}</div>
                </div>
                <div className="list-item">
                  <div className="list-title">Render prompt</div>
                  <div className="list-copy mono">04-edit-style.j2 against {runs[0]?.run_id ?? "chapter 03"}</div>
                </div>
                <div className="list-item">
                  <div className="list-title">Build manuscript</div>
                  <div className="list-copy mono">summary-backed output only</div>
                </div>
              </div>
              <div className="stack">
                <div className="section-head">
                  <h3>Current Baseline</h3>
                  <span className="status-chip" data-tone="accent">
                    Option C
                  </span>
                </div>
                <div className="empty-note">
                  The shell is intentionally editorial-first: runs, review, and prompt preview get priority over KPI
                  tiles and admin surfaces.
                </div>
              </div>
            </aside>
          </div>
        </div>
      </body>
    </html>
  );
}
