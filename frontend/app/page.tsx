'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { useEffect, useState } from 'react'

export default function Home() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  useEffect(() => {
    if (!loading && user) {
      router.push('/dashboard')
    }
  }, [user, loading, router])

  return (
    <div className="min-h-screen quant-grid">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 backdrop-blur-md border-b border-slate-800/80 bg-slate-950/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="text-xs uppercase tracking-[0.4em] text-slate-500 text-mono">HQ</div>
            <h1 className="text-2xl font-semibold text-white">HoopsQuant</h1>
          </div>
          <div className="hidden md:flex gap-4 items-center">
            <span className="text-xs text-slate-500 text-mono">Markets: Live · NBA</span>
            <Link
              href="/login"
              className="text-slate-400 hover:text-white transition font-medium"
            >
              Sign In
            </Link>
            <Link
              href="/login"
              className="quant-chip px-5 py-2 rounded-lg text-sm font-semibold transition"
            >
              Get Started
            </Link>
          </div>
          <div className="md:hidden">
            <button
              type="button"
              onClick={() => setIsMenuOpen((open) => !open)}
              className="border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm"
            >
              Menu
            </button>
          </div>
        </div>
        {isMenuOpen && (
          <div className="md:hidden border-t border-slate-800/80 bg-slate-950/80">
            <div className="px-4 py-4 flex flex-col gap-3">
              <span className="text-xs text-slate-500 text-mono">Markets: Live · NBA</span>
              <Link
                href="/login"
                className="text-slate-300 hover:text-white transition font-medium"
              >
                Sign In
              </Link>
              <Link
                href="/login"
                className="quant-chip px-4 py-2 rounded-lg text-sm font-semibold text-center"
              >
                Get Started
              </Link>
            </div>
          </div>
        )}
      </nav>

      {/* Main Content */}
      <div className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Hero Section with Animation */}
          <div className="space-y-12">
            {/* Animated Hero */}
            <div className="space-y-6 text-center animate-fade-in-up">
              <div className="flex justify-center">
                <div className="quant-chip text-xs uppercase tracking-[0.3em] px-4 py-1 rounded-full text-mono">
                  Quant Edge
                </div>
              </div>
              <h2 className="text-5xl md:text-6xl font-semibold text-white leading-tight">
                Smart NBA
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-emerald-200 to-emerald-400">
                  Alpha, not noise
                </span>
              </h2>
              <p className="text-lg text-slate-300 max-w-3xl mx-auto">
                Predictive models, sharp line monitoring, and arbitrage detection focused on consistent, data‑backed ROI.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center mt-12 animate-fade-in-up-delay">
              <Link
                href="/login"
                className="bg-emerald-400 text-slate-950 px-8 py-4 rounded-lg font-semibold text-lg transition hover:bg-emerald-300"
              >
                Start Free Trial
              </Link>
              <button className="border border-slate-600 hover:border-emerald-300 text-slate-200 px-8 py-4 rounded-lg font-semibold text-lg transition">
                Watch Demo
              </button>
            </div>

            {/* Feature Highlights */}
            <div className="grid md:grid-cols-3 gap-8 mt-20 pt-12 border-t border-slate-800">
              <div className="quant-panel rounded-2xl p-8 hover:border-emerald-400 transition">
                <div className="text-xs text-slate-500 text-mono uppercase tracking-[0.25em]">Model</div>
                <h3 className="text-xl font-semibold text-white mb-2 mt-3">AI Predictions</h3>
                <p className="text-slate-400">
                  Multi‑season model tuned for probability edge and confidence calibration.
                </p>
              </div>

              <div className="quant-panel rounded-2xl p-8 hover:border-emerald-400 transition">
                <div className="text-xs text-slate-500 text-mono uppercase tracking-[0.25em]">Arb</div>
                <h3 className="text-xl font-semibold text-white mb-2 mt-3">Guaranteed Profits</h3>
                <p className="text-slate-400">
                  Cross‑bookmaker scanning finds mispriced lines and locks EV.
                </p>
              </div>

              <div className="quant-panel rounded-2xl p-8 hover:border-emerald-400 transition">
                <div className="text-xs text-slate-500 text-mono uppercase tracking-[0.25em]">Tracking</div>
                <h3 className="text-xl font-semibold text-white mb-2 mt-3">ROI Monitoring</h3>
                <p className="text-slate-400">
                  Real‑time win rates, drift detection, and performance analytics.
                </p>
              </div>
            </div>

            {/* Pricing Preview */}
            <div className="mt-20 pt-12 border-t border-slate-800">
              <h3 className="text-3xl font-semibold text-white text-center mb-12">Simple Pricing</h3>
              <div className="grid md:grid-cols-3 gap-8">
                {/* Free Tier */}
                <div className="quant-panel rounded-2xl p-8">
                  <h4 className="text-xl font-bold text-white mb-4">Free</h4>
                  <div className="text-3xl font-bold text-white mb-6">$0<span className="text-sm text-slate-500">/mo</span></div>
                  <ul className="space-y-3 text-slate-300 mb-8">
                    <li>✓ Today's top picks</li>
                    <li>✓ AI predictions</li>
                    <li>✓ Basic stats</li>
                    <li>✗ Arbitrage scanner</li>
                    <li>✗ Advanced alerts</li>
                  </ul>
                  <button className="w-full border border-slate-600 text-white py-2 rounded-lg hover:border-emerald-300 transition">
                    Get Started
                  </button>
                </div>

                {/* Pro Tier - Highlighted */}
                <div className="quant-panel rounded-2xl p-8 border-2 border-emerald-400/70 transform md:scale-105">
                  <div className="bg-emerald-400 text-slate-900 px-3 py-1 rounded-full text-sm font-bold w-fit mb-4">
                    Most Popular
                  </div>
                  <h4 className="text-xl font-bold text-white mb-4">Pro</h4>
                  <div className="text-3xl font-bold text-white mb-6">$9.99<span className="text-sm text-emerald-200">/mo</span></div>
                  <ul className="space-y-3 text-slate-100 mb-8">
                    <li>✓ Everything in Free</li>
                    <li>✓ Arbitrage scanner</li>
                    <li>✓ Real-time alerts</li>
                    <li>✓ Line tracking</li>
                    <li>✗ SMS notifications</li>
                  </ul>
                  <button className="w-full bg-emerald-400 text-slate-950 font-semibold py-2 rounded-lg hover:bg-emerald-300 transition">
                    Start Free Trial
                  </button>
                </div>

                {/* Premium Tier */}
                <div className="quant-panel rounded-2xl p-8">
                  <h4 className="text-xl font-bold text-white mb-4">Premium</h4>
                  <div className="text-3xl font-bold text-white mb-6">$29.99<span className="text-sm text-slate-500">/mo</span></div>
                  <ul className="space-y-3 text-slate-300 mb-8">
                    <li>✓ Everything in Pro</li>
                    <li>✓ SMS notifications</li>
                    <li>✓ API access</li>
                    <li>✓ Priority support</li>
                    <li>✓ Custom alerts</li>
                  </ul>
                  <button className="w-full border border-slate-600 text-white py-2 rounded-lg hover:border-emerald-300 transition">
                    Coming Soon
                  </button>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="mt-20 pt-12 border-t border-slate-800 grid md:grid-cols-4 gap-8 text-center">
              <div>
                <div className="text-4xl font-semibold text-emerald-300">1,310+</div>
                <div className="text-slate-400 mt-2 text-mono text-xs uppercase tracking-[0.2em]">Games</div>
              </div>
              <div>
                <div className="text-4xl font-semibold text-emerald-300">65%</div>
                <div className="text-slate-400 mt-2 text-mono text-xs uppercase tracking-[0.2em]">Win Rate</div>
              </div>
              <div>
                <div className="text-4xl font-semibold text-emerald-300">5+</div>
                <div className="text-slate-400 mt-2 text-mono text-xs uppercase tracking-[0.2em]">Books</div>
              </div>
              <div>
                <div className="text-4xl font-semibold text-emerald-300">2,000+</div>
                <div className="text-slate-400 mt-2 text-mono text-xs uppercase tracking-[0.2em]">Training</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-20 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center text-slate-500 text-sm text-mono">
          <p>© 2026 HoopsQuant. All rights reserved. | Responsible Gambling</p>
        </div>
      </footer>

      {/* Animations */}
      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeInUpDelay {
          0% {
            opacity: 0;
            transform: translateY(20px);
          }
          50% {
            opacity: 0;
            transform: translateY(20px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fade-in-up {
          animation: fadeInUp 0.8s ease-out;
        }

        .animate-fade-in-up-delay {
          animation: fadeInUpDelay 1.2s ease-out;
        }
      `}</style>
    </div>
  )
}
