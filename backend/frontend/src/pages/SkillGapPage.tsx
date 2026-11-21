import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowUpRight,
  BookOpen,
  BriefcaseBusiness,
  Check,
  CircleAlert,
  CircleCheck,
  Clock3,
  LoaderCircle,
  LockKeyhole,
  Sparkles,
  Target,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient, getApiErrorMessage } from '../api/client'

type ActivityStatus = 'PLANNED' | 'IN_PROGRESS' | 'COMPLETED'

interface Job {
  id: string
  title: string
  company_name: string | null
  location: string | null
}

interface JobList {
  items: Job[]
}

interface LearningResource {
  id: string
  title: string
  provider: string
  url: string
  description: string
  status: ActivityStatus | null
  activity_id: string | null
}

interface SkillEvidence {
  skill: string
  category: 'strong_match' | 'partial_match' | 'missing'
  explanation: string
  learning_progress: number
  resources: LearningResource[]
}

interface Analysis {
  job_id: string
  job_title: string
  resume_id: string
  strong_matches: SkillEvidence[]
  partial_matches: SkillEvidence[]
  missing_skills: SkillEvidence[]
  evidence_note: string
}

interface RelatedJob {
  job_id: string
  title: string
  company_name: string | null
  location: string | null
  matching_skills: string[]
  missing_skills: string[]
  explanation: string
}

interface RelatedJobs {
  items: RelatedJob[]
}

interface ActivityInput {
  skill: string
  resource_id: string
  status: ActivityStatus
}

export function SkillGapPage() {
  const isCandidate = sessionStorage.getItem('careerlens_role') === 'CANDIDATE'
  const [selectedJobId, setSelectedJobId] = useState('')
  const queryClient = useQueryClient()
  const jobsQuery = useQuery({
    queryKey: ['skill-gap-jobs'],
    queryFn: async () => (await apiClient.get<JobList>('/jobs?limit=100')).data,
    enabled: isCandidate,
  })
  const analysisQuery = useQuery({
    queryKey: ['skill-gap-analysis', selectedJobId],
    queryFn: async () =>
      (await apiClient.get<Analysis>(`/skill-gaps/analysis?job_id=${selectedJobId}`)).data,
    enabled: isCandidate && Boolean(selectedJobId),
  })
  const relatedQuery = useQuery({
    queryKey: ['skill-gap-related-jobs'],
    queryFn: async () => (await apiClient.get<RelatedJobs>('/skill-gaps/related-jobs')).data,
    enabled: isCandidate,
  })
  const activityMutation = useMutation({
    mutationFn: async (input: ActivityInput) => {
      if (input.status === 'PLANNED') {
        return apiClient.post('/skill-gaps/activities', input)
      }
      const current = analysisQuery.data
      const entry = [
        ...(current?.partial_matches ?? []),
        ...(current?.missing_skills ?? []),
      ].find((item) => item.skill === input.skill)
      const resource = entry?.resources.find((item) => item.id === input.resource_id)
      if (resource?.activity_id) {
        return apiClient.patch(`/skill-gaps/activities/${resource.activity_id}`, {
          status: input.status,
        })
      }
      return apiClient.post('/skill-gaps/activities', input)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['skill-gap-analysis'] })
    },
  })

  if (!sessionStorage.getItem('careerlens_access_token') || !isCandidate) {
    return (
      <div className="mx-auto max-w-2xl rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-violet-50 text-violet-700">
          <LockKeyhole size={23} />
        </span>
        <h1 className="mt-5 text-2xl font-semibold tracking-tight text-slate-950">
          Sign in to see your skill roadmap
        </h1>
        <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-500">
          Skill comparisons use your analyzed resume and active job requirements. Your
          learning activity is private to your candidate account.
        </p>
        <Link
          to="/login"
          className="mt-6 inline-flex rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white hover:bg-violet-800"
        >
          Sign in to continue
        </Link>
      </div>
    )
  }

  const jobs = jobsQuery.data?.items ?? []
  const analysis = analysisQuery.data
  const totalSkills = analysis
    ? analysis.strong_matches.length +
      analysis.partial_matches.length +
      analysis.missing_skills.length
    : 0

  return (
    <div className="space-y-7">
      <section className="relative overflow-hidden rounded-3xl bg-[#14132d] px-6 py-7 text-white shadow-[0_18px_50px_rgba(27,22,63,0.15)] sm:px-9 sm:py-9">
        <div className="pointer-events-none absolute -right-20 -top-32 size-80 rounded-full bg-violet-500/25 blur-[90px]" />
        <div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div className="max-w-xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-violet-300/20 bg-violet-300/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-violet-200">
              <Sparkles size={13} /> Skill development
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
              Build a roadmap for your next role
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Compare the skills found in your resume with an active job listing, then
              track learning using curated resources.
            </p>
          </div>
          <div className="w-full md:max-w-[330px]">
            <label htmlFor="target-role" className="mb-2 block text-xs font-medium text-slate-300">
              Choose a target role
            </label>
            <select
              id="target-role"
              value={selectedJobId}
              onChange={(event) => setSelectedJobId(event.target.value)}
              className="w-full rounded-xl border border-white/15 bg-white/10 px-3.5 py-3 text-sm text-white outline-none focus:border-violet-300"
            >
              <option className="text-slate-900" value="">Select an active job…</option>
              {jobs.map((job) => (
                <option className="text-slate-900" key={job.id} value={job.id}>
                  {job.title}{job.company_name ? ` · ${job.company_name}` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {jobsQuery.isLoading && <LoadingState message="Loading active job listings…" />}
      {jobsQuery.isError && <ErrorState message={getApiErrorMessage(jobsQuery.error)} />}
      {!jobsQuery.isLoading && !jobsQuery.isError && jobs.length === 0 && (
        <EmptyState
          title="No active job listings yet"
          detail="Published jobs appear here as target roles. The app does not generate fictional openings."
        />
      )}
      {jobs.length > 0 && !selectedJobId && (
        <EmptyState
          title="Choose a role to begin"
          detail="Your comparison will include only explicitly required skills from the selected active listing."
        />
      )}
      {analysisQuery.isLoading && <LoadingState message="Comparing resume evidence with role requirements…" />}
      {analysisQuery.isError && <ErrorState message={getApiErrorMessage(analysisQuery.error)} />}

      {analysis && (
        <>
          <section className="grid gap-4 sm:grid-cols-3">
            <SummaryCard
              icon={<CircleCheck size={17} />}
              label="Explicit resume matches"
              value={analysis.strong_matches.length}
              tone="emerald"
            />
            <SummaryCard
              icon={<Clock3 size={17} />}
              label="Experience evidence"
              value={analysis.partial_matches.length}
              tone="amber"
            />
            <SummaryCard
              icon={<Target size={17} />}
              label="Skills to develop"
              value={analysis.missing_skills.length}
              tone="violet"
            />
          </section>

          <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-5">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-600">
                      Role requirements
                    </p>
                    <h2 className="mt-1 text-lg font-semibold text-slate-950">{analysis.job_title}</h2>
                    <p className="mt-1 text-xs text-slate-500">
                      {totalSkills} taxonomy-matched required skills
                    </p>
                  </div>
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-violet-50 text-violet-700">
                    <BriefcaseBusiness size={18} />
                  </span>
                </div>
                <div className="mt-6 space-y-3">
                  <SkillGroup
                    title="Strong matches"
                    subtitle="Explicitly listed in extracted resume skills"
                    items={analysis.strong_matches}
                    variant="strong"
                  />
                  <SkillGroup
                    title="Partial matches"
                    subtitle="Found in work-experience text only"
                    items={analysis.partial_matches}
                    variant="partial"
                    onTrack={trackResource}
                    pending={activityMutation.isPending}
                  />
                  <SkillGroup
                    title="Missing skills"
                    subtitle="No match in extracted skills or work evidence"
                    items={analysis.missing_skills}
                    variant="missing"
                    onTrack={trackResource}
                    pending={activityMutation.isPending}
                  />
                </div>
              </div>
              <p className="rounded-xl border border-slate-200 bg-white/70 px-4 py-3 text-[11px] leading-5 text-slate-500">
                {analysis.evidence_note}
              </p>
            </div>

            <div className="space-y-5">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="flex items-center gap-3">
                  <span className="grid size-9 place-items-center rounded-xl bg-indigo-50 text-indigo-700">
                    <BookOpen size={17} />
                  </span>
                  <div>
                    <h2 className="text-sm font-semibold text-slate-950">Learning roadmap</h2>
                    <p className="mt-0.5 text-[11px] text-slate-500">Curated provider resources · self-reported progress</p>
                  </div>
                </div>
                <div className="mt-5 space-y-4">
                  {[...analysis.missing_skills, ...analysis.partial_matches].map((skill) => (
                    <div key={skill.skill} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold text-slate-800">{skill.skill}</p>
                        <span className="text-[10px] font-medium text-slate-500">{skill.learning_progress}%</span>
                      </div>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all"
                          style={{ width: `${skill.learning_progress}%` }}
                        />
                      </div>
                      {skill.resources.length === 0 && (
                        <p className="mt-2 text-[10px] leading-4 text-slate-500">
                          No curated resource is currently cataloged for this skill.
                        </p>
                      )}
                    </div>
                  ))}
                  {analysis.missing_skills.length + analysis.partial_matches.length === 0 && (
                    <p className="rounded-xl bg-emerald-50 p-4 text-xs leading-5 text-emerald-800">
                      No skill gaps were identified among this listing’s recognized required skills.
                    </p>
                  )}
                </div>
                {activityMutation.isError && (
                  <p role="alert" className="mt-4 text-xs text-rose-700">
                    {getApiErrorMessage(activityMutation.error)}
                  </p>
                )}
              </section>
            </div>
          </section>
        </>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-950">Related active roles</h2>
            <p className="mt-1 text-[11px] text-slate-500">Ranked by explicit skill overlap with your analyzed resume.</p>
          </div>
          <span className="grid size-9 place-items-center rounded-xl bg-violet-50 text-violet-700">
            <BriefcaseBusiness size={17} />
          </span>
        </div>
        {relatedQuery.isLoading && <LoadingState message="Finding related active listings…" />}
        {relatedQuery.isError && <ErrorState message={getApiErrorMessage(relatedQuery.error)} />}
        {relatedQuery.data?.items.length === 0 && (
          <p className="mt-4 rounded-xl bg-slate-50 p-4 text-xs text-slate-500">
            No active jobs with overlapping required skills were found.
          </p>
        )}
        {relatedQuery.data?.items && relatedQuery.data.items.length > 0 && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {relatedQuery.data.items.map((job) => (
              <article key={job.job_id} className="rounded-xl border border-slate-100 p-4">
                <h3 className="text-xs font-semibold text-slate-900">{job.title}</h3>
                <p className="mt-1 text-[10px] text-slate-500">
                  {[job.company_name, job.location].filter(Boolean).join(' · ') || 'Active listing'}
                </p>
                <p className="mt-2 text-[10px] leading-4 text-slate-600">{job.explanation}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {job.matching_skills.map((skill) => (
                    <span key={skill} className="rounded-full bg-emerald-50 px-2 py-1 text-[9px] font-medium text-emerald-800">{skill}</span>
                  ))}
                  {job.missing_skills.map((skill) => (
                    <span key={skill} className="rounded-full bg-amber-50 px-2 py-1 text-[9px] font-medium text-amber-800">{skill}</span>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedJobId(job.job_id)}
                  className="mt-3 inline-flex items-center gap-1 text-[10px] font-semibold text-violet-700 hover:text-violet-900"
                >
                  Build roadmap <ArrowUpRight size={12} />
                </button>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )

  function trackResource(skill: string, resource: LearningResource) {
    const nextStatus: ActivityStatus = resource.status === 'IN_PROGRESS'
      ? 'COMPLETED'
      : 'IN_PROGRESS'
    activityMutation.mutate({
      skill,
      resource_id: resource.id,
      status: nextStatus,
    })
  }
}

function SummaryCard({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode
  label: string
  value: number
  tone: 'emerald' | 'amber' | 'violet'
}) {
  const tones = {
    emerald: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    violet: 'bg-violet-50 text-violet-700',
  }
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className={`grid size-9 place-items-center rounded-xl ${tones[tone]}`}>{icon}</span>
        <span className="text-2xl font-semibold tracking-tight text-slate-950">{value}</span>
      </div>
      <p className="mt-3 text-xs font-medium text-slate-600">{label}</p>
    </div>
  )
}

function SkillGroup({
  title,
  subtitle,
  items,
  variant,
  onTrack,
  pending,
}: {
  title: string
  subtitle: string
  items: SkillEvidence[]
  variant: 'strong' | 'partial' | 'missing'
  onTrack?: (skill: string, resource: LearningResource) => void
  pending?: boolean
}) {
  const styles = {
    strong: 'bg-emerald-50 text-emerald-800',
    partial: 'bg-amber-50 text-amber-800',
    missing: 'bg-rose-50 text-rose-800',
  }
  const Icon = variant === 'strong' ? Check : variant === 'partial' ? Clock3 : CircleAlert
  return (
    <section className="rounded-xl border border-slate-100 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs font-semibold text-slate-800">{title}</h3>
          <p className="mt-1 text-[10px] text-slate-500">{subtitle}</p>
        </div>
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[9px] font-semibold ${styles[variant]}`}>
          <Icon size={11} /> {items.length}
        </span>
      </div>
      {items.length === 0 ? (
        <p className="mt-3 text-[11px] text-slate-400">None identified.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.map((item) => (
            <li key={item.skill} className="rounded-lg bg-slate-50/80 px-3 py-2.5">
              <p className="text-[11px] font-medium text-slate-800">{item.skill}</p>
              <p className="mt-1 text-[10px] leading-4 text-slate-500">{item.explanation}</p>
              {variant !== 'strong' && item.resources.map((resource) => (
                <div key={resource.id} className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/70 pt-2.5">
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] font-medium text-violet-700 hover:text-violet-900"
                  >
                    {resource.title} <ArrowUpRight size={11} />
                  </a>
                  {onTrack && (
                    <button
                      type="button"
                      disabled={pending || resource.status === 'COMPLETED'}
                      onClick={() => onTrack(item.skill, resource)}
                      className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[9px] font-semibold text-slate-600 hover:border-violet-300 hover:text-violet-700 disabled:cursor-default disabled:opacity-60"
                    >
                      {resource.status === 'COMPLETED'
                        ? 'Completed'
                        : resource.status === 'IN_PROGRESS'
                          ? 'Mark complete'
                          : 'Start learning'}
                    </button>
                  )}
                </div>
              ))}
              {variant !== 'strong' && item.resources.length === 0 && (
                <p className="mt-2 text-[10px] text-slate-400">No curated resource currently available.</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function LoadingState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-500">
      <LoaderCircle size={16} className="animate-spin text-violet-600" /> {message}
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800">{message}</p>
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-7 text-center">
      <BookOpen size={20} className="mx-auto text-slate-400" />
      <h2 className="mt-3 text-sm font-semibold text-slate-800">{title}</h2>
      <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-slate-500">{detail}</p>
    </div>
  )
}
