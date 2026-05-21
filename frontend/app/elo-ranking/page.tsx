'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { createClient } from '@/lib/supabase/client'
import apiClient from '@/lib/api'
import Link from 'next/link'

interface TeamRanking {
  rank: number
  team: string
  elo: number
  conference: string
  wins: number
  losses: number
  win_pct: number
}

const CONFERENCES = [
  { key: 'all', label: 'Combined' },
  { key: 'east', label: 'Eastern' },
  { key: 'west', label: 'Western' },
]

export default function EloRankingPage() {
  const { user, loading: authLoading } = useAuth()
  const [teams, setTeams] = useState<TeamRanking[]>([])
  const [conference, setConference] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
      return
    }
    if (user) fetchRankings()
  }, [user, authLoading, router, conference])

  const fetchRankings = async () => {
    try {
      setLoading(true)
      const res = await apiClient.get(`/elo/rankings?conference=${conference}`, {
        headers: {
          Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        },
      })
      setTeams(res.data.teams || [])
      setError(null)
    } catch (err) {
      console.error('Error fetching Elo rankings:', err)
      setError('Failed to load rankings')
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
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-8">
            <h1 className="text-2xl font-bold text-white">HoopsQuant</h1>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-gray-400 hover:text-white font-medium">Dashboard</Link>
              <Link href="/elo-ranking" className="text-emerald-400 font-medium">Elo Rankings</Link>
              <Link href="/arbitrage" className="text-gray-400 hover:text-white font-medium">Arbitrage</Link>
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
        <div className="mb-8">
          <h2 className="text-4xl font-bold text-white mb-2">Elo Rankings</h2>
          <p className="text-gray-400">Live power ratings based on game results and margin of victory</p>
        </div>

        {error && (
          <div className="bg-red-900 border border-red-700 rounded-lg p-4 mb-8 text-red-200">{error}</div>
        )}

        <div className="flex gap-2 mb-8">
          {CONFERENCES.map((c) => (
            <button
              key={c.key}
              onClick={() => setConference(c.key)}
              className={`px-5 py-2 rounded-lg text-sm font-semibold transition ${
                conference === c.key
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-800 text-gray-400 hover:text-white border border-slate-700'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500" />
          </div>
        ) : teams.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-8 text-center border border-slate-700">
            <p className="text-gray-400 text-lg">No rankings available yet</p>
            <p className="text-gray-500 text-sm mt-2">Completed games are needed to compute Elo ratings</p>
          </div>
        ) : (
          <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-slate-700 bg-slate-700">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Rank</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Team</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-300">Elo</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-300">Record</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-300">Win %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {teams.map((t) => (
                  <tr key={t.team} className="hover:bg-slate-700 transition">
                    <td className="px-6 py-4">
                      <span className={`text-lg font-bold ${
                        t.rank <= 3 ? 'text-emerald-400' : 'text-gray-400'
                      }`}>
                        #{t.rank}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="text-white font-bold text-lg">{t.team}</span>
                        <span className={`text-xs uppercase px-2 py-0.5 rounded-full ${
                          t.conference === 'east'
                            ? 'bg-blue-900/40 text-blue-400'
                            : 'bg-orange-900/40 text-orange-400'
                        }`}>
                          {t.conference === 'east' ? 'East' : 'West'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="text-emerald-400 font-bold text-lg">{t.elo.toFixed(1)}</span>
                    </td>
                    <td className="px-6 py-4 text-right text-gray-300 font-semibold">
                      {t.wins}-{t.losses}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="text-gray-300 font-semibold">
                        {(t.win_pct * 100).toFixed(1)}%
                      </span>
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
