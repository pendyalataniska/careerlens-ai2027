import { useCandidateDashboard } from '../hooks/useCandidateDashboard'
import { Link } from 'react-router-dom'
import { ArrowRight, BriefcaseBusiness, FileText, Sparkles } from 'lucide-react'

export function DashboardPage() {
  const dashboard = useCandidateDashboard()

  if (dashboard.isPending) {
    return <p className="text-sm text-slate-500" role="status">Loading your workspace…</p>
  }
  if (dashboard.isError) {
    return (
      <section role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6">
        <h1 className="font-semibold text-rose-900">Dashboard could not load</h1>
        <p className="mt-1 text-sm text-rose-700">{dashboard.error.message}</p>
        <button className="mt-4 rounded-lg bg-rose-700 px-4 py-2 text-sm text-white" onClick={() => void dashboard.refetch()}>
          Try again
        </button>
      </section>
    )
  }

  const data = dashboard.data
  const fullName = `${data.profile.first_name} ${data.profile.last_name}`.trim()

  return (
    <div className="space-y-6">
      <header>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-violet-700">
          <Sparkles size={12} /> Candidate workspace
        </span>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950 sm:text-[30px]">
          Welcome, {fullName || 'back'}.
        </h1>
        <p className="mt-1.5 text-sm text-slate-500">A current view of your saved CareerLens activity.</p>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <article className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-xs text-slate-500">Resume status</p>
          <p className="mt-3 text-xl font-semibold capitalize text-slate-900">
            {data.resume_status?.replaceAll('_', ' ') ?? 'Not uploaded'}
          </p>
          <Link className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-violet-700" to="/resume-analyzer">
            Manage resumes <ArrowRight size={13} />
          </Link>
        </article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-xs text-slate-500">Skills extracted from latest resume</p>
          <p className="mt-3 text-3xl font-semibold text-slate-900">{data.skills.length}</p>
          <p className="mt-1 text-xs text-slate-400">Source-labelled extraction; not verified qualifications.</p>
        </article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-xs text-slate-500">Interview practice</p>
          <p className="mt-3 text-xl font-semibold text-slate-900">
            {data.completed_interviews} <span className="text-sm font-normal text-slate-500">of {data.interview_sessions} completed</span>
          </p>
          <Link className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-violet-700" to="/interview-prep">
            Continue practice <ArrowRight size={13} />
          </Link>
        </article>
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Analyzed job matches</h2>
              <p className="mt-1 text-xs text-slate-500">Only actual saved compatibility analyses are shown.</p>
            </div>
            <BriefcaseBusiness size={18} className="text-violet-600" />
          </div>
          {data.matches.length ? (
            <div className="mt-4 divide-y divide-slate-100">
              {data.matches.map((match) => (
                <article key={match.id} className="flex items-center gap-4 py-4">
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-medium text-slate-800">{match.title}</h3>
                    <p className="mt-1 text-xs text-slate-500">
                      {match.company_name ?? 'Company not listed'}{match.location ? ` · ${match.location}` : ''}
                    </p>
                  </div>
                  <p className="shrink-0 text-sm font-semibold text-violet-700">{Math.round(match.total_score)} / 100</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="mt-5 rounded-xl bg-slate-50 p-5 text-sm text-slate-600">
              No analysis has been run yet. Upload a resume and analyze active roles to see transparent, evidence-based matches.
            </div>
          )}
          <p className="mt-4 text-[11px] leading-5 text-slate-500">{data.disclaimer}</p>
          <Link to="/job-matching" className="mt-4 inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-violet-700">
            Explore job matches <ArrowRight size={14} />
          </Link>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <div className="flex items-center gap-2">
            <FileText size={17} className="text-violet-600" />
            <h2 className="text-sm font-semibold text-slate-900">Latest extracted skills</h2>
          </div>
          {data.skills.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {data.skills.map((skill) => (
                <span key={skill} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-700">{skill}</span>
              ))}
            </div>
          ) : (
            <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
              Skills will appear here after resume processing completes.
            </p>
          )}
          <Link to="/resume-analyzer" className="mt-5 inline-flex items-center gap-2 text-xs font-semibold text-violet-700">
            Review resume analysis <ArrowRight size={14} />
          </Link>
        </section>
      </div>
    </div>
  )
}
