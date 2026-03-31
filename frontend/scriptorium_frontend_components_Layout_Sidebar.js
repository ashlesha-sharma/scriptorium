import { motion, AnimatePresence } from 'framer-motion'
import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { FileText, Upload, Trash2, ChevronLeft, ChevronRight, CheckSquare, Square, Loader, CheckCircle, AlertCircle, BookOpen, Zap } from 'lucide-react'
import { useStore } from '../../lib/store'
import { uploadDocument, deleteDocument, getDocumentStatus } from '../../lib/api'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const DOMAIN_LABELS = {
  chemistry: { label: 'Chem', cls: 'domain-chemistry' },
  finance:   { label: 'Finance', cls: 'domain-finance' },
  law:       { label: 'Law', cls: 'domain-law' },
  policy:    { label: 'Policy', cls: 'domain-policy' },
  general:   { label: 'General', cls: 'domain-general' },
}

const STAGE_ICONS = {
  uploading:  <Loader size={12} className="animate-spin text-gold" />,
  parsing:    <Loader size={12} className="animate-spin text-gold" />,
  ocr:        <Loader size={12} className="animate-spin text-blue-400" />,
  chunking:   <Loader size={12} className="animate-spin text-gold" />,
  embedding:  <Loader size={12} className="animate-spin text-gold" />,
  ready:      <CheckCircle size={12} className="text-emerald-400" />,
  failed:     <AlertCircle size={12} className="text-red-400" />,
}

const STAGE_LABELS = {
  uploading: 'Uploading…',
  parsing:   'Parsing PDF…',
  ocr:       'OCR…',
  chunking:  'Chunking…',
  embedding: 'Embedding…',
  ready:     'Ready',
  failed:    'Failed',
}

function pollStatus(docId, updateFn, onDone) {
  let attempts = 0
  const interval = setInterval(async () => {
    try {
      const status = await getDocumentStatus(docId)
      updateFn(docId, status.stage, status.progress)
      if (status.stage === 'ready' || status.stage === 'failed') {
        clearInterval(interval)
        onDone(status.stage)
      }
      if (++attempts > 120) clearInterval(interval) // 4min timeout
    } catch { clearInterval(interval) }
  }, 2000)
}

export default function Sidebar() {
  const { sidebarOpen, setSidebarOpen, documents, addDocument, removeDocument,
          toggleDocumentSelection, selectedDocIds, activeDocId, setActiveDoc,
          updateDocumentStage } = useStore()
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback(async (accepted) => {
    const pdfs = accepted.filter(f => f.name.toLowerCase().endsWith('.pdf'))
    if (!pdfs.length) { toast.error('Only PDF files are supported'); return }

    setUploading(true)
    for (const file of pdfs) {
      try {
        const res = await uploadDocument(file)
        addDocument({
          doc_id: res.doc_id,
          filename: res.filename,
          domain: 'general',
          processing_stage: 'parsing',
          progress: 10,
          page_count: 0,
        })
        toast(`Processing "${file.name}"`, { icon: '📄' })

        pollStatus(
          res.doc_id,
          updateDocumentStage,
          (stage) => {
            if (stage === 'ready') toast.success(`"${file.name}" is ready`)
            else toast.error(`"${file.name}" processing failed`)
          }
        )
      } catch (e) {
        toast.error(`Upload failed: ${e.message}`)
      }
    }
    setUploading(false)
  }, [addDocument, updateDocumentStage])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'] }, multiple: true,
  })

  const handleDelete = async (e, docId, filename) => {
    e.stopPropagation()
    try {
      await deleteDocument(docId)
      removeDocument(docId)
      toast(`Removed "${filename}"`)
    } catch { toast.error('Delete failed') }
  }

  return (
    <>
      {/* Collapse toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed left-0 top-1/2 -translate-y-1/2 z-30 flex items-center justify-center w-5 h-10 bg-sidebar-bg text-white/50 hover:text-white rounded-r-md transition-all hover:w-6"
        style={{ left: sidebarOpen ? '280px' : '0px' }}
      >
        {sidebarOpen ? <ChevronLeft size={12} /> : <ChevronRight size={12} />}
      </button>

      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed left-0 top-0 bottom-0 w-[280px] bg-sidebar-bg z-20 flex flex-col shadow-sidebar"
          >
            {/* Header */}
            <div className="px-5 py-5 border-b border-white/8">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-md bg-gold/20 flex items-center justify-center">
                  <BookOpen size={14} className="text-gold" />
                </div>
                <div>
                  <h1 className="font-display text-white text-base font-medium tracking-wide">Scriptorium</h1>
                  <p className="text-white/35 text-2xs font-mono tracking-widest uppercase">Research OS</p>
                </div>
              </div>
            </div>

            {/* Upload Zone */}
            <div className="px-4 pt-4">
              <div
                {...getRootProps()}
                className={clsx(
                  'border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all duration-200',
                  isDragActive
                    ? 'border-gold/60 bg-gold/10'
                    : 'border-white/15 hover:border-white/30 hover:bg-white/5'
                )}
              >
                <input {...getInputProps()} />
                <Upload size={18} className={clsx('mx-auto mb-1.5', isDragActive ? 'text-gold' : 'text-white/30')} />
                <p className="text-white/50 text-xs">
                  {isDragActive ? 'Drop PDFs here' : 'Drop PDFs or click to upload'}
                </p>
                {uploading && <p className="text-gold text-xs mt-1 animate-pulse">Uploading…</p>}
              </div>
            </div>

            {/* Document List */}
            <div className="flex-1 overflow-y-auto sidebar-scroll px-3 py-3">
              <div className="flex items-center justify-between px-2 mb-2">
                <p className="text-white/35 text-2xs font-mono uppercase tracking-widest">
                  Library ({documents.length})
                </p>
                {selectedDocIds.length > 0 && (
                  <span className="text-gold text-2xs">{selectedDocIds.length} selected</span>
                )}
              </div>

              <div className="space-y-1">
                {documents.length === 0 && (
                  <div className="text-center py-10">
                    <FileText size={28} className="text-white/15 mx-auto mb-2" />
                    <p className="text-white/25 text-xs">No documents yet</p>
                  </div>
                )}

                {documents.map((doc) => {
                  const isActive = doc.doc_id === activeDocId
                  const isSelected = selectedDocIds.includes(doc.doc_id)
                  const isReady = doc.processing_stage === 'ready'
                  const domainInfo = DOMAIN_LABELS[doc.domain] || DOMAIN_LABELS.general

                  return (
                    <motion.div
                      key={doc.doc_id}
                      layout
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={clsx(
                        'group flex items-start gap-2 p-2.5 rounded-lg cursor-pointer transition-all duration-150',
                        isActive ? 'bg-sidebar-active' : 'hover:bg-sidebar-hover'
                      )}
                      onClick={() => setActiveDoc(doc.doc_id)}
                    >
                      {/* Selection checkbox */}
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleDocumentSelection(doc.doc_id) }}
                        className="mt-0.5 shrink-0 text-white/30 hover:text-gold transition-colors"
                      >
                        {isSelected
                          ? <CheckSquare size={14} className="text-gold" />
                          : <Square size={14} />}
                      </button>

                      <div className="flex-1 min-w-0">
                        {/* Filename */}
                        <p className={clsx(
                          'text-xs font-medium truncate leading-tight',
                          isActive ? 'text-white' : 'text-white/75'
                        )}>
                          {doc.filename}
                        </p>

                        {/* Stage + domain */}
                        <div className="flex items-center gap-1.5 mt-1">
                          <span className="flex items-center gap-1 text-2xs text-white/40">
                            {STAGE_ICONS[doc.processing_stage]}
                            {STAGE_LABELS[doc.processing_stage]}
                          </span>
                          {isReady && doc.domain && (
                            <span className={clsx('text-2xs px-1.5 py-px rounded-full font-medium', domainInfo.cls)}>
                              {domainInfo.label}
                            </span>
                          )}
                        </div>

                        {/* Progress bar */}
                        {!isReady && doc.processing_stage !== 'failed' && (
                          <div className="mt-1.5 h-0.5 bg-white/10 rounded-full overflow-hidden">
                            <motion.div
                              className="h-full bg-gold/60 rounded-full"
                              initial={{ width: 0 }}
                              animate={{ width: `${doc.progress || 15}%` }}
                              transition={{ duration: 0.5 }}
                            />
                          </div>
                        )}
                      </div>

                      {/* Delete */}
                      <button
                        onClick={(e) => handleDelete(e, doc.doc_id, doc.filename)}
                        className="shrink-0 opacity-0 group-hover:opacity-100 text-white/25 hover:text-red-400 transition-all mt-0.5"
                      >
                        <Trash2 size={12} />
                      </button>
                    </motion.div>
                  )
                })}
              </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-white/8">
              {selectedDocIds.length > 0 ? (
                <div className="flex items-center gap-2 text-xs text-white/50">
                  <Zap size={11} className="text-gold" />
                  <span>{selectedDocIds.length} doc{selectedDocIds.length > 1 ? 's' : ''} active in chat</span>
                </div>
              ) : (
                <p className="text-xs text-white/25">Select documents to query</p>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}
