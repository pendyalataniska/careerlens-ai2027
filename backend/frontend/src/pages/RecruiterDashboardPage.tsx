import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BriefcaseBusiness, LoaderCircle, Plus } from 'lucide-react'
import type { FormEvent } from 'react'
import { candidateApi } from '../api/candidate'
import { getApiErrorMessage } from '../api/client'

export function RecruiterDashboardPage() {
  const queryClient = useQueryClient()
  const jobs = useQuery({ queryKey: ['recruiter-jobs'], queryFn: candidateApi.recruiterJobs })
  const create = useMutation({
    mutationFn: candidateApi.createJob,
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['recruiter-jobs'] }),
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    create.mutate({
      title: String(form.get('title')),
      description: String(form.get('description')),
      location: String(form.get('location') || ''),
      employment_type: String(form.get('employment_type') || ''),
      required_skills: String(form.get('required_skills')).split(',').map((skill) => skill.trim()).filter(Boolean),
      minimum_experience_years: form.get('minimum_experience_years') ? Number(form.get('minimum_experience_years')) : undefined,
      required_education: String(form.get('required_education') || ''),
    })
    event.currentTarget.reset()
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-violet-700">Recruiter workspace</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-950">Manage your job listings</h1>
        <p className="mt-2 text-sm text-slate-600">Create roles and review listings owned by your account.</p>
      </header>
      <form onSubmit={submit} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2 sm:p-6">
        <h2 className="sm:col-span-2 text-sm font-semibold text-slate-900">Create a job</h2>
        <Input label="Job title" name="title" required maxLength={180} />
        <Input label="Location" name="location" maxLength={180} />
        <Input label="Employment type" name="employment_type" maxLength={40} />
        <Input label="Required skills (comma separated)" name="required_skills" />
        <Input label="Minimum experience (years)" name="minimum_experience_years" type="number" min={0} max={60} />
        <Input label="Required education (if applicable)" name="required_education" maxLength={300} />
        <label htmlFor="description" className="text-sm font-medium text-slate-700 sm:col-span-2">Job description
          <textarea id="description" name="description" required minLength={20} maxLength={20000} rows={6} className="mt-2 block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal" />
        </label>
        {create.isError && <p role="alert" className="text-sm text-rose-700 sm:col-span-2">{getApiErrorMessage(create.error)}</p>}
        <button disabled={create.isPending} type="submit" className="inline-flex w-fit items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
          {create.isPending ? <LoaderCircle size={16} className="animate-spin" /> : <Plus size={16} />} Publish role
        </button>
      </form>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Your listings</h2>
        {jobs.isPending ? <p role="status" className="text-sm text-slate-500">Loading listings…</p> : null}
        {jobs.isError ? <p role="alert" className="text-sm text-rose-700">{getApiErrorMessage(jobs.error)}</p> : null}
        {!jobs.isPending && jobs.data?.items.length === 0 ? <p className="rounded-xl bg-white p-5 text-sm text-slate-500">You have not published any roles yet.</p> : null}
        <div className="space-y-3">
          {jobs.data?.items.map((job) => (
            <article key={job.id} className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-start gap-3">
                <BriefcaseBusiness size={18} className="mt-0.5 text-violet-600" />
                <div>
                  <h3 className="font-semibold text-slate-900">{job.title}</h3>
                  <p className="mt-1 text-sm text-slate-500">{job.location || 'Location not listed'}{job.employment_type ? ` · ${job.employment_type}` : ''}</p>
                  <div className="mt-3 flex flex-wrap gap-2">{job.required_skills.map((skill) => <span key={skill} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">{skill}</span>)}</div>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900">
        Candidate ranking is not displayed here: there are no applicant records in this workflow. The platform will not invent candidate profiles or rankings.
      </p>
    </div>
  )
}

function Input({ label, name, type = 'text', ...attributes }: { label: string; name: string; type?: string; required?: boolean; maxLength?: number; min?: number; max?: number }) {
  return <label htmlFor={name} className="text-sm font-medium text-slate-700">{label}<input id={name} name={name} type={type} {...attributes} className="mt-2 block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
}
