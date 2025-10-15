"use client"

import React, { useCallback, useRef } from "react"
import { Bot, FolderOpen } from "lucide-react"
import { useProject, buildTreeFromPaths } from "./ProjectContext"

export default function Header() {
  const { setRoot } = useProject()
  const fileInputRef = useRef(null)

  // Read directory via File System Access API
  const pickDirectory = useCallback(async () => {
    const canUseNativePicker = (() => {
      try {
        return window.self === window.top && typeof window.showDirectoryPicker === "function"
      } catch {
        // Accessing window.top can throw in cross-origin iframes
        return false
      }
    })()

    if (!canUseNativePicker) {
      fileInputRef.current?.click()
      return
    }

    try {
      const dirHandle = await window.showDirectoryPicker()

      async function readDir(handle, basePath = "") {
        const node = {
          name: basePath ? basePath.split("/").pop() || "" : handle.name || "project",
          path: basePath,
          kind: "directory",
          children: [],
        }

        for await (const [name, entry] of handle.entries()) {
          if (entry.kind === "file") {
            const f = await entry.getFile()
            node.children.push({
              name,
              path: basePath ? `${basePath}/${name}` : name,
              kind: "file",
              size: f.size,
            })
          } else if (entry.kind === "directory") {
            const child = await readDir(entry, basePath ? `${basePath}/${name}` : name)
            node.children.push(child)
          }
        }
        return node
      }

      const tree = await readDir(dirHandle)
      setRoot(tree)
    } catch (err) {
      fileInputRef.current?.click()
    }
  }, [setRoot])

  const onFilesSelected = useCallback(
    (e) => {
      const list = e.target.files
      if (!list || list.length === 0) return
      const items = []
      for (let i = 0; i < list.length; i++) {
        const f = list.item(i)
        const rel = f.webkitRelativePath || f.name
        items.push({ path: rel, size: f.size })
      }
      const rootName = items[0]?.path?.split("/")?.[0] || "project"
      const tree = buildTreeFromPaths(items, rootName)
      setRoot(tree)
      e.target.value = ""
    },
    [setRoot]
  )

  return (
    <header className="bg-evua-panel rounded-xl border border-border/20 shadow-lg">
      <div className="px-6 py-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* Left: Logo + Title */}
        <div className="flex items-center gap-3">
          <div aria-hidden className="size-9 rounded-lg bg-evua-accent flex items-center justify-center">
            <Bot className="size-5 text-evua-on-accent" />
          </div>
          <div>
            <h1 className="text-evua-foreground text-xl font-semibold leading-none">EVUA</h1>
            <p className="text-evua-muted text-sm mt-1">AI-Powered Code Upgrade Assistant</p>
          </div>
        </div>

        {/* Right: Tagline + Action */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="hidden md:block text-evua-muted text-sm">AI-powered hybrid code upgrade engine</div>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-lg px-3.5 py-2 bg-evua-accent text-evua-on-accent text-sm font-medium hover:opacity-95 transition"
            aria-label="Select Project Folder"
            onClick={pickDirectory}
          >
            <FolderOpen className="size-4" />
            <span>Select Project Folder</span>
          </button>
          {/* visually hidden fallback input for directory selection */}
          <input
            ref={fileInputRef}
            type="file"
            webkitdirectory=""
            multiple
            className="sr-only"
            onChange={onFilesSelected}
            aria-hidden="true"
            tabIndex={-1}
          />
        </div>
      </div>
    </header>
  )
}
