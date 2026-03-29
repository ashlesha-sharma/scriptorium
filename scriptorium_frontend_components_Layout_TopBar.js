import { motion } from 'framer-motion'
import { Search, BookOpen, Settings, Layers, ChevronDown } from 'lucide-react'
import { useStore } from '../../lib/store'
import clsx from 'clsx'

const MODE_OPTIONS = [
  { value: 'conversational', label: 'Conversational', desc: 'Ask anything' },
  { value: 'extraction',     label: 'Extract Data',   desc: 'Pull structured info' },
  { value: 'summary',        label: 'Summarize',      desc: 'Key findings overview' },
  { value: 'comparison',     label: 'Compare',        desc: 'Cross-document analysis' },
]

const EXPLAIN_OPTIONS = [
  { value: 'eli5',         label: 'ELI5',         desc: 'Simple analogies' },
  { value: 'intermediate', label: 'Intermediate', desc: 'Graduate level' },
  { value: 'expert',       label: 'Expert',       desc: 'Full technical depth' },
]

export default function TopBar() {
  const { sidebarOpen, queryMode, setQueryMode, explainLevel, setExplainLevel,
          selectedDocIds, documents } = useStore()

  const readyDocs = documents.filter(d =>
    selectedDocIds.includes(d.doc_id) && d.processing_stage === 'ready'
  )

  return (
    <motion.header
      className={clsx(
        'fixed top-0 right-0 z-10 h-14 flex items-center px-6 gap-4',
        'bg-parchment/90 backdrop-blur-sm border-b border-border-subtle transition-all duration-300'
      )}
      style={{ left: sidebarOpen ? '280px' : '0px' }}
    >
      {/* Branding (when sidebar closed) */}
      {!sidebarOpen && (
        <div className="flex items-center gap-2 mr-2">
          <BookOpen size={16} className="text-navy" />
          <span className="font-display text-navy font-medium text-sm">Scriptorium</span>
        </div>
      )}

      {/* Active context indicator */}
      {readyDocs.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-navy/6 rounded-lg border border-navy/12">
          <Layers size={13} className="text-navy" />
          <span className="text-xs text-navy font-medium">
            {readyDocs.length === 1
              ? readyDocs[0].filename.replace('.pdf', '')
              : `${readyDocs.length} documents`}
          </span>
        </div>
      )}

      <div className="flex-1" />

      {/* Mode selector */}
      <div className="flex items-center gap-1 bg-white/60 border border-border-subtle rounded-lg p-0.5">
        {MODE_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => setQueryMode(opt.value)}
            title={opt.desc}
            className={clsx(
              'px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150',
              queryMode === opt.value
                ? 'bg-navy text-white shadow-sm'
                : 'text-muted hover:text-ink'
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Explain level */}
      <div className="relative group">
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border-subtle bg-white/50 text-xs text-muted hover:text-ink hover:border-border-medium transition-all">
          <span className="font-medium">{EXPLAIN_OPTIONS.find(o => o.value === explainLevel)?.label}</span>
          <ChevronDown size={11} />
        </button>
        <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-border-subtle rounded-xl shadow-elevated opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-50 overflow-hidden">
          {EXPLAIN_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setExplainLevel(opt.value)}
              className={clsx(
                'w-full text-left px-3 py-2.5 text-xs transition-colors',
                explainLevel === opt.value
                  ? 'bg-navy/6 text-navy font-medium'
                  : 'text-muted hover:bg-gray-50 hover:text-ink'
              )}
            >
              <div className="font-medium">{opt.label}</div>
              <div className="text-2xs opacity-60 mt-0.5">{opt.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </motion.header>
  )
}
