'use client'

import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { createClient } from '@/lib/supabase/client'
import { useEffect } from 'react'
import Link from 'next/link'

export default function ArbitragePage() {
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    if (!authLoading && !user) router.push('/login')
  }, [user, authLoading, router])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  if (authLoading || !user) return null

  return (
    <div className="min-h-screen quant-grid">
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-8">
            <h1 className="text-2xl font-bold text-white">HoopsQuant</h1>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-gray-400 hover:text-white font-medium">Dashboard</Link>
              <Link href="/elo-ranking" className="text-gray-400 hover:text-white font-medium">Elo</Link>
              <Link href="/arbitrage" className="text-emerald-400 font-medium">Arbitrage</Link>
              <Link href="/picks" className="text-gray-400 hover:text-white font-medium">My Picks</Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">{user?.email}</span>
            <button onClick={handleLogout} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition">Logout</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-xl mx-auto text-center py-20">
          <div className="quant-chip text-xs uppercase tracking-[0.3em] px-4 py-1 rounded-full text-mono inline-block mb-6">
            Coming Soon
          </div>
          <h2 className="text-4xl font-bold text-white mb-4">Arbitrage Scanner</h2>
          <p className="text-slate-400 text-lg mb-8">
            Cross-bookmaker arbitrage detection is in development. We&apos;re scanning live odds
            to find guaranteed profit opportunities across multiple bookmakers.
          </p>
          <div className="quant-panel rounded-2xl p-8 inline-block text-left">
            <div className="space-y-4 text-slate-300">
              <div className="flex items-center gap-3">
                <span className="text-emerald-400 text-lg">✓</span>
                <span>Real-time odds aggregation</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-emerald-400 text-lg">✓</span>
                <span>Automated arbitrage detection</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-emerald-400 text-lg">✓</span>
                <span>Guaranteed ROI calculations</span>
              </div>
              <div className="flex items-center gap-3 text-slate-500">
                <span className="text-lg">○</span>
                <span>Push & SMS alerts <span className="text-xs">(future)</span></span>
              </div>
            </div>
          </div>
          <div className="mt-8">
            <Link
              href="/dashboard"
              className="inline-block bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-3 rounded-lg font-semibold transition"
            >
              Back to Dashboard
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
