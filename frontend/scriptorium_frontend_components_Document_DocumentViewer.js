import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Sparkles, X } from 'lucide-react'
import { useStore } from '../../lib/store'
import clsx from 'clsx'

export default function DocumentViewer() {
  const { activeDocId, documents, setHighlightedText, highlightedText } = useStore()
  const [scale, setScale] = useState(1)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [selectionPopup, setSelectionPopup] = useState(null)
  const viewerRef = useRef(null)
  const [pdfUrl, setPdfUrl] = useState(null)

  const activeDoc = documents.find(d => d.doc_id === activeDocId)

  useEffect(() => {
    if (activeDocId) {
      setPdfUrl(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents/${activeDocId}/file`)
      setPage(1)
    }
  }, [activeDocId])

  // Handle text selection → highlight-to-query
  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection()
    const selected = selection?.toString().trim()
    if (selected && selected.length > 10) {
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      const viewerRect = viewerRef.current?.getBoundingClientRect()
      if (viewerRect) {
        setSelectionPopup({
          text: selected,
          x: rect.left - viewerRect.left + rect.width / 2,
          y: rect.top - viewerRect.top - 10,
        })
      }
    } else {
      setSelectionPopup(null)
    }
  }, [])

  const handleAskAboutSelection = () => {
    setHighlightedText(selectionPopup.text)
    setSelectionPopup(null)
    window.getSelection()?.removeAllRanges()
  }

  if (!activeDoc) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white/30">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-navy/6 flex items-center justify-center mx-auto mb-4">
            <FileText size={28} className="text-navy/30" />
          </div>
          <p className="font-display text-lg text-ink/40">No document selected</p>
          <p className="text-sm text-muted mt-1">Upload a PDF from the sidebar to begin</p>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={viewerRef}
      className="flex-1 flex flex-col bg-white/20 relative overflow-hidden"
      onMouseUp={handleMouseUp}
    >
      {/* Viewer toolbar */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border-subtle bg-white/50 shrink-0">
        <FileText size={14} className="text-navy/60" />
        <span className="text-sm font-medium text-ink truncate flex-1">{activeDoc.filename}</span>

        {/* Page controls */}
        {totalPages > 1 && (
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-100 disabled:opacity-30 transition-colors"
            >
              <ChevronLeft size={12} />
            </button>
            <span className="text-xs text-muted font-mono">{page} / {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-100 disabled:opacity-30 transition-colors"
            >
              <ChevronRight size={12} />
            </button>
          </div>
        )}

        {/* Zoom */}
        <div className="flex items-center gap-1">
          <button onClick={() => setScale(s => Math.max(0.5, s - 0.15))} className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-100 transition-colors">
            <ZoomOut size={12} />
          </button>
          <span className="text-2xs font-mono text-muted w-10 text-center">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale(s => Math.min(2, s + 0.15))} className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-100 transition-colors">
            <ZoomIn size={12} />
          </button>
        </div>
      </div>

      {/* PDF iframe embed */}
      <div className="flex-1 overflow-auto p-4 selectable-text">
        {activeDoc.processing_stage === 'ready' ? (
          <div
            className="mx-auto bg-white shadow-card rounded-lg overflow-hidden"
            style={{ transform: `scale(${scale})`, transformOrigin: 'top center', width: `${100 / scale}%` }}
          >
            <iframe
              src={`${pdfUrl}#page=${page}`}
              className="w-full"
              style={{ height: '80vh', border: 'none' }}
              title={activeDoc.filename}
              onLoad={(e) => {
                // Try to get total pages — may not work cross-origin
                try {
                  const pdf = e.target.contentDocument
                  if (pdf) setTotalPages(activeDoc.page_count || 0)
                } catch {}
                setTotalPages(activeDoc.page_count || 0)
              }}
            />
          </div>
        ) : (
          <ProcessingOverlay stage={activeDoc.processing_stage} progress={activeDoc.progress} />
        )}
      </div>

      {/* Highlight-to-query popup */}
      <AnimatePresence>
        {selectionPopup && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.95 }}
            className="absolute z-30 pointer-events-auto"
            style={{
              left: Math.min(selectionPopup.x, (viewerRef.current?.offsetWidth || 400) - 200),
              top: selectionPopup.y,
              transform: 'translate(-50%, -100%)',
            }}
          >
            <div className="flex items-center gap-2 bg-navy text-white px-3 py-2 rounded-xl shadow-elevated">
              <Sparkles size={12} className="text-gold" />
              <button
                onClick={handleAskAboutSelection}
                className="text-xs font-medium hover:text-gold transition-colors whitespace-nowrap"
              >
                Ask about selection
              </button>
              <button onClick={() => setSelectionPopup(null)} className="text-white/40 hover:text-white ml-1">
                <X size={11} />
              </button>
            </div>
            {/* Arrow */}
            <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-navy" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Active highlight banner */}
      <AnimatePresence>
        {highlightedText && (
          <motion.div
            initial={{ y: 60 }} animate={{ y: 0 }} exit={{ y: 60 }}
            className="absolute bottom-0 left-0 right-0 bg-gold/10 border-t border-gold/30 px-4 py-2.5 flex items-center gap-3"
          >
            <Sparkles size={13} className="text-gold shrink-0" />
            <p className="text-xs text-ink flex-1 truncate">
              <span className="font-medium text-navy">Selected: </span>
              "{highlightedText.slice(0, 80)}{highlightedText.length > 80 ? '…' : ''}"
            </p>
            <button
              onClick={() => setHighlightedText(null)}
              className="text-muted hover:text-ink transition-colors"
            >
              <X size={13} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ProcessingOverlay({ stage, progress }) {
  const stages = ['parsing', 'ocr', 'chunking', 'embedding']
  const stageLabels = {
    parsing: 'Parsing PDF structure',
    ocr: 'Running OCR on scanned pages',
    chunking: 'Segmenting into knowledge units',
    embedding: 'Generating semantic embeddings',
  }

  return (
    <div className="flex flex-col items-center justify-center h-64">
      <div className="w-64">
        <div className="flex flex-col gap-3">
          {stages.map((s, i) => {
            const stageIdx = stages.indexOf(stage)
            const isDone = i < stageIdx
            const isActive = s === stage
            return (
              <div key={s} className="flex items-center gap-3">
                <div className={clsx(
                  'w-2 h-2 rounded-full shrink-0 transition-all',
                  isDone ? 'bg-emerald-400' : isActive ? 'bg-gold animate-pulse' : 'bg-gray-200'
                )} />
                <span className={clsx(
                  'text-xs transition-colors',
                  isDone ? 'text-emerald-600' : isActive ? 'text-navy font-medium' : 'text-muted'
                )}>
                  {stageLabels[s]}
                </span>
              </div>
            )
          })}
        </div>
        <div className="mt-5 h-1 bg-gray-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-navy to-gold rounded-full"
            animate={{ width: `${progress || 20}%` }}
            transition={{ duration: 0.6 }}
          />
        </div>
        <p className="text-2xs text-muted text-center mt-2">{progress || 20}%</p>
      </div>
    </div>
  )
}
