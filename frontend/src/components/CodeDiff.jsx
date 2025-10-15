"use client"

import { useEffect, useMemo, useState } from "react"
import { ChevronRight, Download } from "lucide-react"
import { useProject } from "./ProjectContext"

const samplePy2 = [
  "# Python 2 example",
  "print 'Hello, world!'",
  "",
  "def divide(a, b):",
  "    return a / b",
  "",
  "for i in xrange(5):",
  "    print i",
]

const samplePy3 = [
  "# Python 3 upgraded example",
  "print('Hello, world!')",
  "",
  "from __future__ import annotations  # retained for tooling compatibility",
  "def divide(a, b):",
  "    return a / b",
  "",
  "for i in range(5):",
  "    print(i)",
]

export default function CodePanels() {
  const [mode, setMode] = useState("AST")
  const { selectedPath, fileIndex } = useProject()
  const [originalText, setOriginalText] = useState(null)
  const [upgradedText, setUpgradedText] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (selectedPath && fileIndex?.has(selectedPath)) {
        const f = fileIndex.get(selectedPath)
        const txt = await f.text()
        if (!cancelled) {
          setOriginalText(txt)
          setUpgradedText(txt)
        }
      } else if (selectedPath?.toLowerCase().endsWith(".py")) {
        setOriginalText(samplePy2.join("\n"))
        setUpgradedText(samplePy3.join("\n"))
      } else if (!selectedPath) {
        setOriginalText(samplePy2.join("\n"))
        setUpgradedText(samplePy3.join("\n"))
      } else {
        setOriginalText(samplePy2.join("\n"))
        setUpgradedText(samplePy2.join("\n"))
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [selectedPath, fileIndex])

  const upgradedBlob = useMemo(() => {
    const content = upgradedText ?? samplePy3.join("\n")
    return new Blob([content], { type: "text/plain" })
  }, [upgradedText])

  function handleDownload() {
    const url = URL.createObjectURL(upgradedBlob)
    const a = document.createElement("a")
    a.href = url
    a.download = selectedPath ? selectedPath.split("/").pop() || "upgraded.txt" : "upgraded_example.py"
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const diffSummaryLines = useMemo(() => {
    const left = (originalText ?? samplePy2.join("\n")).split("\n")
    const right = (upgradedText ?? samplePy3.join("\n")).split("\n")
    if (left.join("\n") === right.join("\n")) {
      return [`Opened ${selectedPath ?? "sample.py"} (no changes detected)`]
    }
    const max = Math.max(left.length, right.length)
    const lines = []
    for (let i = 0; i < max; i++) {
      const l = left[i]
      const r = right[i]
      if (l === r) {
        if (l !== undefined) lines.push(`  ${l}`)
      } else {
        if (l !== undefined) lines.push(`- ${l}`)
        if (r !== undefined) lines.push(`+ ${r}`)
      }
    }
    return lines
  }, [originalText, upgradedText, selectedPath])

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="inline-flex rounded-lg border border-border/20 p-1 bg-evua-bg/40">
          <button
            type="button"
            onClick={() => setMode("AST")}
            aria-pressed={mode === "AST"}
            className={`px-3 py-1.5 text-xs rounded-md transition ${
              mode === "AST" ? "bg-evua-accent text-evua-on-accent" : "text-evua-muted hover:text-evua-foreground"
            }`}
          >
            AST Mode
          </button>
          <button
            type="button"
            onClick={() => setMode("LLM")}
            aria-pressed={mode === "LLM"}
            className={`px-3 py-1.5 text-xs rounded-md transition ${
              mode === "LLM" ? "bg-evua-accent text-evua-on-accent" : "text-evua-muted hover:text-evua-foreground"
            }`}
          >
            LLM Mode
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 bg-evua-accent text-evua-on-accent text-xs font-medium hover:opacity-95 transition"
          >
            Next File
            <ChevronRight className="size-4" />
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 border border-border/30 text-evua-foreground text-xs font-medium hover:bg-evua-bg/40 transition"
          >
            <Download className="size-4 text-evua-muted" />
            Download Upgraded Code
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-lg border border-border/20 bg-evua-bg/40 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border/10">
            <h3 className="text-xs font-medium text-evua-foreground">
              {selectedPath ? "Original: " + selectedPath : "Python 2"}
            </h3>
            <span className="text-xs text-evua-muted">{mode} suggestions</span>
          </div>
          <pre className="p-3 text-xs leading-6 font-mono text-evua-foreground/95 overflow-auto">
            {(originalText ?? samplePy2.join("\n")).split("\n").map((l, i) => (
              <code key={i} className="block">
                {l}
              </code>
            ))}
          </pre>
        </div>

        <div className="rounded-lg border border-border/20 bg-evua-bg/40 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border/10">
            <h3 className="text-xs font-medium text-evua-foreground">
              {selectedPath ? "Upgraded: " + selectedPath : "Python 3"}
            </h3>
            <span className="text-xs text-evua-muted">{mode} output</span>
          </div>
          <pre className="p-3 text-xs leading-6 font-mono text-evua-foreground/95 overflow-auto">
            {(upgradedText ?? samplePy3.join("\n")).split("\n").map((l, i) => (
              <code key={i} className="block">
                {l}
              </code>
            ))}
          </pre>
        </div>
      </div>

      <div className="rounded-lg border border-border/20 bg-evua-bg/40 overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b border-border/10">
          <h3 className="text-xs font-medium text-evua-foreground">Diff summary</h3>
          <span className="text-xs text-evua-muted">+ additions / - removals</span>
        </div>
        <pre className="p-3 text-xs leading-6 font-mono overflow-auto">
          {diffSummaryLines.map((line, idx) => {
            const isAdd = line.trimStart().startsWith("+")
            const isDel = line.trimStart().startsWith("-")
            return (
              <code
                key={idx}
                className={`block ${
                  isAdd ? "text-evua-accent" : isDel ? "text-destructive" : "text-evua-foreground/90"
                }`}
              >
                {line}
              </code>
            )
          })}
        </pre>
      </div>
    </div>
  )
}
