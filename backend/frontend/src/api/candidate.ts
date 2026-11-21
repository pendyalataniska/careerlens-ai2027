import { apiClient } from './client'

export interface CandidateProfile {
  id: string
  first_name: string
  last_name: string
  headline: string | null
  location: string | null
  summary: string | null
  user: { id: string; email: string; role: string }
}

export interface CandidateDashboard {
  profile: CandidateProfile
  latest_resume_id: string | null
  resume_status: string | null
  skills: string[]
  matches: Array<{
    id: string
    title: string
    company_name: string | null
    location: string | null
    total_score: number
    created_at: string
  }>
  interview_sessions: number
  completed_interviews: number
  disclaimer: string
}

export interface Resume {
  id: string
  content_type: string
  file_size_bytes: number
  extraction_status: string
  task_id: string | null
  created_at: string
}

export interface ResumeTask {
  resume_id: string
  status: string
  task_id: string | null
  limitations: string[]
}

export interface ResumeEvidence {
  text: string
  source: 'resume_text'
}

export interface ResumeAnalysis {
  resume_id: string
  extraction_status: string
  skills: Array<{ name: string; source: 'resume_text' }>
  skill_section_evidence: ResumeEvidence[]
  education: ResumeEvidence[]
  work_experience: ResumeEvidence[]
  projects: ResumeEvidence[]
  certifications: ResumeEvidence[]
  limitations: string[]
}

export interface Job {
  id: string
  title: string
  description: string
  location: string | null
  employment_type: string | null
  company_name: string | null
  required_skills: string[]
}

export interface JobList {
  items: Job[]
  total: number
  limit: number
  offset: number
}

export interface MatchingResult {
  id: string
  job_id: string
  resume_id: string
  total_score: number
  score_details: {
    matching_skills: string[]
    missing_required_skills: string[]
    explanations: string[]
    score_completeness: string
    components: Record<string, { score: number; explanation: string }>
  }
}

export const candidateApi = {
  dashboard: async () =>
    (await apiClient.get<CandidateDashboard>('/candidates/dashboard')).data,
  profile: async () =>
    (await apiClient.get<CandidateProfile>('/candidates/profile')).data,
  updateProfile: async (profile: Partial<CandidateProfile> & { full_name?: string }) =>
    (await apiClient.put<CandidateProfile>('/candidates/profile', profile)).data,
  resumes: async () =>
    (await apiClient.get<Resume[]>('/resumes')).data,
  uploadResume: async (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return (await apiClient.post<Resume>('/resumes/upload', body)).data
  },
  resumeTask: async (id: string) =>
    (await apiClient.get<ResumeTask>(`/resumes/${id}/task`)).data,
  resumeAnalysis: async (id: string) =>
    (await apiClient.get<ResumeAnalysis>(`/resumes/${id}/analysis`)).data,
  jobs: async () => (await apiClient.get<JobList>('/jobs')).data,
  recruiterJobs: async () => (await apiClient.get<JobList>('/jobs/mine')).data,
  createJob: async (job: {
    title: string
    description: string
    location?: string
    employment_type?: string
    required_skills: string[]
    minimum_experience_years?: number
    required_education?: string
  }) => (await apiClient.post<Job>('/jobs', job)).data,
  recommendations: async (resumeId: string) =>
    (
      await apiClient.get<{ items: MatchingResult[] }>('/matching/recommendations', {
        params: { resume_id: resumeId, limit: 20 },
      })
    ).data.items,
}
