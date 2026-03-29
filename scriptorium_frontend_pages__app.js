import '../styles/globals.css'
import { Toaster } from 'react-hot-toast'

export default function App({ Component, pageProps }) {
  return (
    <>
      <Component {...pageProps} />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.85rem',
            background: '#1C1C1C',
            color: '#F8F6F2',
            borderRadius: '8px',
            padding: '10px 14px',
          },
          success: { iconTheme: { primary: '#D4AF37', secondary: '#1C1C1C' } },
          error: { iconTheme: { primary: '#6D2E2E', secondary: '#F8F6F2' } },
        }}
      />
    </>
  )
}
