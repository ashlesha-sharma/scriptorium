import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // ── Documents ───────────────────────────────────────────
  documents: [],
  selectedDocIds: [],
  activeDocId: null,

  setDocuments: (docs) => set({ documents: docs }),
  
  addDocument: (doc) => set((s) => ({
    documents: [doc, ...s.documents],
    selectedDocIds: [...s.selectedDocIds, doc.doc_id],
    activeDocId: doc.doc_id,
  })),

  updateDocumentStage: (doc_id, stage, progress) => set((s) => ({
    documents: s.documents.map(d =>
      d.doc_id === doc_id ? { ...d, processing_stage: stage, progress } : d
    ),
  })),

  removeDocument: (doc_id) => set((s) => ({
    documents: s.documents.filter(d => d.doc_id !== doc_id),
    selectedDocIds: s.selectedDocIds.filter(id => id !== doc_id),
    activeDocId: s.activeDocId === doc_id
      ? s.documents.find(d => d.doc_id !== doc_id)?.doc_id || null
      : s.activeDocId,
  })),

  toggleDocumentSelection: (doc_id) => set((s) => ({
    selectedDocIds: s.selectedDocIds.includes(doc_id)
      ? s.selectedDocIds.filter(id => id !== doc_id)
      : [...s.selectedDocIds, doc_id],
  })),

  setActiveDoc: (doc_id) => set({ activeDocId: doc_id }),

  // ── Chat ────────────────────────────────────────────────
  sessions: {},        // sessionId → messages[]
  activeSessionId: 'default',

  getMessages: () => {
    const s = get()
    return s.sessions[s.activeSessionId] || []
  },

  addMessage: (message) => set((s) => {
    const sid = s.activeSessionId
    const existing = s.sessions[sid] || []
    return {
      sessions: {
        ...s.sessions,
        [sid]: [...existing, message],
      }
    }
  }),

  updateLastMessage: (partial) => set((s) => {
    const sid = s.activeSessionId
    const msgs = s.sessions[sid] || []
    if (!msgs.length) return {}
    const updated = [...msgs]
    updated[updated.length - 1] = { ...updated[updated.length - 1], ...partial }
    return { sessions: { ...s.sessions, [sid]: updated } }
  }),

  clearSession: () => set((s) => ({
    sessions: { ...s.sessions, [s.activeSessionId]: [] }
  })),

  // ── UI State ────────────────────────────────────────────
  sidebarOpen: true,
  setSidebarOpen: (v) => set({ sidebarOpen: v }),

  highlightedText: null,
  setHighlightedText: (text) => set({ highlightedText: text }),

  queryMode: 'conversational',
  setQueryMode: (mode) => set({ queryMode: mode }),

  explainLevel: 'expert',
  setExplainLevel: (level) => set({ explainLevel: level }),

  isQuerying: false,
  setIsQuerying: (v) => set({ isQuerying: v }),
}))
