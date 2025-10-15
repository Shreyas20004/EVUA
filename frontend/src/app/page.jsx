"use client"

import Header from "@/components/Header"
import StatsCard from "@/components/StatsGrid"
import FileList from "@/components/ProjectFiles"
import CodePanels from "@/components/CodeDiff"
import Assistant from "@/components/AssistantPanel"
import { files } from "@/data/files"
import { ProjectProvider } from "@/components/ProjectContext"

export default function Page() {
  const upgraded = files.filter((f) => f.status === "upgraded").length
  const needsReview = files.filter((f) => f.status === "needs-review").length
  const pending = files.filter((f) => f.status === "pending").length

  return (
    <main className="min-h-screen bg-evua-bg">
      <div className="max-w-[1400px] mx-auto p-6 space-y-6">
        <ProjectProvider>
          <Header />

          {/* Status summary row */}
          <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatsCard label="Upgraded" value={String(upgraded)} hint="Files upgraded by EVUA" />
            <StatsCard label="Needs Review" value={String(needsReview)} hint="Manual attention recommended" />
            <StatsCard label="Pending" value={String(pending)} hint="Queued for processing" />
          </section>

          {/* Three-column dashboard */}
          <section className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Left: File List */}
            <aside className="md:col-span-3">
              <div className="bg-evua-panel rounded-xl shadow-lg border border-border/20">
                <FileList />
              </div>
            </aside>

            {/* Center: Code Panels */}
            <section className="md:col-span-6">
              <div className="bg-evua-panel rounded-xl shadow-lg border border-border/20">
                <CodePanels />
              </div>
            </section>

            {/* Right: Assistant */}
            <aside className="md:col-span-3">
              <div className="bg-evua-panel rounded-xl shadow-lg border border-border/20">
                <Assistant />
              </div>
            </aside>
          </section>
        </ProjectProvider>
      </div>
    </main>
  )
}
