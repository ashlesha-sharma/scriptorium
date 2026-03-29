import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { FileText, ChevronDown, ChevronUp, Sparkles, Clock, BarChart2, AlertCircle } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

const DOMAIN_COLORS = {
  chemistry: '#059669',
  finance:   '#2563EB',
  law:       '#D97706',
  policy:    '#7C3AED',
  general:   '#6B7280',
}

const MODE_LABELS = {
  conversational: 'Answer',
  extraction:     'Extracted',
  summary:        'Summary',
  comparison:     'Comparison',
  highlight:      'Selection Analysis',
}

export function UserMessage({ message }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-end"
    >
      <div className="max-w-[75%]">
        {message.highlight_text && (
          <div className="mb-1.5 flex items-center gap-1.5 justify-end">
            <Sparkles size={11} className="text-gold" />
            <span className="text-2xs text-gold font-medium">Selection context active</span>
          </div>
        )}
        <div className="bg-chat-user rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          <p className="text-sm text-ink leading-relaxed">{message.content}</p>
        </div>
      </div>
    </motion.div>
  )
}

export function AssistantMessage({ message }) {
  const [citationsOpen, setCitationsOpen] = useState(false)
  const [insightsOpen, setInsightsOpen] = useState(true)
  const domainColor = DOMAIN_COLORS[message.domain] || DOMAIN_COLORS.general

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      {/* Avatar */}
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 shadow-sm"
        style={{ background: `${domainColor}15`, border: `1px solid ${domainColor}25` }}
      >
        <span style={{ fontSize: '12px' }}>
          {message.domain === 'chemistry' ? '⚗️' : message.domain === 'finance' ? '📊' : message.domain === 'law' ? '⚖️' : message.domain === 'policy' ? '🏛️' : '📖'}
        </span>
      </div>

      <div className="flex-1 min-w-0">
        {/* Mode tag + confidence */}
        <div className="flex items-center gap-2 mb-2">
          <span
            className="text-2xs font-medium px-2 py-0.5 rounded-full"
            style={{ background: `${domainColor}12`, color: domainColor }}
          >
            {MODE_LABELS[message.query_mode] || 'Answer'}
          </span>
          {message.confidence !== undefined && (
            <span className="text-2xs text-muted flex items-center gap-1">
              <BarChart2 size={10} />
              {Math.round(message.confidence * 100)}% confidence
            </span>
          )}
          {message.processing_time_ms && (
            <span className="text-2xs text-muted flex items-center gap-1 ml-auto">
              <Clock size={10} />
              {(message.processing_time_ms / 1000).toFixed(1)}s
            </span>
          )}
        </div>

        {/* Answer body */}
        <div className="bg-chat-ai rounded-2xl rounded-tl-sm px-4 py-3.5 shadow-sm">
          <div className="prose-scriptorium">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>

        {/* Structured insights (extraction mode) */}
        {message.structured_insights?.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setInsightsOpen(!insightsOpen)}
              className="flex items-center gap-1.5 text-xs text-navy font-medium mb-1.5 hover:text-navy/70 transition-colors"
            >
              <BarChart2 size={12} />
              Extracted Data Points ({message.structured_insights.length})
              {insightsOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
            {insightsOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="bg-white border border-border-subtle rounded-xl overflow-hidden"
              >
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-navy/5 border-b border-border-subtle">
                      <th className="text-left px-3 py-2 text-navy font-medium">Label</th>
                      <th className="text-left px-3 py-2 text-navy font-medium">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {message.structured_insights.map((ins, i) => (
                      <tr key={i} className="border-b border-border-subtle last:border-0">
                        <td className="px-3 py-2 text-muted">{ins.label}</td>
                        <td className="px-3 py-2 font-medium font-mono text-ink">{ins.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </motion.div>
            )}
          </div>
        )}

        {/* Citations */}
        {message.citations?.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setCitationsOpen(!citationsOpen)}
              className="flex items-center gap-1.5 text-xs text-muted hover:text-ink transition-colors"
            >
              <FileText size={11} />
              {message.citations.length} source{message.citations.length > 1 ? 's' : ''}
              {citationsOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>

            {citationsOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-1.5 space-y-1.5"
              >
                {message.citations.map((cit, i) => (
                  <div
                    key={i}
                    className="bg-white/70 border border-border-subtle rounded-lg px-3 py-2.5 text-xs"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <FileText size={10} className="text-navy/50 shrink-0" />
                      <span className="font-medium text-navy truncate">{cit.filename}</span>
                      <span className="text-muted ml-auto shrink-0">p.{cit.page}</span>
                      <span
                        className="text-2xs shrink-0"
                        style={{ color: `hsl(${Math.round(cit.relevance_score * 120)}, 60%, 40%)` }}
                      >
                        {Math.round(cit.relevance_score * 100)}%
                      </span>
                    </div>
                    <p className="text-muted leading-relaxed line-clamp-2">{cit.chunk_text}</p>
                  </div>
                ))}
              </motion.div>
            )}
          </div>
        )}

        {/* Follow-up questions */}
        {message.follow_up_questions?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {message.follow_up_questions.map((q, i) => (
              <button
                key={i}
                onClick={() => message.onFollowUp?.(q)}
                className="text-2xs text-slate border border-slate/25 hover:border-slate/50 hover:bg-slate/5 px-2.5 py-1 rounded-full transition-all duration-150"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

export function LoadingMessage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div className="w-7 h-7 rounded-lg bg-navy/8 flex items-center justify-center shrink-0 mt-0.5">
        <span style={{ fontSize: '12px' }}>📖</span>
      </div>
      <div className="bg-chat-ai rounded-2xl rounded-tl-sm px-4 py-3.5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="flex gap-1">
            {[0, 1, 2].map(i => (
              <span
                key={i}
                className="w-1.5 h-1.5 bg-navy/30 rounded-full animate-bounce"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </span>
          <span className="text-xs text-muted">Reasoning across documents…</span>
        </div>
      </div>
    </motion.div>
  )
}

export function ErrorMessage({ error }) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
      <div className="w-7 h-7 rounded-lg bg-crimson/10 flex items-center justify-center shrink-0 mt-0.5">
        <AlertCircle size={13} className="text-crimson" />
      </div>
      <div className="bg-red-50 border border-red-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-crimson">
        {error}
      </div>
    </motion.div>
  )
}
