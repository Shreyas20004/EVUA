"use client"

import { useMemo, useState } from "react"
import { ChevronDown, ChevronRight, FileCode2, Folder, FolderOpen } from "lucide-react"
import { files } from "../data/files"
import { useProject } from "./ProjectContext"

function Dot({ status }) {
  const base = "inline-block size-2.5 rounded-full"
  if (status === "upgraded") return <span className={`${base} bg-evua-foreground`} aria-label="Upgraded" />
  if (status === "needs-review") return <span className={`${base} bg-destructive`} aria-label="Needs review" />
  return <span className={`${base} bg-muted-foreground/60`} aria-label="Pending" />
}

function TreeNode({ node, depth = 0 }) {
  const [open, setOpen] = useState(true)
  const isDir = node.kind === "directory"
  const hasChildren = (node.children?.length || 0) > 0
  const { setSelectedPath } = useProject()

  const DotNeutral = <span className="inline-block size-2 rounded-full bg-muted-foreground/60" aria-hidden />

  return (
    <li>
      <div className="flex items-center gap-2 py-1.5" style={{ paddingLeft: depth ? depth * 12 : 0 }}>
        {isDir ? (
          <button
            type="button"
            className="inline-flex items-center gap-1 text-evua-foreground/90 text-sm"
            aria-expanded={open}
            onClick={() => setOpen(v => !v)}
          >
            {open ? <ChevronDown className="size-4 text-evua-muted" /> : <ChevronRight className="size-4 text-evua-muted" />}
            {open ? <FolderOpen className="size-4 text-evua-muted" /> : <Folder className="size-4 text-evua-muted" />}
            <span className="truncate">{node.name}</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setSelectedPath(node.path)}
            className="flex items-center gap-2 text-sm hover:bg-evua-bg/40 rounded px-1 py-0.5 text-left w-full"
            aria-label={`Open ${node.name} in diff viewer`}
          >
            {DotNeutral}
            <FileCode2 className="size-4 text-evua-muted" aria-hidden />
            <span className="text-evua-foreground/90 truncate">{node.name}</span>
          </button>
        )}
      </div>
      {isDir && hasChildren && open && (
        <ul>
          {node.children.map(child => (
            <TreeNode key={child.path} node={child} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  )
}

export default function FileList() {
  const { root, setSelectedPath } = useProject()
  const hasSelection = !!root

  const headerLegend = useMemo(() => (
    <div className="flex items-center gap-3 text-xs text-evua-muted">
      <div className="flex items-center gap-1">
        <span className="inline-block size-2 rounded-full bg-evua-foreground" /> Upgraded
      </div>
      <div className="flex items-center gap-1">
        <span className="inline-block size-2 rounded-full bg-destructive" /> Needs Review
      </div>
      <div className="flex items-center gap-1">
        <span className="inline-block size-2 rounded-full bg-muted-foreground/60" /> Pending
      </div>
    </div>
  ), [])

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-evua-foreground text-sm font-medium">Project Files</h2>
        {!hasSelection && headerLegend}
      </div>

      {hasSelection ? (
        <div className="max-h-[52vh] overflow-auto pr-1">
          <ul className="divide-y-0">
            {root && <TreeNode node={root} depth={0} />}
          </ul>
        </div>
      ) : (
        <ul className="divide-y divide-border/10">
          {files.map(f => (
            <li key={f.name} className="py-2">
              <button
                type="button"
                onClick={() => setSelectedPath(f.name)}
                className="w-full flex items-center gap-3 hover:bg-evua-bg/40 rounded px-2 py-1 text-left"
                aria-label={`Open ${f.name} in diff viewer`}
              >
                <Dot status={f.status} />
                <FileCode2 className="size-4 text-evua-muted" aria-hidden />
                <span className="text-sm text-evua-foreground/90 truncate">{f.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
