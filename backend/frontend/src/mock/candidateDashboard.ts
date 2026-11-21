export interface CandidateMetric {
  label: string
  value: string
  delta: string
  tone: 'violet' | 'blue' | 'green'
}

export interface MatchedJob {
  company: string
  role: string
  location: string
  match: number
  initials: string
  color: string
}

export interface CandidateActivity {
  title: string
  detail: string
  time: string
  icon: 'resume' | 'match' | 'skill'
}

export interface CandidateDashboardData {
  metrics: CandidateMetric[]
  jobs: MatchedJob[]
  activities: CandidateActivity[]
  skills: { name: string; level: number }[]
}

// UI-only sample data. This module is deliberately separate from API services.
export async function getCandidateDashboardDemo(): Promise<CandidateDashboardData> {
  return {
    metrics: [
      { label: 'Resume readiness', value: '82', delta: '+8 this week', tone: 'violet' },
      { label: 'Role matches', value: '24', delta: 'Across 8 companies', tone: 'blue' },
      { label: 'Skills coverage', value: '76%', delta: '3 skills to strengthen', tone: 'green' },
    ],
    jobs: [
      {
        company: 'Vercel',
        role: 'Product Designer',
        location: 'Remote · Full-time',
        match: 92,
        initials: 'V',
        color: 'bg-slate-900',
      },
      {
        company: 'Linear',
        role: 'Senior UX Designer',
        location: 'New York · Hybrid',
        match: 86,
        initials: 'L',
        color: 'bg-violet-700',
      },
      {
        company: 'Notion',
        role: 'Product Design Lead',
        location: 'San Francisco · Hybrid',
        match: 81,
        initials: 'N',
        color: 'bg-amber-600',
      },
    ],
    activities: [
      { title: 'Resume profile updated', detail: 'Your experience section was edited', time: '2 hours ago', icon: 'resume' },
      { title: 'New role added to your list', detail: 'Product Designer at Vercel', time: 'Yesterday', icon: 'match' },
      { title: 'Skills profile reviewed', detail: 'Design systems · Figma · Prototyping', time: '2 days ago', icon: 'skill' },
    ],
    skills: [
      { name: 'Product design', level: 88 },
      { name: 'Figma', level: 82 },
      { name: 'Prototyping', level: 74 },
      { name: 'Design systems', level: 68 },
    ],
  }
}
