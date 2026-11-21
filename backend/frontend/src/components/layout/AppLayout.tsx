import { useState } from 'react'
import {
  Activity,
  BarChart3,
  BriefcaseBusiness,
  FileText,
  LayoutDashboard,
  Menu,
  Settings,
  Sparkles,
  X,
} from 'lucide-react'
import { Navigate, NavLink, Outlet, useNavigate } from 'react-router-dom'

const candidateNavigation = [
  { label: 'Overview', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Resume analyzer', to: '/resume-analyzer', icon: FileText },
  { label: 'Job matches', to: '/job-matching', icon: BriefcaseBusiness },
  { label: 'Skill gaps', to: '/skill-gaps', icon: BarChart3 },
  { label: 'Interview prep', to: '/interview-prep', icon: Sparkles },
  { label: 'Profile & settings', to: '/profile-settings', icon: Settings },
]

const recruiterNavigation = [
  { label: 'Overview', to: '/dashboard', icon: LayoutDashboard },
]

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const recruiter = sessionStorage.getItem('careerlens_role') === 'RECRUITER'
  const navigation = recruiter ? recruiterNavigation : candidateNavigation
  const workspaceLabel = recruiter ? 'Recruiter workspace' : 'Candidate workspace'

  if (!sessionStorage.getItem('careerlens_access_token')) return <Navigate to="/login" replace />

  return (
    <div className="min-h-screen bg-[#f7f7fb] text-slate-900">
      {menuOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-950/50 lg:hidden"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[260px] flex-col bg-[#101126] text-white transition-transform duration-200 lg:translate-x-0 ${
          menuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-[76px] items-center justify-between border-b border-white/10 px-6">
          <NavLink to="/" className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-500 shadow-lg shadow-violet-950/50">
              <Sparkles size={18} />
            </span>
            <span className="text-[17px] font-semibold tracking-tight">
              CareerLens<span className="text-violet-300">.</span>
            </span>
          </NavLink>
          <button
            aria-label="Close navigation"
            className="rounded-lg p-2 text-slate-400 hover:bg-white/10 lg:hidden"
            onClick={() => setMenuOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-4 pt-7">
          <p className="px-3 pb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Workspace
          </p>
          <nav aria-label={`${workspaceLabel} navigation`} className="space-y-1">
            {navigation.map(({ label, to, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] transition ${
                    isActive
                      ? 'bg-violet-500/15 font-medium text-violet-200 ring-1 ring-violet-400/20'
                      : 'text-slate-400 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                <Icon size={17} strokeWidth={1.8} />
                <span className="flex-1">{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="mt-auto p-4">
          <div className="rounded-2xl border border-violet-300/10 bg-gradient-to-br from-violet-500/15 to-indigo-500/5 p-4">
            <div className="mb-2 flex items-center gap-2 text-violet-200">
              <Activity size={15} />
              <span className="text-xs font-semibold">Your next step</span>
            </div>
            <p className="text-[11px] leading-5 text-slate-400">
              {recruiter ? 'Create and manage roles published by your account.' : 'Upload your resume to explore evidence-based career tools.'}
            </p>
          </div>
          <div className="mt-4 flex items-center gap-3 border-t border-white/10 px-2 pt-4">
            <div className="grid size-9 place-items-center rounded-full bg-gradient-to-br from-fuchsia-400 to-violet-500 text-xs font-bold">
              {recruiter ? 'R' : 'C'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-white">{workspaceLabel}</p>
              <p className="text-[10px] text-slate-500">Signed in</p>
            </div>
            <button aria-label="Sign out" onClick={() => { sessionStorage.clear(); navigate('/login') }} className="text-[10px] text-slate-400 hover:text-white">Sign out</button>
          </div>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-[260px]">
        <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-slate-200/80 bg-white/90 px-5 backdrop-blur-md sm:px-8">
          <div className="flex items-center gap-3">
            <button
              aria-label="Open navigation"
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
              onClick={() => setMenuOpen(true)}
            >
              <Menu size={19} />
            </button>
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-400">
                {workspaceLabel}
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-800">
                Your CareerLens workspace
              </p>
            </div>
          </div>
          <button onClick={() => { sessionStorage.clear(); navigate('/login') }} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm hover:border-slate-300">
            Sign out
          </button>
        </header>
        <main className="mx-auto max-w-[1400px] px-5 py-7 sm:px-8 sm:py-9">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
