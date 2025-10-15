"use client"

import { Send } from "lucide-react"

export default function Assistant() {
  return (
    <div className="p-4 h-full flex flex-col">
      <div className="mb-3">
        <h2 className="text-evua-foreground text-sm font-medium">Assistant</h2>
        <p className="text-evua-muted text-xs mt-1">Ask EVUA about upgrade strategy or specific diffs.</p>
      </div>

      <div className="flex-1 overflow-auto space-y-3 pr-1">
        <div className="rounded-lg bg-evua-bg/40 border border-border/10 p-3">
          <p className="text-xs text-evua-foreground">
            Hello! I’ll help you upgrade Python 2 code to Python 3 using a hybrid AST + LLM approach.
          </p>
        </div>
        <div className="rounded-lg bg-evua-bg/40 border border-border/10 p-3">
          <p className="text-xs text-evua-foreground">
            I detected print statements and xrange usage. I proposed safe, modern replacements.
          </p>
        </div>
        <div className="rounded-lg bg-evua-bg/40 border border-border/10 p-3">
          <p className="text-xs text-evua-foreground">
            Let me know if you want stricter type hints or automated test updates next.
          </p>
        </div>
      </div>

      <form onSubmit={(e) => e.preventDefault()} className="mt-3 flex items-center gap-2" aria-label="Assistant input">
        <input
          className="flex-1 rounded-lg bg-evua-bg/60 border border-border/20 px-3 py-2 text-sm text-evua-foreground placeholder:text-evua-muted focus:outline-none focus:ring-2 focus:ring-evua-accent/40"
          placeholder="Type your message..."
        />
        <button
          type="submit"
          className="inline-flex items-center gap-2 rounded-lg px-3 py-2 bg-evua-accent text-evua-on-accent text-xs font-medium hover:opacity-95 transition"
        >
          <Send className="size-4" />
          Send
        </button>
      </form>
    </div>
  )
}
