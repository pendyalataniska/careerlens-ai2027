import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, FileText, LoaderCircle, Upload } from 'lucide-react'
import { useState } from 'react'
import { candidateApi } from '../api/candidate'
import { getApiErrorMessage } from '../api/client'

export function ResumeAnalyzerPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string>()
  const [file, setFile] = useState<File>()
  const resumes = useQuery({ queryKey: ['resumes'], queryFn: candidateApi.resumes })
  const resumeId = selectedId ?? resumes.data?.[0]?.id
  const task = useQuery({
    queryKey: ['resume-task', resumeId],
    queryFn: () => candidateApi.resumeTask(resumeId!),
    enabled: Boolean(resumeId),
    refetchInterval: (query) =>
      ['pending', 'processing'].includes(query.state.data?.status ?? '') ? 2000 : false,
  })
  const analysis = useQuery({
    queryKey: ['resume-analysis', resumeId],
    queryFn: () => candidateApi.resumeAnalysis(resumeId!),
    enabled: Boolean(resumeId) && task.data?.status === 'completed',
  })
  const upload = useMutation({
    mutationFn: (selectedFile: File) => candidateApi.uploadResume(selectedFile),
    onSuccess: async (resume) => {
      setSelectedId(resume.id)
      setFile(undefined)
      await queryClient.invalidateQueries({ queryKey: ['resumes'] })
    },
  })

  function submitUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (file) upload.mutate(file)
  }

  if (resumes.isError) {
    return <p role="alert" className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{getApiErrorMessage(resumes.error)}</p>
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-violet-700">Resume intelligence</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-950">Resume analyzer</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">Upload a PDF or DOCX to extract source-labelled resume evidence. Extraction can miss information and does not verify qualifications.</p>
      </header>

      <form onSubmit={submitUpload} className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
        <label htmlFor="resume-file" className="mb-2 block text-sm font-medium text-slate-800">Choose a resume (PDF or DOCX, up to 10 MiB)</label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input id="resume-file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => setFile(event.target.files?.[0])} className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-violet-50 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-violet-700" />
          <button type="submit" disabled={!file || upload.isPending} className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
            {upload.isPending ? <LoaderCircle size={16} className="animate-spin" /> : <Upload size={16} />}
            Upload and analyze
          </button>
        </div>
        {upload.isError && <p role="alert" className="mt-3 text-sm text-rose-700">{getApiErrorMessage(upload.error)}</p>}
      </form>

      {resumes.isPending ? (
        <p role="status" className="text-sm text-slate-500">Loading resumes…</p>
      ) : resumes.data?.length ? (
        <label className="block text-sm font-medium text-slate-700">
          Resume
          <select value={resumeId} onChange={(event) => setSelectedId(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm">
            {resumes.data.map((resume) => (
              <option key={resume.id} value={resume.id}>{new Date(resume.created_at).toLocaleString()} · {resume.extraction_status}</option>
            ))}
          </select>
        </label>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <FileText className="mx-auto text-slate-400" />
          <p className="mt-3 text-sm font-medium text-slate-800">No resumes uploaded</p>
          <p className="mt-1 text-xs text-slate-500">Your uploaded resume will be processed securely and privately.</p>
        </div>
      )}

      {resumeId && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
          {task.isPending || ['pending', 'processing'].includes(task.data?.status ?? '') ? (
            <p role="status" className="flex items-center gap-2 text-sm text-slate-600"><LoaderCircle size={16} className="animate-spin text-violet-600" /> Resume processing is underway… This page checks for updates automatically.</p>
          ) : task.isError ? (
            <p role="alert" className="text-sm text-rose-700">{getApiErrorMessage(task.error)}</p>
          ) : task.data?.status === 'completed' && analysis.isPending ? (
            <p role="status" className="text-sm text-slate-500">Loading extracted evidence…</p>
          ) : task.data?.status === 'completed' && analysis.data ? (
            <div className="space-y-6">
              <div className="flex items-center gap-2 text-emerald-700"><CheckCircle2 size={18} /><h2 className="font-semibold">Analysis complete</h2></div>
              <EvidenceList title="Extracted skills" values={analysis.data.skills.map((skill) => skill.name)} />
              <EvidenceList title="Education evidence" values={analysis.data.education.map((item) => item.text)} />
              <EvidenceList title="Work experience evidence" values={analysis.data.work_experience.map((item) => item.text)} />
              <EvidenceList title="Projects" values={analysis.data.projects.map((item) => item.text)} />
              <EvidenceList title="Certifications" values={analysis.data.certifications.map((item) => item.text)} />
              <Limitations values={analysis.data.limitations} />
            </div>
          ) : (
            <div className="space-y-3">
              <p className="flex items-center gap-2 text-sm font-medium text-slate-800"><AlertCircle size={17} className="text-amber-600" />Processing status: {task.data?.status ?? 'unknown'}</p>
              <Limitations values={task.data?.limitations ?? []} />
              {analysis.isError && <p className="text-xs text-slate-500">Detailed extracted evidence is not available for this document.</p>}
            </div>
          )}
        </section>
      )}
    </div>
  )
}

function EvidenceList({ title, values }: { title: string; values: string[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      {values.length ? (
        <ul className="mt-2 space-y-2">{values.map((value, index) => <li key={`${index}-${value}`} className="rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-700">{value}</li>)}</ul>
      ) : <p className="mt-2 text-sm text-slate-400">No evidence extracted.</p>}
    </div>
  )
}

function Limitations({ values }: { values: string[] }) {
  return values.length ? (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-900">Extraction limitations</h3>
      <ul className="mt-2 list-inside list-disc space-y-1 text-xs leading-5 text-amber-800">{values.map((item) => <li key={item}>{item}</li>)}</ul>
    </div>
  ) : null
}
