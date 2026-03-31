import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Trash2, Lightbulb, BarChart2, GitCompare, Download } from 'lucide-react'
import { useStore } from '../../lib/store'
import { sendQuery, getAutoInsights, compareDocuments } from '../../lib/api'
import { UserMessage, AssistantMessage, LoadingMessage, ErrorMessage } from './MessageBubble'
import ChatInput from './ChatInput'
import InsightPanel from '../Intelligence/InsightPanel'
import toast from 'react-hot-toast'
import clsx from 'clsx'

export default function ChatPanel() {
  const {
    getMessages, addMessage, updateLastMessage, clearSession,
    selectedDocIds, documents, queryMode, highlightedText, setHighlightedText,
    explainLevel, isQuerying, setIsQuerying, activeSessionId,
  } = useStore()

  const messages = getMessages()
  const bottomRef = useRef(null)
  const [insightOpen, setInsightOpen] = useState(false)
  const [insights, setInsights] = useState(null)
  const [loadingInsights, setLoadingInsights] = useState(false)
  const [compareAspect, setCompareAspect] = useState('')
  const [showCompareBar, setShowCompareBar] = useState(false)

  const readyDocIds = documents
    .filter(d => selectedDocIds.includes(d.doc_id) && d.processing_stage === 'ready')
    .map(d => d.doc_id)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isQuerying])

  const handleQuery = async (query) => {
    if (!readyDocIds.length) { toast.error('No ready documents selected'); return }

    // Add user message
    addMessage({
      role: 'user',
      content: query,
      highlight_text: highlightedText,
      timestamp: new Date().toISOString(),
    })
    setHighlightedText(null)
    setIsQuerying(true)

    // Add loading placeholder
    addMessage({
      role: 'assistant',
      content: '',
      loading: true,
      timestamp: new Date().toISOString(),
    })

    try {
      const history = messages
        .filter(m => !m.loading)
        .slice(-6)
        .map(m => ({ role: m.role, content: m.content }))

      const response = await sendQuery({
        query,
        docIds: readyDocIds,
        history,
        mode: queryMode,
        highlightText: highlightedText,
        explainLevel,
        sessionId: activeSessionId,
      })

      updateLastMessage({
        loading: false,
        content: response.answer,
        citations: response.citations,
        structured_insights: response.structured_insights,
        domain: response.domain,
        query_mode: response.query_mode,
        confidence: response.confidence,
        follow_up_questions: response.follow_up_questions,
        processing_time_ms: response.processing_time_ms,
        onFollowUp: handleQuery,
      })
    } catch (e) {
      updateLastMessage({
        loading: false,
        error: e.message,
      })
    } finally {
      setIsQuerying(false)
    }
  }

  const handleAutoInsights = async () => {
    if (!readyDocIds.length) { toast.error('Select ready documents first'); return }
    setLoadingInsights(true)
    setInsightOpen(true)
    try {
      const data = await getAutoInsights(readyDocIds)
      setInsights(data)
    } catch (e) {
      toast.error('Failed to generate insights: ' + e.message)
    } finally {
      setLoadingInsights(false)
    }
  }

  const handleCompare = async () => {
    if (readyDocIds.length < 2) { toast.error('Select at least 2 documents to compare'); return }
    if (!compareAspect.trim()) { toast.error('Enter an aspect to compare'); return }
    setShowCompareBar(false)
    await handleQuery(`Compare documents on: ${compareAspect}`)
    setCompareAspect('')
  }

  const exportMarkdown = () => {
    const md = messages
      .filter(m => !m.loading)
      .map(m => m.role === 'user' ? `**You:** ${m.content}` : `**Scriptorium:** ${m.content}`)
      .join('\n\n---\n\n')
    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `scriptorium-session-${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Session exported as Markdown')
  }

  return (
    <div className="flex flex-col h-full bg-parchment/40 relative">

      {/* Chat toolbar */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border-subtle bg-white/40 shrink-0">
        <span className="text-xs font-medium text-muted">Research Chat</span>
        <div className="flex-1" />

        {/* Action buttons */}
        <button
          onClick={handleAutoInsights}
          title="Auto-generate insights"
          className={clsx(
            'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all',
            insightOpen
              ? 'bg-gold/15 text-gold border border-gold/25'
              : 'text-muted hover:text-ink hover:bg-white/70 border border-transparent'
          )}
        >
          <Lightbulb size={12} />
          Insights
        </button>

        <button
          onClick={() => setShowCompareBar(!showCompareBar)}
          disabled={readyDocIds.length < 2}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-muted hover:text-ink hover:bg-white/70 transition-all disabled:opacity-40 disabled:cursor-not-allowed border border-transparent"
          title="Compare documents"
        >
          <GitCompare size={12} />
          Compare
        </button>

        {messages.length > 0 && (
          <>
            <button
              onClick={exportMarkdown}
              className="text-muted hover:text-ink transition-colors p-1.5 rounded-lg hover:bg-white/70"
              title="Export session"
            >
              <Download size={13} />
            </button>
            <button
              onClick={clearSession}
              className="text-muted hover:text-crimson transition-colors p-1.5 rounded-lg hover:bg-white/70"
              title="Clear chat"
            >
              <Trash2 size={13} />
            </button>
          </>
        )}
      </div>

      {/* Compare aspect bar */}
      <AnimatePresence>
        {showCompareBar && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="flex items-center gap-2 px-4 py-2 bg-navy/4 border-b border-navy/10 shrink-0 overflow-hidden"
          >
            <GitCompare size={13} className="text-navy/60 shrink-0" />
            <input
              value={compareAspect}
              onChange={e => setCompareAspect(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCompare()}
              placeholder="What aspect to compare? (e.g. methodology, findings, limitations)"
              className="flex-1 bg-transparent text-xs outline-none text-ink placeholder-muted/60"
              autoFocus
            />
            <button
              onClick={handleCompare}
              disabled={!compareAspect.trim()}
              className="text-xs px-3 py-1.5 bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors disabled:opacity-40"
            >
              Compare
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Insight Panel */}
      <AnimatePresence>
        {insightOpen && (
          <InsightPanel
            insights={insights}
            loading={loadingInsights}
            onClose={() => setInsightOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
        {messages.length === 0 && (
          <EmptyState onSuggestion={handleQuery} hasReadyDocs={readyDocIds.length > 0} />
        )}

        {messages.map((msg, i) => {
          if (msg.loading) return <LoadingMessage key={i} />
          if (msg.error) return <ErrorMessage key={i} error={msg.error} />
          if (msg.role === 'user') return <UserMessage key={i} message={msg} />
          return <AssistantMessage key={i} message={{ ...msg, onFollowUp: handleQuery }} />
        })}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSubmit={handleQuery} disabled={isQuerying} />
    </div>
  )
}

function EmptyState({ onSuggestion, hasReadyDocs }) {
  const suggestions = [
    'Summarize the key findings of this document',
    'Extract all quantitative data points',
    'What are the main arguments presented?',
    'What methodology is described?',
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="flex flex-col items-center justify-center h-full text-center py-12"
    >
      <div className="w-14 h-14 rounded-2xl bg-navy/6 flex items-center justify-center mb-4">
        <BarChart2 size={22} className="text-navy/40" />
      </div>
      <h3 className="font-display text-lg text-ink/60 mb-1">Start your research</h3>
      <p className="text-sm text-muted mb-6 max-w-xs leading-relaxed">
        {hasReadyDocs
          ? 'Ask a question, extract data, or generate insights from your documents'
          : 'Select documents from the sidebar, then ask anything'}
      </p>

      {hasReadyDocs && (
        <div className="flex flex-wrap gap-2 justify-center max-w-sm">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggestion(s)}
              className="text-xs text-slate border border-slate/20 hover:border-slate/40 hover:bg-slate/5 px-3 py-1.5 rounded-full transition-all duration-150"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </motion.div>
  )
}
