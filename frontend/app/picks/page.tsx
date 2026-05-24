'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { createClient } from '@/lib/supabase/client'
import apiClient from '@/lib/api'
import Link from 'next/link'
import TeamLogo from '@/components/TeamLogo'
import { getTeam } from '@/lib/teams'

interface Pick {
  id: number
  game_id: string
  home_team: string
  away_team: string
  game_date: string
  pick_team: string
  odds: number
  stake: number
  result?: string
  profit?: number
}

export default function PicksPage() {
  const { user, loading: authLoading } = useAuth()
  const [picks, setPicks] = useState<Pick[]>([])
  const [stats, setStats] = useState({ total: 0, wins: 0, roi: 0 })
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
      fetchPicks()
      fetchStats()
    }
  }, [user, authLoading, router])

  const fetchPicks = async () => {
    try {
      const response = await apiClient.get('/dashboard/picks', {
        headers: {
          Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        },
      })
      setPicks(Array.isArray(response.data) ? response.data : response.data.picks || [])
    } catch (err) {
      console.error('Error fetching picks:', err)
    }
  }

  const fetchStats = async () => {
    try {
      setLoading(true)
      const response = await apiClient.get('/dashboard/picks/stats', {
        headers: {
          Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        },
      })
      const d = response.data
      setStats({ total: d.total_picks || d.total || 0, wins: d.wins || 0, roi: d.roi || 0 })
    } catch (err) {
      console.error('Error fetching stats:', err)
      setError('Failed to load statistics')
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
              <Link href="/elo-ranking" className="text-gray-400 hover:text-white font-medium">
                Elo
              </Link>
              <Link href="/arbitrage" className="text-gray-400 hover:text-white font-medium">
                Arbitrage
              </Link>
              <Link href="/picks" className="text-emerald-400 font-medium">
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
          <h2 className="text-4xl font-bold text-white mb-2">My Picks</h2>
          <p className="text-gray-400">Track your betting history and ROI</p>
        </div>

        {error && (
          <div className="bg-red-900 border border-red-700 rounded-lg p-4 mb-8 text-red-200">
            {error}
          </div>
        )}

        {/* Stats */}
        {!loading && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-gray-400">Total Picks</div>
              <div className="text-3xl font-bold text-emerald-400 mt-1">{stats.total}</div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-gray-400">Wins</div>
              <div className="text-3xl font-bold text-green-400 mt-1">
                {stats.wins}
                {stats.total > 0 && ` (${((stats.wins / stats.total) * 100).toFixed(1)}%)`}
              </div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <div className="text-sm text-gray-400">ROI</div>
              <div className={`text-3xl font-bold mt-1 ${stats.roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {stats.roi.toFixed(2)}%
              </div>
            </div>
          </div>
        )}

        {/* Picks Table */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500" />
          </div>
        ) : picks.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-8 text-center border border-slate-700">
            <p className="text-gray-400 text-lg">No picks yet</p>
            <p className="text-gray-500 text-sm mt-2">
              Head to the <Link href="/dashboard" className="text-emerald-400 hover:underline">Dashboard</Link> to place your first pick
            </p>
          </div>
        ) : (
          <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-slate-700 bg-slate-700">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Game</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Pick</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Odds</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Stake</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Result</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Profit</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {picks.map((pick) => (
                  <tr key={pick.id} className="hover:bg-slate-700 transition">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <TeamLogo abbr={pick.home_team} size="sm" showName="abbr" />
                        <span className="text-gray-500 text-xs">vs</span>
                        <TeamLogo abbr={pick.away_team} size="sm" showName="abbr" />
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <TeamLogo abbr={pick.pick_team} size="sm" showName="short" />
                    </td>
                    <td className="px-6 py-4 text-emerald-400">{pick.odds}</td>
                    <td className="px-6 py-4 text-white">${pick.stake}</td>
                    <td className="px-6 py-4">
                      {pick.result ? (
                        <span
                          className={`px-3 py-1 rounded-full text-sm font-semibold ${
                            pick.result === 'WIN'
                              ? 'bg-green-900 text-green-300'
                              : pick.result === 'LOSS'
                              ? 'bg-red-900 text-red-300'
                              : 'bg-gray-700 text-gray-300'
                          }`}
                        >
                          {pick.result}
                        </span>
                      ) : (
                        <span className="px-3 py-1 rounded-full text-sm font-semibold bg-yellow-900 text-yellow-300">
                          PENDING
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-semibold">
                      {pick.profit ? (
                        <span className={pick.profit >= 0 ? 'text-green-400' : 'text-red-400'}>
                          {pick.profit >= 0 ? '+' : ''}${pick.profit}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-gray-400 text-sm">
                      {new Date(pick.game_date).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
