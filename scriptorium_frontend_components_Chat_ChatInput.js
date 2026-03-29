import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Sparkles, X, Mic, Square } from 'lucide-react'
import { useStore } from '../../lib/store'
import clsx from 'clsx'

const MODE_PLACEHOLDERS = {
  conversational: 'Ask anything about your documents…',
  extraction:     'What data should I extract? (e.g. "Extract all yield percentages")',
  summary:        'What should I summarize? (leave blank for full document)',
  comparison:     'What aspect should I compare across documents?',
  highlight:      'Ask a question about the selected passage…',
}

export default function ChatInput({ onSubmit, disabled }) {
  const { queryMode, highlightedText, setHighlightedText, selectedDocIds, documents } = useStore()
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const hasReady = documents.some(d => selectedDocIds.includes(d.doc_id) && d.processing_stage === 'ready')

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`
  }, [value])

  // Auto-focus when highlight text is set
  useEffect(() => {
    if (highlightedText) textareaRef.current?.focus()
  }, [highlightedText])

  const handleSubmit = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSubmit(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const activePlaceholder = highlightedText
    ? MODE_PLACEHOLDERS.highlight
    : MODE_PLACEHOLDERS[queryMode] || MODE_PLACEHOLDERS.conversational

  const isBlocked = !hasReady || disabled

  return (
    <div className="border-t border-border-subtle bg-parchment/80 backdrop-blur-sm px-4 py-3">
      {/* No documents warning */}
      {!hasReady && selectedDocIds.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center text-xs text-muted mb-2 pb-2 border-b border-border-subtle"
        >
          Select documents from the sidebar to start querying
        </motion.div>
      )}

      {/* Highlight context bar */}
      <AnimatePresence>
        {highlightedText && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-2 flex items-start gap-2 px-3 py-2 bg-gold/8 border border-gold/25 rounded-xl"
          >
            <Sparkles size={12} className="text-gold mt-0.5 shrink-0" />
            <p className="text-xs text-ink flex-1 line-clamp-2 leading-relaxed">
              <span className="font-medium text-navy">Asking about: </span>
              "{highlightedText.slice(0, 120)}{highlightedText.length > 120 ? '…' : ''}"
            </p>
            <button
              onClick={() => setHighlightedText(null)}
              className="text-muted hover:text-ink shrink-0 transition-colors"
            >
              <X size={12} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input row */}
      <div className={clsx(
        'flex items-end gap-2 bg-white rounded-2xl border transition-all duration-200 px-3 py-2.5',
        disabled ? 'border-border-subtle opacity-60' : 'border-border-medium focus-within:border-navy/30 focus-within:shadow-sm'
      )}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder={isBlocked ? 'Select a document first…' : activePlaceholder}
          disabled={isBlocked}
          rows={1}
          className="flex-1 bg-transparent text-sm text-ink placeholder-muted/60 resize-none outline-none leading-relaxed min-h-[20px]"
          style={{ fontFamily: 'Inter, system-ui, sans-serif' }}
        />

        <div className="flex items-center gap-1.5 shrink-0 pb-0.5">
          {/* Char count */}
          {value.length > 200 && (
            <span className="text-2xs text-muted font-mono">{value.length}</span>
          )}

          {/* Send */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSubmit}
            disabled={isBlocked || !value.trim()}
            className={clsx(
              'w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-150',
              value.trim() && !isBlocked
                ? 'bg-navy text-white shadow-sm hover:bg-navy/90'
                : 'bg-gray-100 text-muted cursor-not-allowed'
            )}
          >
            {disabled
              ? <Square size={12} className="text-navy" />
              : <Send size={13} />}
          </motion.button>
        </div>
      </div>

      {/* Keyboard hint */}
      <p className="text-center text-2xs text-muted/50 mt-1.5">
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  )
}
