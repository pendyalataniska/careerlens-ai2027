import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, LoaderCircle, Save } from 'lucide-react'
import type { FormEvent } from 'react'
import { useState } from 'react'
import { candidateApi } from '../api/candidate'
import { getApiErrorMessage } from '../api/client'

export function ProfileSettingsPage() {
  const queryClient = useQueryClient()
  const profile = useQuery({ queryKey: ['candidate-profile'], queryFn: candidateApi.profile })
  const [saved, setSaved] = useState(false)
  const update = useMutation({
    mutationFn: candidateApi.updateProfile,
    onSuccess: async () => {
      setSaved(true)
      await queryClient.invalidateQueries({ queryKey: ['candidate-profile'] })
      await queryClient.invalidateQueries({ queryKey: ['candidate-dashboard'] })
    },
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaved(false)
    const form = new FormData(event.currentTarget)
    update.mutate({
      full_name: String(form.get('full_name')),
      headline: String(form.get('headline') || '') || null,
      location: String(form.get('location') || '') || null,
      summary: String(form.get('summary') || '') || null,
    })
  }

  if (profile.isPending) return <p role="status" className="text-sm text-slate-500">Loading profile…</p>
  if (profile.isError) return <p role="alert" className="text-sm text-rose-700">{getApiErrorMessage(profile.error)}</p>

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-violet-700">Account</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-950">Profile and settings</h1>
        <p className="mt-2 text-sm text-slate-600">Update the candidate profile stored with your account.</p>
      </header>
      <form onSubmit={submit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
        <Field label="Full name" name="full_name" defaultValue={`${profile.data.first_name} ${profile.data.last_name}`.trim()} required />
        <Field label="Professional headline" name="headline" defaultValue={profile.data.headline ?? ''} />
        <Field label="Location" name="location" defaultValue={profile.data.location ?? ''} />
        <label className="block text-sm font-medium text-slate-700" htmlFor="summary">Professional summary
          <textarea id="summary" name="summary" defaultValue={profile.data.summary ?? ''} maxLength={5000} rows={6} className="mt-2 block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100" />
        </label>
        <p className="text-xs text-slate-500">Account email: {profile.data.user.email}</p>
        {update.isError && <p role="alert" className="text-sm text-rose-700">{getApiErrorMessage(update.error)}</p>}
        {saved && <p role="status" className="flex items-center gap-2 text-sm text-emerald-700"><CheckCircle2 size={16} /> Profile saved.</p>}
        <button type="submit" disabled={update.isPending} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
          {update.isPending ? <LoaderCircle size={16} className="animate-spin" /> : <Save size={16} />} Save profile
        </button>
      </form>
    </div>
  )
}

function Field({ label, name, defaultValue, required = false }: { label: string; name: string; defaultValue: string; required?: boolean }) {
  return (
    <label htmlFor={name} className="block text-sm font-medium text-slate-700">{label}
      <input id={name} name={name} defaultValue={defaultValue} required={required} maxLength={name === 'full_name' ? 200 : 180} className="mt-2 block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100" />
    </label>
  )
}
