'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'

export default function AuthCallbackPage() {
  const router = useRouter()

  useEffect(() => {
    const handleCallback = async () => {
      const supabase = createClient()
      
      // Get the session from the URL
      const { data, error } = await supabase.auth.getSession()
      
      if (error || !data.session) {
        console.error('Auth error:', error)
        router.push('/login')
        return
      }

      // Store token in localStorage for API requests
      if (data.session.access_token) {
        localStorage.setItem('sb-token', data.session.access_token)
      }

      // Redirect to dashboard
      router.push('/dashboard')
    }

    handleCallback()
  }, [router])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Setting up your account...</h2>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
      </div>
    </div>
  )
}
