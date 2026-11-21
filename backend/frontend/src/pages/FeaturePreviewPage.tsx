import { ArrowLeft, ArrowRight, Sparkles } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

const pageTitles: Record<string, string> = {
  '/resume-analyzer': 'Resume analyzer',
  '/job-matching': 'Job matching',
  '/skill-gaps': 'Skill gap analysis',
  '/interview-prep': 'Interview preparation',
  '/profile-settings': 'Profile & settings',
}

export function FeaturePreviewPage() {
  const { pathname } = useLocation()
  const title = pageTitles[pathname] ?? 'Career workspace'

  return (
    <section className="mx-auto max-w-2xl rounded-3xl border border-slate-200/80 bg-white px-6 py-12 text-center shadow-[0_3px_14px_rgba(27,30,65,0.035)] sm:px-12 sm:py-16">
      <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-violet-100 text-violet-700">
        <Sparkles size={21} />
      </span>
      <p className="mt-5 text-[10px] font-semibold uppercase tracking-[0.17em] text-violet-600">
        Coming in a future stage
      </p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {title}
      </h1>
      <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-500">
        This part of CareerLens is being built. No analysis, recommendations, or
        matching results are generated here yet.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-3">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft size={14} /> Dashboard
        </Link>
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-violet-700"
        >
          Home <ArrowRight size={14} />
        </Link>
      </div>
    </section>
  )
}
