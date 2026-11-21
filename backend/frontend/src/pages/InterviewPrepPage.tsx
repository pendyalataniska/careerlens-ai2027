import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  BarChart3,
  Brain,
  CheckCircle2,
  CircleAlert,
  Clock3,
  LoaderCircle,
  LockKeyhole,
  MessageSquareText,
  RotateCcw,
  Sparkles,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient, getApiErrorMessage } from '../api/client'

interface InterviewRole {
  id: string
  title: string
  company_name: string | null
  location: string | null
  required_skills: string[]
}

interface Evaluation {
  relevance: CriterionEvaluation
  technical_correctness: CriterionEvaluation
  clarity: CriterionEvaluation
  completeness: CriterionEvaluation
  overall_feedback: string
  strengths: string[]
  areas_to_improve: string[]
}

interface CriterionEvaluation {
  score: number
  feedback: string
}

interface InterviewQuestion {
  id: string
  position: number
  category: 'TECHNICAL' | 'HR'
  prompt: string
  targeted_skills: string[]
  answer: string | null
  evaluation: Evaluation | null
  answered_at: string | null
}

interface InterviewSession {
  id: string
  job_id: string | null
  role_title: string
  status: 'DRAFT' | 'IN_PROGRESS' | 'COMPLETED'
  created_at: string
  completed_at: string | null
  questions: InterviewQuestion[]
  answered_questions: number
  total_questions: number
  average_score: number | null
  score_disclaimer: string
}

interface SessionList {
  items: InterviewSession[]
}

interface Analytics {
  total_sessions: number
  completed_sessions: number
  total_questions: number
  answered_questions: number
  average_score: number | null
  criterion_averages: Record<string, number | null>
  disclaimer: string
}

const criterionLabels = [
  ['relevance', 'Relevance'],
  ['technical_correctness', 'Technical correctness'],
  ['clarity', 'Clarity'],
  ['completeness', 'Completeness'],
] as const

export function InterviewPrepPage() {
  const isCandidate =
    sessionStorage.getItem('careerlens_role') === 'CANDIDATE' &&
    Boolean(sessionStorage.getItem('careerlens_access_token'))
  const queryClient = useQueryClient()
  const [selectedJobId, setSelectedJobId] = useState('')
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [technicalCount, setTechnicalCount] = useState(4)
  const [hrCount, setHrCount] = useState(2)
  const [answers, setAnswers] = useState<Record<string, string>>({})

  const rolesQuery = useQuery({
    queryKey: ['interview-roles'],
    queryFn: async () => (await apiClient.get<InterviewRole[]>('/interviews/roles')).data,
    enabled: isCandidate,
  })
  const sessionsQuery = useQuery({
    queryKey: ['interview-sessions'],
    queryFn: async () => (await apiClient.get<SessionList>('/interviews/sessions')).data,
    enabled: isCandidate,
  })
  const analyticsQuery = useQuery({
    queryKey: ['interview-analytics'],
    queryFn: async () => (await apiClient.get<Analytics>('/interviews/analytics')).data,
    enabled: isCandidate,
  })
  const activeSessionQuery = useQuery({
    queryKey: ['interview-session', selectedSessionId],
    queryFn: async () =>
      (await apiClient.get<InterviewSession>(`/interviews/sessions/${selectedSessionId}`)).data,
    enabled: isCandidate && Boolean(selectedSessionId),
  })

  const createSessionMutation = useMutation({
    mutationFn: async () =>
      (
        await apiClient.post<InterviewSession>(
          '/interviews/sessions',
          {
            job_id: selectedJobId,
            technical_questions: technicalCount,
            hr_questions: hrCount,
          },
          { timeout: 45_000 },
        )
      ).data,
    onSuccess: async (session) => {
      setSelectedSessionId(session.id)
      setAnswers({})
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['interview-sessions'] }),
        queryClient.invalidateQueries({ queryKey: ['interview-analytics'] }),
      ])
    },
  })

  const answerMutation = useMutation({
    mutationFn: async ({
      sessionId,
      questionId,
      answer,
    }: {
      sessionId: string
      questionId: string
      answer: string
    }) =>
      (
        await apiClient.post<InterviewSession>(
          `/interviews/sessions/${sessionId}/questions/${questionId}/answer`,
          { answer },
          { timeout: 45_000 },
        )
      ).data,
    onSuccess: async (session) => {
      queryClient.setQueryData(['interview-session', session.id], session)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['interview-sessions'] }),
        queryClient.invalidateQueries({ queryKey: ['interview-analytics'] }),
      ])
    },
  })

  if (!isCandidate) {
    return (
      <div className="mx-auto max-w-2xl rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-violet-50 text-violet-700">
          <LockKeyhole size={23} />
        </span>
        <h1 className="mt-5 text-2xl font-semibold tracking-tight text-slate-950">
          Sign in to prepare for interviews
        </h1>
        <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-500">
          Choose an active role and use your analyzed resume to generate tailored practice questions.
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

  const activeSession = activeSessionQuery.data
  const analytics = analyticsQuery.data
  const roles = rolesQuery.data ?? []

  return (
    <div className="space-y-7">
      <section className="relative overflow-hidden rounded-3xl bg-[#14132d] px-6 py-7 text-white shadow-[0_18px_50px_rgba(27,22,63,0.15)] sm:px-9 sm:py-9">
        <div className="pointer-events-none absolute -right-20 -top-32 size-80 rounded-full bg-violet-500/25 blur-[90px]" />
        <div className="relative grid gap-7 lg:grid-cols-[1fr_0.85fr] lg:items-end">
          <div className="max-w-xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-violet-300/20 bg-violet-300/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-violet-200">
              <Sparkles size={13} /> Interview practice
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
              Practice with feedback grounded in your target role
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Gemini creates role-specific technical and HR prompts from skills extracted
              from your resume and the job’s stated requirements.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 sm:p-5">
            <label htmlFor="interview-role" className="mb-2 block text-xs font-medium text-slate-200">
              Select an active job role
            </label>
            <select
              id="interview-role"
              value={selectedJobId}
              onChange={(event) => setSelectedJobId(event.target.value)}
              className="w-full rounded-xl border border-white/15 bg-white/10 px-3.5 py-3 text-sm text-white outline-none focus:border-violet-300"
            >
              <option className="text-slate-900" value="">Choose a target role…</option>
              {roles.map((role) => (
                <option className="text-slate-900" key={role.id} value={role.id}>
                  {role.title}{role.company_name ? ` · ${role.company_name}` : ''}
                </option>
              ))}
            </select>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <CountInput label="Technical" value={technicalCount} onChange={setTechnicalCount} />
              <CountInput label="HR" value={hrCount} onChange={setHrCount} />
            </div>
            <button
              type="button"
              disabled={!selectedJobId || createSessionMutation.isPending || rolesQuery.isLoading}
              onClick={() => createSessionMutation.mutate()}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-indigo-500 px-4 py-3 text-xs font-semibold text-white shadow-lg shadow-violet-950/20 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createSessionMutation.isPending
                ? <><LoaderCircle size={15} className="animate-spin" /> Generating with Gemini…</>
                : <>Generate practice set <ArrowRight size={14} /></>}
            </button>
            <p className="mt-2 text-center text-[9px] leading-4 text-slate-400">
              Resume skill names and job role/requirements are sent to Gemini. Raw resumes and contact details are not sent.
            </p>
          </div>
        </div>
      </section>

      {rolesQuery.isLoading && <Notice message="Loading active job roles…" loading />}
      {rolesQuery.isError && <Notice message={getApiErrorMessage(rolesQuery.error)} error />}
      {roles.length === 0 && !rolesQuery.isLoading && !rolesQuery.isError && (
        <EmptyNotice message="No active job listings are available. Interview questions require a verified active job role." />
      )}
      {createSessionMutation.isError && (
        <Notice message={getApiErrorMessage(createSessionMutation.error)} error />
      )}

      {analytics && (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Practice sessions" value={analytics.total_sessions} icon={<MessageSquareText size={17} />} />
          <MetricCard label="Completed sessions" value={analytics.completed_sessions} icon={<CheckCircle2 size={17} />} />
          <MetricCard label="Answers reviewed" value={`${analytics.answered_questions}/${analytics.total_questions}`} icon={<Brain size={17} />} />
          <MetricCard
            label="Average rubric score"
            value={analytics.average_score === null ? '—' : `${analytics.average_score.toFixed(1)} / 5`}
            icon={<BarChart3 size={17} />}
          />
        </section>
      )}
      {analyticsQuery.isError && <Notice message={getApiErrorMessage(analyticsQuery.error)} error />}

      <section className="grid gap-5 xl:grid-cols-[0.72fr_1.28fr]">
        <div className="space-y-5">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-950">Rubric analytics</h2>
                <p className="mt-1 text-[10px] text-slate-500">Average AI feedback scores · 1 to 5</p>
              </div>
              <span className="grid size-9 place-items-center rounded-xl bg-indigo-50 text-indigo-700">
                <BarChart3 size={17} />
              </span>
            </div>
            <div className="mt-5 space-y-4">
              {criterionLabels.map(([key, label]) => {
                const score = analytics?.criterion_averages[key] ?? null
                return (
                  <div key={key}>
                    <div className="mb-1.5 flex justify-between text-[10px]">
                      <span className="font-medium text-slate-700">{label}</span>
                      <span className="text-slate-500">{score === null ? 'No data' : `${score.toFixed(1)} / 5`}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500"
                        style={{ width: `${score === null ? 0 : score / 5 * 100}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="mt-5 rounded-xl bg-amber-50 px-3 py-2.5 text-[10px] leading-4 text-amber-900">
              {analytics?.disclaimer ??
                'Scores are subjective AI practice feedback, not an objective employability or hiring measure.'}
            </p>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-950">Recent practice</h2>
                <p className="mt-1 text-[10px] text-slate-500">Your saved interview sessions</p>
              </div>
              <Clock3 size={17} className="text-slate-400" />
            </div>
            {sessionsQuery.isLoading && <Notice message="Loading sessions…" loading />}
            {sessionsQuery.isError && <Notice message={getApiErrorMessage(sessionsQuery.error)} error />}
            {sessionsQuery.data?.items.length === 0 && (
              <p className="mt-4 rounded-xl bg-slate-50 p-4 text-[11px] text-slate-500">
                No interview sessions yet. Choose a role above to generate your first practice set.
              </p>
            )}
            <div className="mt-4 space-y-2">
              {sessionsQuery.data?.items.map((session) => (
                <button
                  type="button"
                  key={session.id}
                  onClick={() => setSelectedSessionId(session.id)}
                  className={`w-full rounded-xl border p-3 text-left transition ${
                    selectedSessionId === session.id
                      ? 'border-violet-300 bg-violet-50/60'
                      : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-[11px] font-semibold text-slate-800">{session.role_title}</span>
                    <span className={`shrink-0 rounded-full px-2 py-1 text-[8px] font-semibold ${
                      session.status === 'COMPLETED'
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-amber-50 text-amber-700'
                    }`}>
                      {session.status === 'COMPLETED' ? 'Completed' : 'In progress'}
                    </span>
                  </span>
                  <span className="mt-1 block text-[9px] text-slate-500">
                    {session.answered_questions} of {session.total_questions} answers · {new Date(session.created_at).toLocaleDateString()}
                  </span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <section className="min-h-[400px] rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-violet-600">Practice session</p>
              <h2 className="mt-1 text-base font-semibold text-slate-950">
                {activeSession?.role_title ?? 'Your questions and feedback'}
              </h2>
            </div>
            {activeSession && (
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[9px] font-medium text-slate-600">
                {activeSession.answered_questions}/{activeSession.total_questions} answered
              </span>
            )}
          </div>
          {activeSessionQuery.isLoading && <Notice message="Loading session…" loading />}
          {activeSessionQuery.isError && <Notice message={getApiErrorMessage(activeSessionQuery.error)} error />}
          {!activeSession && !activeSessionQuery.isLoading && (
            <div className="grid min-h-[300px] place-items-center text-center">
              <div className="max-w-xs">
                <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-violet-50 text-violet-700">
                  <Sparkles size={20} />
                </span>
                <p className="mt-4 text-sm font-semibold text-slate-800">Ready when you are</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Generate a set or select a saved session to work through questions and review feedback.
                </p>
              </div>
            </div>
          )}
          {activeSession && (
            <>
              {answerMutation.isError && <Notice message={getApiErrorMessage(answerMutation.error)} error />}
              <div className="mt-5 space-y-5">
                {activeSession.questions.map((question) => (
                  <QuestionCard
                    key={question.id}
                    question={question}
                    answer={answers[question.id] ?? question.answer ?? ''}
                    pending={answerMutation.isPending}
                    onAnswerChange={(answer) =>
                      setAnswers((current) => ({ ...current, [question.id]: answer }))
                    }
                    onSubmit={(answer) =>
                      answerMutation.mutate({
                        sessionId: activeSession.id,
                        questionId: question.id,
                        answer,
                      })
                    }
                  />
                ))}
              </div>
              <p className="mt-5 text-[9px] leading-4 text-slate-400">
                {activeSession.score_disclaimer}
              </p>
            </>
          )}
        </section>
      </section>
    </div>
  )
}

function CountInput({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (value: number) => void
}) {
  return (
    <label className="text-[10px] text-slate-300">
      {label} questions
      <input
        type="number"
        min={1}
        max={10}
        value={value}
        onChange={(event) => onChange(Math.min(10, Math.max(1, Number(event.target.value))))}
        className="mt-1 w-full rounded-lg border border-white/15 bg-white/10 px-3 py-2 text-xs text-white outline-none focus:border-violet-300"
      />
    </label>
  )
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string
  value: number | string
  icon: React.ReactNode
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="grid size-9 place-items-center rounded-xl bg-violet-50 text-violet-700">{icon}</span>
        <span className="text-xl font-semibold tracking-tight text-slate-950">{value}</span>
      </div>
      <p className="mt-3 text-xs font-medium text-slate-600">{label}</p>
    </div>
  )
}

function QuestionCard({
  question,
  answer,
  pending,
  onAnswerChange,
  onSubmit,
}: {
  question: InterviewQuestion
  answer: string
  pending: boolean
  onAnswerChange: (answer: string) => void
  onSubmit: (answer: string) => void
}) {
  return (
    <article className="rounded-xl border border-slate-200 p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={`rounded-full px-2.5 py-1 text-[9px] font-semibold ${
          question.category === 'TECHNICAL'
            ? 'bg-indigo-50 text-indigo-700'
            : 'bg-fuchsia-50 text-fuchsia-700'
        }`}>
          {question.category === 'TECHNICAL' ? 'Technical' : 'HR'} · Question {question.position}
        </span>
        <span className="flex flex-wrap gap-1">
          {question.targeted_skills.map((skill) => (
            <span key={skill} className="rounded-full bg-slate-100 px-2 py-1 text-[8px] font-medium text-slate-600">{skill}</span>
          ))}
        </span>
      </div>
      <h3 className="mt-3 text-sm font-semibold leading-6 text-slate-900">{question.prompt}</h3>
      <label className="sr-only" htmlFor={`answer-${question.id}`}>Your answer</label>
      <textarea
        id={`answer-${question.id}`}
        rows={4}
        maxLength={10_000}
        value={answer}
        onChange={(event) => onAnswerChange(event.target.value)}
        placeholder="Write your answer here. Include your reasoning, approach, and examples where useful…"
        className="mt-4 w-full resize-y rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-3 text-xs leading-5 text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:bg-white focus:ring-4 focus:ring-violet-500/10"
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <span className="text-[9px] text-slate-400">{answer.length}/10,000 characters · minimum 10</span>
        <button
          type="button"
          disabled={pending || answer.trim().length < 10}
          onClick={() => onSubmit(answer.trim())}
          className="inline-flex items-center gap-1.5 rounded-lg bg-violet-700 px-3 py-2 text-[10px] font-semibold text-white hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {pending
            ? <><LoaderCircle size={12} className="animate-spin" /> Reviewing…</>
            : <>{question.evaluation ? 'Re-evaluate' : 'Submit for feedback'} <ArrowRight size={11} /></>}
        </button>
      </div>
      {question.evaluation && (
        <div className="mt-4 rounded-xl border border-violet-100 bg-violet-50/50 p-4">
          <div className="flex items-start gap-2">
            <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-violet-700" />
            <div>
              <p className="text-[11px] font-semibold text-slate-900">Constructive feedback</p>
              <p className="mt-1 text-[10px] leading-5 text-slate-600">{question.evaluation.overall_feedback}</p>
            </div>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {criterionLabels.map(([key, label]) => {
              const criterion = question.evaluation?.[key]
              return criterion ? (
                <div key={key} className="rounded-lg border border-white bg-white/80 p-2.5">
                  <p className="flex items-center justify-between gap-2 text-[9px] font-semibold text-slate-700">
                    {label} <span className="text-violet-700">{criterion.score}/5</span>
                  </p>
                  <p className="mt-1 text-[9px] leading-4 text-slate-500">{criterion.feedback}</p>
                </div>
              ) : null
            })}
          </div>
          {(question.evaluation.strengths.length > 0 || question.evaluation.areas_to_improve.length > 0) && (
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <FeedbackList title="What worked" items={question.evaluation.strengths} />
              <FeedbackList title="Try next time" items={question.evaluation.areas_to_improve} />
            </div>
          )}
        </div>
      )}
    </article>
  )
}

function FeedbackList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-[9px] font-semibold text-slate-700">{title}</p>
      <ul className="mt-1 space-y-1">
        {items.map((item) => <li key={item} className="text-[9px] leading-4 text-slate-500">• {item}</li>)}
      </ul>
    </div>
  )
}

function Notice({
  message,
  loading = false,
  error = false,
}: {
  message: string
  loading?: boolean
  error?: boolean
}) {
  return (
    <div
      role={error ? 'alert' : 'status'}
      className={`flex items-center gap-2 rounded-xl border p-3 text-xs ${
        error
          ? 'border-rose-200 bg-rose-50 text-rose-800'
          : 'border-slate-200 bg-white text-slate-500'
      }`}
    >
      {loading ? <LoaderCircle size={14} className="animate-spin" /> : error ? <CircleAlert size={14} /> : null}
      {message}
    </div>
  )
}

function EmptyNotice({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-7 text-center">
      <RotateCcw size={19} className="mx-auto text-slate-400" />
      <p className="mt-3 text-xs leading-5 text-slate-500">{message}</p>
    </div>
  )
}
