import { useEffect } from 'react'
import { motion } from 'framer-motion'
import Head from 'next/head'
import Sidebar from '../components/Layout/Sidebar'
import TopBar from '../components/Layout/TopBar'
import DocumentViewer from '../components/Document/DocumentViewer'
import ChatPanel from '../components/Chat/ChatPanel'
import { useStore } from '../lib/store'
import { listDocuments } from '../lib/api'

export default function Home() {
  const { sidebarOpen, setDocuments } = useStore()

  // Load existing documents on mount
  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch(() => {})
  }, [])

  return (
    <>
      <Head>
        <title>Scriptorium — Research Intelligence</title>
      </Head>

      <div className="h-screen flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main content area */}
        <motion.div
          className="flex-1 flex flex-col min-w-0"
          animate={{ marginLeft: sidebarOpen ? '280px' : '0px' }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          {/* Top bar */}
          <TopBar />

          {/* Content below topbar */}
          <div className="flex flex-1 overflow-hidden mt-14">
            {/* Document Viewer — left half */}
            <div className="flex-1 flex flex-col border-r border-border-subtle overflow-hidden">
              <DocumentViewer />
            </div>

            {/* Chat Panel — right half */}
            <div className="w-[44%] min-w-[360px] max-w-[680px] flex flex-col overflow-hidden">
              <ChatPanel />
            </div>
          </div>
        </motion.div>
      </div>
    </>
  )
}
