import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import { AppRoutes } from '@/app/routes'
import { initI18n } from '@/lib/i18n'
import { queryClient } from '@/lib/queryClient'
import { applyTheme, readStoredTheme } from '@/ui/theme'
import '@/styles.css'

// Language and theme before the first paint: Arabic is the default, so getting
// this wrong would show a left-to-right frame that then flips.
initI18n()
applyTheme(readStoredTheme())

const container = document.getElementById('root')
if (!container) throw new Error('#root is missing from index.html')

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
