import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'OptiSchema - AI-Powered PostgreSQL Optimization',
  description: 'Monitor PostgreSQL workloads, identify performance bottlenecks, and get actionable optimization recommendations.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}