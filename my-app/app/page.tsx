"use client";

import { useState } from "react";
import Sidebar from "./Sidebar";
import Toolbar from "./editor/[id]/Toolbar";

export default function Home() {
  const [menuOpen, setMenuOpen] = useState(true);

  return (
    <div className="app-frame">
      <div className="editor-shell">
        <header className="no-print doc-toolbar">
          <div className="doc-toolbar-row">
            <Toolbar
              editor={null}
              menuOpen={menuOpen}
              onMenuClick={() => setMenuOpen((value) => !value)}
            />
            <p className="doc-toolbar-status">
              Upload or search a saved resume
            </p>
            <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
          </div>
        </header>
        <main className="app-home">
          <h1 className="text-2xl font-semibold">Resume editor</h1>
          <p className="mt-2 max-w-md text-sm text-neutral-600">
            Open the menu with the three dots below the header. Upload a PDF or
            search a note you saved when downloading.
          </p>
        </main>
      </div>
    </div>
  );
}
