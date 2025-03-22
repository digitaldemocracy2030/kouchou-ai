'use client'

import { useEffect } from 'react'
import ClientProvider from './ClientProvider'
import './global.css'
import { getApiBaseUrl } from './utils/api'

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  useEffect(() => {
    const script = document.createElement('script')
    script.src = '/js/plotly-locale-ja.js'
    script.async = true
    document.body.appendChild(script)
  }, [])

  return (
    <html suppressHydrationWarning lang='ja'>
      <head>
        <link rel='icon' href={getApiBaseUrl() + '/meta/icon.png'} sizes='any' />
      </head>
      <body>
        <ClientProvider>
          {children}
        </ClientProvider>
      </body>
    </html>
  )
}
