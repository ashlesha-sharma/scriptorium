import { motion } from 'framer-motion'
import { X, TrendingUp, FileText, Lightbulb, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

const IMPORTANCE_STYLES = {
  critical: 'bg-crimson/8 border-crimson/20 text-crimson',
  high:     'bg-navy/6 border-navy/15 text-navy',
  medium:   'bg-gray-50 border-gray-200 text-muted',
}

const IMPORTANCE_DOTS = {
  critical: 'bg-crimson',
  high:     'bg-gold',
  medium:   'bg-gray-300',
}

export default function InsightPanel({ insights, loading, onClose }) {
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="border-b border-gold/20 bg-amber-50/40 overflow-hidden shrink-0"
    >
      <div className="px-4 py-3 max-h-64 overflow-y-auto">
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb size={13} className="text-gold" />
          <span className="text-xs font-semibold text-navy tracking-wide uppercase">Auto Insights</span>
          {insights && (
            <span className="text-2xs text-muted ml-1">· {insights.document_count} document{insights.document_count !== 1 ? 's' : ''}</span>
          )}
          <button onClick={onClose} className="ml-auto text-muted hover:text-ink transition-colors">
            <X size={13} />
          </button>
        </div>

        {loading && (
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-12 rounded-lg shimmer" />
            ))}
          </div>
        )}

        {insights && !loading && (
          <div className="space-y-3">
            {/* Executive Summary */}
            {insights.executive_summary && (
              <div className="bg-white/70 border border-border-subtle rounded-xl p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <TrendingUp size={11} className="text-navy/60" />
                  <span className="text-2xs font-semibold text-navy uppercase tracking-wide">Executive Summary</span>
                </div>
                <p className="text-xs text-ink leading-relaxed">{insights.executive_summary}</p>
              </div>
            )}

            {/* Key Findings */}
            {insights.key_findings?.length > 0 && (
              <div>
                <p className="text-2xs font-semibold text-navy uppercase tracking-wide mb-2">
                  Key Findings ({insights.key_findings.length})
                </p>
                <div className="space-y-1.5">
                  {insights.key_findings.map((finding, i) => (
                    <div
                      key={i}
                      className={clsx(
                        'flex items-start gap-2 px-3 py-2 rounded-lg border text-xs',
                        IMPORTANCE_STYLES[finding.importance] || IMPORTANCE_STYLES.medium
                      )}
                    >
                      <div className={clsx(
                        'w-1.5 h-1.5 rounded-full shrink-0 mt-1',
                        IMPORTANCE_DOTS[finding.importance] || IMPORTANCE_DOTS.medium
                      )} />
                      <div>
                        <span className="font-medium">{finding.title}: </span>
                        <span className="opacity-80 leading-relaxed">{finding.description}</span>
                        {finding.citation && (
                          <div className="flex items-center gap-1 mt-1 opacity-60">
                            <FileText size={9} />
                            <span className="text-2xs">{finding.citation.filename} · p.{finding.citation.page}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {insights.key_findings?.length === 0 && (
              <div className="flex items-center gap-2 text-xs text-muted py-2">
                <AlertCircle size={13} />
                No significant findings detected. Try a more specific focus query.
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
