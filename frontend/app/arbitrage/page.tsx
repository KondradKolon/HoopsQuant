'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { createClient } from '@/lib/supabase/client'
import apiClient from '@/lib/api'
import Link from 'next/link'

interface ArbitrageOpportunity {
  game_id: string
  home_team: string
  away_team: string
  game_date: string
  bookmaker_1: string
  bookmaker_2: string
  bet_1: string // "home" or "away"
  bet_2: string
  odds_1: number
  odds_2: number
  guaranteed_roi: number
  wager_amount?: number
}

export default function ArbitragePage() {
  const { user, loading: authLoading } = useAuth()
  const [opportunities, setOpportunities] = useState<ArbitrageOpportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
      return
    }

    if (user) {
      fetchArbitrage()
    }
  }, [user, authLoading, router])

  const fetchArbitrage = async () => {
    try {
      setLoading(true)
      const response = await apiClient.get('/dashboard/arbitrage', {
        headers: {
          Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        },
      })
      setOpportunities(response.data.opportunities || [])
      setError(null)
    } catch (err) {
      console.error('Error fetching arbitrage:', err)
      setError('Failed to load arbitrage opportunities')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <div className="min-h-screen quant-grid">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-8">
            <h1 className="text-2xl font-bold text-white">HoopsQuant</h1>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-gray-400 hover:text-white font-medium">
                Dashboard
              </Link>
              <Link href="/arbitrage" className="text-emerald-400 font-medium">
                Arbitrage
              </Link>
              <Link href="/picks" className="text-gray-400 hover:text-white font-medium">
                My Picks
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="mb-12">
          <h2 className="text-4xl font-bold text-white mb-2">Arbitrage Opportunities</h2>
          <p className="text-gray-400">Guaranteed profit opportunities across bookmakers</p>
        </div>

        {error && (
          <div className="bg-red-900 border border-red-700 rounded-lg p-4 mb-8 text-red-200">
            {error}
          </div>
        )}

        {/* Stats */}
        {!loading && opportunities.length > 0 && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-gray-400">Total Opportunities</div>
              <div className="text-3xl font-bold text-green-400 mt-1">{opportunities.length}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-gray-400">Average ROI</div>
              <div className="text-3xl font-bold text-green-400 mt-1">
                {(
                  opportunities.reduce((sum, opp) => sum + opp.guaranteed_roi, 0) /
                  opportunities.length
                ).toFixed(2)}
                %
              </div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-gray-400">Best ROI</div>
              <div className="text-3xl font-bold text-green-400 mt-1">
                {Math.max(...opportunities.map((o) => o.guaranteed_roi)).toFixed(2)}%
              </div>
            </div>
          </div>
        )}

        {/* Opportunities Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500" />
          </div>
        ) : opportunities.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-8 text-center border border-slate-700">
            <p className="text-gray-400 text-lg">No arbitrage opportunities at the moment</p>
            <p className="text-gray-500 text-sm mt-2">Check back later for guaranteed profit opportunities</p>
          </div>
        ) : (
          <div className="grid gap-6">
            {opportunities.map((opp) => (
              <div
                key={opp.game_id}
                className="bg-slate-800 rounded-lg border border-green-600 border-opacity-30 p-6 hover:border-opacity-100 transition"
              >
                <div className="grid grid-cols-4 gap-4 mb-4">
                  {/* Game Info */}
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Game</div>
                    <div className="text-white font-semibold">
                      {opp.home_team} vs {opp.away_team}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {new Date(opp.game_date).toLocaleDateString()}
                    </div>
                  </div>

                  {/* Bet 1 */}
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Bet 1 ({opp.bookmaker_1})</div>
                    <div className="text-white font-semibold capitalize">{opp.bet_1}</div>
                    <div className="text-green-400 font-bold">{opp.odds_1}</div>
                  </div>

                  {/* Bet 2 */}
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Bet 2 ({opp.bookmaker_2})</div>
                    <div className="text-white font-semibold capitalize">{opp.bet_2}</div>
                    <div className="text-green-400 font-bold">{opp.odds_2}</div>
                  </div>

                  {/* ROI */}
                  <div className="text-right">
                    <div className="text-sm text-gray-400 mb-1">Guaranteed ROI</div>
                    <div className="text-3xl font-bold text-green-400">
                      {opp.guaranteed_roi.toFixed(2)}%
                    </div>
                  </div>
                </div>

                {/* Action */}
                <div className="flex gap-2 pt-4 border-t border-slate-700">
                  <button className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg transition font-semibold">
                    Take Opportunity
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
