"use client"

import React, { useState, useMemo, useContext, createContext } from "react"

const ProjectContext = createContext(undefined)

export function ProjectProvider({ children }) {
  const [root, setRoot] = useState(null)
  const [selectedPath, setSelectedPath] = useState(null)
  const [fileIndex, setFileIndex] = useState(null)

  const value = useMemo(
    () => ({ root, setRoot, selectedPath, setSelectedPath, fileIndex, setFileIndex }),
    [root, selectedPath, fileIndex]
  )

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
}

export function useProject() {
  const ctx = useContext(ProjectContext)
  if (!ctx) throw new Error("useProject must be used within a ProjectProvider")
  return ctx
}

export function buildTreeFromPaths(files, rootName = "project") {
  const root = { name: rootName, path: "", kind: "directory", children: [] }

  for (const f of files) {
    const parts = f.path.split("/").filter(Boolean)
    let cursor = root
    let current = ""

    for (let i = 0; i < parts.length; i++) {
      const seg = parts[i]
      const isFile = i === parts.length - 1
      current = current ? `${current}/${seg}` : seg

      if (isFile) {
        cursor.children = cursor.children || []
        cursor.children.push({ name: seg, path: current, kind: "file", size: f.size })
      } else {
        let next = cursor.children?.find(c => c.kind === "directory" && c.name === seg)
        if (!next) {
          next = { name: seg, path: current, kind: "directory", children: [] }
          cursor.children = cursor.children || []
          cursor.children.push(next)
        }
        cursor = next
      }
    }
  }

  return root
}
