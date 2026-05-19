# HoopsQuant Frontend

A modern Next.js application for NBA betting predictions and arbitrage detection.

## Features

- 🎯 **Dashboard**: Today's AI-powered game picks with confidence scores
- 💰 **Arbitrage Scanner**: Find guaranteed profit opportunities across bookmakers
- 📊 **My Picks**: Track your betting history, wins, losses, and ROI
- 🔐 **OAuth Authentication**: Sign in with Google or GitHub via Supabase
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile

## Tech Stack

- **Framework**: Next.js 16+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Auth**: Supabase Auth (OAuth)
- **API Client**: Axios
- **Animations**: CSS & Framer Motion ready

## Setup

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Create .env.local with your Supabase credentials
cp .env.example .env.local
```

### Environment Variables

```env
# Get these from your Supabase project settings
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Backend API (change in production)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Development

```bash
# Run dev server
npm run dev

# Open http://localhost:3000
```

## Build & Deployment

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

The app will be deployed to Vercel with automatic deployments on git push.

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx              # Landing page with hero animation
│   ├── login/page.tsx        # OAuth login page
│   ├── auth/callback/page.tsx # Auth callback handler
│   ├── dashboard/page.tsx    # Main dashboard (today's picks)
│   ├── arbitrage/page.tsx    # Arbitrage scanner
│   ├── picks/page.tsx        # My picks history & stats
│   ├── layout.tsx            # Root layout
│   └── globals.css           # Global styles
├── lib/
│   ├── supabase/client.ts    # Supabase client setup
│   ├── api.ts                # Axios API client
│   └── hooks/useAuth.ts      # Auth hook
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── .env.example
```

## Key Features

### Authentication
- OAuth with Google and GitHub via Supabase Auth
- Automatic token management in localStorage
- Protected routes redirect to login

### API Integration
- Axios client with automatic token injection
- Handles `/api/v1/dashboard/*` endpoints from backend
- Error handling and loading states

### UI Components
- Dark theme with slate colors
- Responsive grid layouts
- Loading spinners and error states
- Interactive cards with hover effects

## Dashboard Pages

### 1. Landing Page (`/`)
- Hero section with animations
- Feature highlights
- Pricing tiers
- Sign up call-to-action

### 2. Login (`/login`)
- OAuth buttons (Google/GitHub)
- Guest mode option
- Beautiful auth card design

### 3. Dashboard (`/dashboard`)
- Today's upcoming games
- AI prediction confidence scores
- Best odds display
- Place pick buttons

### 4. Arbitrage (`/arbitrage`)
- Guaranteed profit opportunities
- ROI statistics
- Bookmaker comparisons
- Take opportunity buttons

### 5. My Picks (`/picks`)
- Betting history table
- Win/loss/pending status
- Profit/loss tracking
- Overall ROI percentage

## Customization

### Update Branding
Edit these files to change colors/fonts:
- `app/globals.css` - Colors, fonts
- `tailwind.config.ts` - Tailwind theme
- `app/page.tsx` - Landing page content

### Add More Pages
```bash
mkdir app/newpage
touch app/newpage/page.tsx
```

## Troubleshooting

### Build fails with "Module not found"
```bash
npm install  # Reinstall dependencies
npm run build
```

### Supabase auth not working
1. Check `.env.local` has correct URL and key
2. Verify OAuth apps are configured in Supabase
3. Check redirect URL includes `/auth/callback`

### API calls failing
1. Ensure backend is running on `localhost:8000`
2. Check `NEXT_PUBLIC_API_URL` environment variable
3. Verify backend CORS allows frontend origin

## Production Checklist

- [ ] Update `NEXT_PUBLIC_API_URL` to production backend
- [ ] Update `NEXT_PUBLIC_SUPABASE_URL` to production Supabase
- [ ] Set up custom domain
- [ ] Enable HTTPS
- [ ] Configure OAuth redirect URLs
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Configure analytics

## Support

For issues or questions, check:
- `/docs/SETUP.md` - More detailed setup
- Backend API documentation
- Supabase auth docs: https://supabase.com/docs/guides/auth

---

Built with ❤️ for NBA bettors
