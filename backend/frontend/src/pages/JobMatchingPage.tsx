import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowUpRight, BriefcaseBusiness, LoaderCircle, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { candidateApi } from '../api/candidate'
import { getApiErrorMessage } from '../api/client'

export function JobMatchingPage() {
  const [resumeId, setResumeId] = useState('')
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: candidateApi.jobs })
  const resumes = useQuery({ queryKey: ['resumes'], queryFn: candidateApi.resumes })
  const analyze = useMutation({ mutationFn: candidateApi.recommendations })
  const jobsById = useMemo(() => new Map(jobs.data?.items.map((job) => [job.id, job]) ?? []), [jobs.data])
  const readyResumes = resumes.data?.filter((resume) => resume.extraction_status === 'completed') ?? []

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-violet-700">Opportunity discovery</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-950">Job matching</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Run the configured matching model against active jobs. Scores include component explanations and are not probabilities of being hired.</p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <label htmlFor="match-resume" className="block text-sm font-medium text-slate-800">Use a processed resume</label>
        {resumes.isPending ? (
          <p role="status" className="mt-2 text-sm text-slate-500">Loading resumes…</p>
        ) : readyResumes.length ? (
          <div className="mt-2 flex flex-col gap-3 sm:flex-row">
            <select id="match-resume" value={resumeId || readyResumes[0].id} onChange={(event) => setResumeId(event.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm">
              {readyResumes.map((resume) => <option key={resume.id} value={resume.id}>{new Date(resume.created_at).toLocaleString()}</option>)}
            </select>
            <button onClick={() => analyze.mutate(resumeId || readyResumes[0].id)} disabled={analyze.isPending || jobs.isPending} className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
              {analyze.isPending ? <LoaderCircle size={16} className="animate-spin" /> : <Search size={16} />}
              Analyze active jobs
            </button>
          </div>
        ) : (
          <div className="mt-3 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
            A successfully processed resume is required. <a className="font-semibold text-violet-700 underline" href="/resume-analyzer">Upload or review a resume</a>.
          </div>
        )}
        {analyze.isError && <p role="alert" className="mt-3 text-sm text-rose-700">{getApiErrorMessage(analyze.error)}</p>}
        {jobs.isError && <p role="alert" className="mt-3 text-sm text-rose-700">{getApiErrorMessage(jobs.error)}</p>}
      </section>

      {jobs.isPending ? <p role="status" className="text-sm text-slate-500">Loading active jobs…</p> : null}
      {jobs.data?.total === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <BriefcaseBusiness className="mx-auto text-slate-400" />
          <p className="mt-3 text-sm font-medium text-slate-800">No active jobs are available</p>
        </div>
      )}
      {analyze.data && (
        <section aria-label="Job match results" className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-900">Analysis results</h2>
          {analyze.data.length ? analyze.data.map((result) => {
            const job = jobsById.get(result.job_id)
            if (!job) return null
            return (
              <article key={result.id} className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">{job.title}</h3>
                    <p className="mt-1 text-sm text-slate-500">{job.company_name ?? 'Company not listed'}{job.location ? ` · ${job.location}` : ''}</p>
                  </div>
                  <div className="rounded-xl bg-violet-50 px-4 py-2 text-right">
                    <p className="text-2xl font-semibold text-violet-800">{Math.round(result.total_score)}<span className="text-sm">/100</span></p>
                    <p className="text-[10px] font-medium uppercase tracking-wide text-violet-600">Compatibility policy score</p>
                  </div>
                </div>
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <SkillList title="Matching required skills" skills={result.score_details.matching_skills} tone="green" />
                  <SkillList title="Missing required skills" skills={result.score_details.missing_required_skills} tone="amber" />
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  {Object.entries(result.score_details.components).map(([name, component]) => (
                    <div key={name} className="rounded-xl bg-slate-50 p-3">
                      <p className="text-xs font-semibold capitalize text-slate-800">{name.replaceAll('_', ' ')}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-600">{component.explanation}</p>
                    </div>
                  ))}
                </div>
                {result.score_details.explanations.length > 0 && (
                  <ul className="mt-4 space-y-1 text-xs leading-5 text-slate-600">{result.score_details.explanations.map((item) => <li key={item} className="flex gap-2"><ArrowUpRight size={14} className="mt-0.5 shrink-0 text-violet-600" />{item}</li>)}</ul>
                )}
              </article>
            )
          }) : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">No active jobs to compare against yet.</p>}
        </section>
      )}
      {jobs.data?.items?.length && !analyze.data && !analyze.isPending ? (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">Active jobs ({jobs.data.total})</h2>
          {jobs.data.items.map((job) => (
            <article key={job.id} className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="font-semibold text-slate-900">{job.title}</h3>
              <p className="mt-1 text-sm text-slate-500">{job.company_name ?? 'Company not listed'}{job.location ? ` · ${job.location}` : ''}</p>
              <div className="mt-3 flex flex-wrap gap-2">{job.required_skills.map((skill) => <span key={skill} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">{skill}</span>)}</div>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  )
}

function SkillList({ title, skills, tone }: { title: string; skills: string[]; tone: 'green' | 'amber' }) {
  const style = tone === 'green' ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'
  return (
    <div>
      <h4 className="text-xs font-semibold text-slate-700">{title}</h4>
      {skills.length ? <div className="mt-2 flex flex-wrap gap-2">{skills.map((skill) => <span key={skill} className={`rounded-full px-2.5 py-1 text-xs ${style}`}>{skill}</span>)}</div> : <p className="mt-2 text-xs text-slate-400">None reported.</p>}
    </div>
  )
}
