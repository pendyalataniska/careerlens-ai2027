import { useState } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  Check,
  Eye,
  EyeOff,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { BrandMark } from '../components/ui/BrandMark'
import { apiClient, getApiErrorMessage } from '../api/client'

type AuthMode = 'login' | 'register'
type AccountRole = 'candidate' | 'recruiter'

export function AuthPage({ mode }: { mode: AuthMode }) {
  const navigate = useNavigate()
  const [role, setRole] = useState<AccountRole>('candidate')
  const [showPassword, setShowPassword] = useState(false)
  const [notice, setNotice] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const isRegister = mode === 'register'

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice('')
    setIsSubmitting(true)
    const formData = new FormData(event.currentTarget)
    try {
      const response = isRegister
        ? await apiClient.post<AuthResponse>('/auth/register', {
            email: formData.get('email'),
            password: formData.get('password'),
            role: role.toUpperCase(),
            full_name: formData.get('name'),
            company_name: role === 'recruiter' ? formData.get('company-name') : undefined,
          })
        : await apiClient.post<AuthResponse>('/auth/login', {
            email: formData.get('email'),
            password: formData.get('password'),
          })
      sessionStorage.setItem('careerlens_access_token', response.data.access_token)
      sessionStorage.setItem('careerlens_role', response.data.user.role)
      navigate('/dashboard')
    } catch (error) {
      setNotice(getApiErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1fr_0.88fr]">
      <section className="relative hidden overflow-hidden bg-[#111128] px-10 py-10 lg:flex lg:flex-col lg:justify-between xl:px-16">
        <div className="pointer-events-none absolute -right-40 top-1/4 size-[500px] rounded-full bg-violet-600/20 blur-[120px]" />
        <div className="pointer-events-none absolute -bottom-32 -left-24 size-[360px] rounded-full bg-indigo-600/20 blur-[100px]" />
        <div className="relative z-10">
          <BrandMark light />
          <div className="mt-[18vh] max-w-lg">
            <span className="inline-flex items-center gap-2 rounded-full border border-violet-300/20 bg-violet-300/10 px-3 py-1.5 text-[10px] font-medium text-violet-200">
              <Sparkles size={13} /> Your career workspace
            </span>
            <h1 className="mt-6 text-5xl font-semibold leading-tight tracking-[-0.04em] text-white">
              Make your next move a more informed one.
            </h1>
            <p className="mt-5 text-sm leading-7 text-slate-300">
              Bring your career goals, experience, and opportunities into focus
              with CareerLens AI.
            </p>
          </div>
        </div>
        <div className="relative z-10">
          <div className="flex gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-emerald-400/10 text-emerald-300"><Check size={17} /></span>
            <div>
              <p className="text-xs font-medium text-white">A workspace built around you</p>
              <p className="mt-1 text-[10px] leading-5 text-slate-400">A thoughtful place to organize your career journey and plan what comes next.</p>
            </div>
          </div>
          <p className="mt-6 text-[9px] text-slate-500">CareerLens AI · Career decisions, grounded in your goals.</p>
        </div>
      </section>

      <section className="flex min-h-screen flex-col px-5 py-6 sm:px-10 lg:px-14 xl:px-20">
        <div className="flex items-center justify-between lg:hidden">
          <BrandMark />
          <Link to="/" aria-label="Back to home" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><ArrowLeft size={17} /></Link>
        </div>
        <div className="mx-auto flex w-full max-w-[420px] flex-1 flex-col justify-center py-10">
          <Link to="/" className="mb-8 hidden w-fit items-center gap-2 text-[11px] text-slate-500 hover:text-violet-700 lg:inline-flex">
            <ArrowLeft size={14} /> Back to home
          </Link>
          <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-violet-600">
            {isRegister ? 'Start your journey' : 'Welcome back'}
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
            {isRegister ? 'Create your account' : 'Sign in to CareerLens'}
          </h2>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            {isRegister
              ? 'Choose your workspace and take your next step.'
              : 'Enter your details to continue to your workspace.'}
          </p>

          {isRegister && (
            <fieldset className="mt-7">
              <legend className="mb-2.5 text-[11px] font-medium text-slate-700">I’m joining as a</legend>
              <div className="grid grid-cols-2 gap-3">
                <RoleCard
                  selected={role === 'candidate'}
                  icon={<UserRound size={17} />}
                  title="Candidate"
                  description="Explore your next role"
                  onClick={() => setRole('candidate')}
                />
                <RoleCard
                  selected={role === 'recruiter'}
                  icon={<BriefcaseBusiness size={17} />}
                  title="Recruiter"
                  description="Find great candidates"
                  onClick={() => setRole('recruiter')}
                />
              </div>
            </fieldset>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {isRegister && (
              <div>
                <label htmlFor="full-name" className="mb-1.5 block text-[11px] font-medium text-slate-700">Full name</label>
                <input id="full-name" name="name" autoComplete="name" required placeholder="Jordan Davis" className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-xs text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10" />
              </div>
            )}
            {isRegister && role === 'recruiter' && (
              <div>
                <label htmlFor="company-name" className="mb-1.5 block text-[11px] font-medium text-slate-700">Company name</label>
                <input id="company-name" name="company-name" autoComplete="organization" required placeholder="Acme Inc." className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-xs text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10" />
              </div>
            )}
            <div>
              <label htmlFor="email" className="mb-1.5 block text-[11px] font-medium text-slate-700">Email address</label>
              <input id="email" name="email" type="email" autoComplete="email" required placeholder="you@example.com" className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-xs text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10" />
            </div>
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label htmlFor="password" className="text-[11px] font-medium text-slate-700">Password</label>
                {!isRegister && <button type="button" onClick={() => setNotice('Password reset is not connected yet.')} className="text-[10px] font-medium text-violet-700 hover:text-violet-900">Forgot password?</button>}
              </div>
              <div className="relative">
                <input id="password" name="password" type={showPassword ? 'text' : 'password'} autoComplete={isRegister ? 'new-password' : 'current-password'} required minLength={isRegister ? 12 : 1} placeholder={isRegister ? 'At least 12 characters' : 'Enter your password'} className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 pr-11 text-xs text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10" />
                <button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-0 grid w-10 place-items-center text-slate-400 hover:text-slate-700">
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            {isRegister && (
              <label className="flex items-start gap-2 pt-1 text-[10px] leading-4 text-slate-500">
                <input required type="checkbox" className="mt-0.5 accent-violet-600" />
                I agree to the Terms of Service and Privacy Policy.
              </label>
            )}
            <button type="submit" disabled={isSubmitting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3.5 text-xs font-semibold text-white shadow-lg shadow-violet-700/15 transition hover:brightness-110 disabled:cursor-wait disabled:opacity-70">
              {isSubmitting ? 'Please wait…' : isRegister ? `Create ${role} account` : 'Sign in'} <ArrowRight size={14} />
            </button>
          </form>

          {notice && (
            <div role="status" className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3 text-[10px] leading-5 text-amber-900">
              {notice}
            </div>
          )}

          <div className="my-5 flex items-center gap-3">
            <span className="h-px flex-1 bg-slate-200" />
            <span className="text-[9px] text-slate-400">OR CONTINUE WITH</span>
            <span className="h-px flex-1 bg-slate-200" />
          </div>
          <button type="button" onClick={() => setNotice('Social sign-in is not connected yet.')} className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-3 text-[11px] font-medium text-slate-700 transition hover:bg-slate-50">
            <GoogleMark /> Continue with Google
          </button>

          <p className="mt-6 text-center text-[11px] text-slate-500">
            {isRegister ? 'Already have an account?' : 'New to CareerLens?'}{' '}
            <Link to={isRegister ? '/login' : '/register'} className="font-semibold text-violet-700 hover:text-violet-900">
              {isRegister ? 'Log in' : 'Create an account'}
            </Link>
          </p>
          <p className="mt-7 text-center text-[9px] leading-4 text-slate-400">
            Authentication is securely sent to the CareerLens API.
          </p>
        </div>
        <p className="pb-2 text-center text-[9px] text-slate-400">© 2026 CareerLens AI</p>
      </section>
    </div>
  )
}

interface AuthResponse {
  access_token: string
  user: { role: string }
}

function RoleCard({
  selected,
  icon,
  title,
  description,
  onClick,
}: {
  selected: boolean
  icon: React.ReactNode
  title: string
  description: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`relative rounded-xl border p-3 text-left transition ${
        selected
          ? 'border-violet-400 bg-violet-50/60 ring-2 ring-violet-500/10'
          : 'border-slate-200 bg-white hover:border-slate-300'
      }`}
    >
      {selected && <span className="absolute right-2.5 top-2.5 text-violet-600"><Check size={13} /></span>}
      <span className={`mb-2 grid size-8 place-items-center rounded-lg ${selected ? 'bg-violet-100 text-violet-700' : 'bg-slate-100 text-slate-500'}`}>{icon}</span>
      <span className="block text-[11px] font-semibold text-slate-800">{title}</span>
      <span className="mt-1 block text-[9px] text-slate-500">{description}</span>
    </button>
  )
}

function GoogleMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" className="size-4">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z" transform="translate(0 5)" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.74 7.18l7.73 6C44.43 38.01 46.98 31.9 46.98 24.55Z" transform="translate(0 0)" />
      <path fill="#FBBC05" d="M10.53 28.59a14.4 14.4 0 0 1 0-9.18l-7.98-6.19a23.9 23.9 0 0 0 0 21.56l7.98-6.19Z" transform="translate(0 0)" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.91-5.8l-7.73-6c-2.14 1.44-4.88 2.3-8.18 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z" transform="translate(0 -5)" />
    </svg>
  )
}
