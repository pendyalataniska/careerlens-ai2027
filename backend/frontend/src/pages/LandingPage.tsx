import {
  ArrowRight,
  BarChart3,
  Check,
  FileSearch2,
  MoveUpRight,
  ScanSearch,
  Sparkles,
  Target,
  UserRoundCheck,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { BrandMark } from '../components/ui/BrandMark'

const features = [
  {
    icon: FileSearch2,
    title: 'Resume intelligence',
    description:
      'Turn your experience into a clear, structured profile that is easier to refine and share.',
    tint: 'bg-violet-100 text-violet-700',
  },
  {
    icon: Target,
    title: 'Role alignment',
    description:
      'Understand how your profile relates to the roles you are exploring, with context you can act on.',
    tint: 'bg-indigo-100 text-indigo-700',
  },
  {
    icon: BarChart3,
    title: 'Skills development',
    description:
      'See areas to strengthen and build a practical plan around your career goals.',
    tint: 'bg-fuchsia-100 text-fuchsia-700',
  },
]

const steps = [
  { number: '01', title: 'Build your profile', description: 'Bring your experience and career goals into one clear workspace.' },
  { number: '02', title: 'Explore your direction', description: 'Review relevant roles and the skills they ask for.' },
  { number: '03', title: 'Move forward with confidence', description: 'Prepare, grow, and take your next step with intention.' },
]

export function LandingPage() {
  return (
    <div className="overflow-hidden bg-white">
      <header className="relative z-10 border-b border-white/10 bg-[#111128]">
        <nav className="mx-auto flex h-[76px] max-w-7xl items-center justify-between px-5 sm:px-8">
          <BrandMark light />
          <div className="hidden items-center gap-8 md:flex">
            <a href="#features" className="text-xs text-slate-300 transition hover:text-white">Platform</a>
            <a href="#how-it-works" className="text-xs text-slate-300 transition hover:text-white">How it works</a>
            <a href="#about" className="text-xs text-slate-300 transition hover:text-white">Our approach</a>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link to="/login" className="rounded-lg px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/10">
              Log in
            </Link>
            <Link to="/register" className="inline-flex items-center gap-2 rounded-lg bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-950 shadow-lg shadow-black/10 transition hover:bg-violet-50 sm:px-4">
              Get started <ArrowRight size={14} />
            </Link>
          </div>
        </nav>
      </header>

      <main>
        <section className="relative overflow-hidden bg-[#111128]">
          <div className="pointer-events-none absolute -right-36 -top-40 size-[520px] rounded-full bg-violet-600/20 blur-[120px]" />
          <div className="pointer-events-none absolute -bottom-48 left-1/4 size-[460px] rounded-full bg-indigo-600/20 blur-[120px]" />
          <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 pb-20 pt-16 sm:px-8 sm:pb-24 sm:pt-24 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8 lg:pb-28 lg:pt-28">
            <div className="max-w-2xl">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-300/20 bg-violet-300/10 px-3 py-1.5 text-[10px] font-medium tracking-wide text-violet-200">
                <Sparkles size={13} />
                A clearer path to your next opportunity
              </div>
              <h1 className="max-w-[680px] text-[42px] font-semibold leading-[1.08] tracking-[-0.045em] text-white sm:text-6xl lg:text-[68px]">
                Your career, seen{' '}
                <span className="bg-gradient-to-r from-violet-300 via-fuchsia-200 to-indigo-300 bg-clip-text text-transparent">
                  more clearly.
                </span>
              </h1>
              <p className="mt-6 max-w-xl text-sm leading-7 text-slate-300 sm:text-base">
                Make thoughtful career moves with a workspace for your experience,
                the roles you want, and the skills to get there.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link to="/register" className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-indigo-500 px-5 py-3.5 text-xs font-semibold text-white shadow-lg shadow-violet-950/40 transition hover:brightness-110">
                  Create your free account <ArrowRight size={15} />
                </Link>
                <a href="#how-it-works" className="rounded-xl border border-white/15 px-5 py-3.5 text-xs font-medium text-white transition hover:bg-white/5">
                  See how it works
                </a>
              </div>
              <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-[10px] text-slate-400">
                <span className="inline-flex items-center gap-1.5"><Check size={13} className="text-emerald-300" /> Your goals, your direction</span>
                <span className="inline-flex items-center gap-1.5"><Check size={13} className="text-emerald-300" /> One workspace to grow</span>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-[510px] lg:ml-auto">
              <div className="absolute -inset-8 rounded-[36px] bg-gradient-to-br from-violet-500/20 to-indigo-500/10 blur-2xl" />
              <div className="relative rounded-[26px] border border-white/10 bg-[#1a1b37]/90 p-4 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-5">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div className="flex items-center gap-2.5">
                    <span className="grid size-8 place-items-center rounded-lg bg-violet-500/20 text-violet-200"><Sparkles size={15} /></span>
                    <div>
                      <p className="text-[11px] font-semibold text-white">Career workspace</p>
                      <p className="mt-0.5 text-[9px] text-slate-400">A preview of what's possible</p>
                    </div>
                  </div>
                  <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-2 py-1 text-[8px] uppercase tracking-wide text-amber-200">Product preview</span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                    <p className="text-[9px] text-slate-400">Your next chapter</p>
                    <p className="mt-2 text-sm font-semibold text-white">Product design</p>
                    <div className="mt-4 flex items-end gap-1.5">
                      {[32, 44, 38, 58, 52, 72, 64, 86, 74, 96].map((height, index) => (
                        <span key={index} className="flex-1 rounded-t-sm bg-gradient-to-t from-violet-600 to-fuchsia-300/80" style={{ height: `${height}px` }} />
                      ))}
                    </div>
                    <p className="mt-3 text-[8px] text-slate-500">Illustrative visual · not an assessment</p>
                  </div>
                  <div className="flex flex-col gap-3">
                    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                      <div className="flex items-center gap-2 text-violet-200"><ScanSearch size={14} /><span className="text-[9px] font-medium">Profile insights</span></div>
                      <p className="mt-3 text-xs font-semibold text-white">Your experience, organized</p>
                      <p className="mt-1 text-[9px] leading-4 text-slate-400">Bring your strengths into focus.</p>
                    </div>
                    <div className="rounded-2xl border border-indigo-300/15 bg-indigo-400/[0.08] p-4">
                      <div className="flex items-center gap-2 text-indigo-200"><UserRoundCheck size={14} /><span className="text-[9px] font-medium">Career direction</span></div>
                      <p className="mt-3 text-xs font-semibold text-white">Explore what fits</p>
                      <div className="mt-2 flex items-center justify-between text-[9px] text-slate-400"><span>Roles to discover</span><MoveUpRight size={12} /></div>
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.035] px-3.5 py-3">
                  <div className="flex items-center gap-2.5">
                    <span className="grid size-7 place-items-center rounded-lg bg-emerald-400/10 text-emerald-300"><Check size={14} /></span>
                    <span className="text-[10px] text-slate-200">A plan built around your goals</span>
                  </div>
                  <ArrowRight size={14} className="text-slate-400" />
                </div>
              </div>
              <div className="absolute -left-7 top-1/3 hidden rounded-2xl border border-white/10 bg-[#242443] p-3 shadow-xl sm:block">
                <div className="flex items-center gap-2">
                  <span className="grid size-7 place-items-center rounded-lg bg-fuchsia-400/15 text-fuchsia-200"><Target size={14} /></span>
                  <div><p className="text-[9px] text-slate-400">Built around</p><p className="text-[10px] font-semibold text-white">Your next move</p></div>
                </div>
              </div>
            </div>
          </div>
          <div className="relative border-t border-white/[0.08]">
            <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-5 py-5 text-center sm:flex-row sm:px-8 sm:text-left">
              <p className="text-[10px] text-slate-400">A thoughtful toolkit for every step of your career journey.</p>
              <p className="text-[9px] text-slate-500">AI-powered capabilities are being developed; no AI predictions are shown in this preview.</p>
            </div>
          </div>
        </section>

        <section id="features" className="scroll-mt-12 px-5 py-20 sm:px-8 sm:py-24">
          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-2xl text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-600">A better career toolkit</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Make every next step count.</h2>
              <p className="mt-4 text-sm leading-6 text-slate-500">Bring your career story, opportunities, and growth plans together in one considered experience.</p>
            </div>
            <div className="mt-11 grid gap-4 md:grid-cols-3">
              {features.map(({ icon: Icon, title, description, tint }) => (
                <article key={title} className="group rounded-2xl border border-slate-200/80 bg-white p-6 transition hover:-translate-y-1 hover:border-violet-200 hover:shadow-xl hover:shadow-violet-950/[0.05]">
                  <span className={`grid size-11 place-items-center rounded-2xl ${tint}`}><Icon size={20} /></span>
                  <h3 className="mt-5 text-sm font-semibold text-slate-900">{title}</h3>
                  <p className="mt-2 text-xs leading-6 text-slate-500">{description}</p>
                  <span className="mt-5 inline-flex items-center gap-1.5 text-[10px] font-medium text-violet-700">Explore the platform <ArrowRight size={12} className="transition group-hover:translate-x-1" /></span>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="scroll-mt-12 border-y border-slate-200/80 bg-[#f7f6fb] px-5 py-20 sm:px-8 sm:py-24">
          <div className="mx-auto max-w-7xl">
            <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr] lg:gap-20">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-600">How it works</p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">From where you are to where you want to be.</h2>
                <p className="mt-4 text-sm leading-6 text-slate-500">A simple, human-centered way to bring your goals into focus and keep momentum.</p>
                <Link to="/register" className="mt-6 inline-flex items-center gap-2 text-xs font-semibold text-violet-700 hover:text-violet-900">Start your journey <ArrowRight size={14} /></Link>
              </div>
              <div className="space-y-3">
                {steps.map((step) => (
                  <article key={step.number} className="flex gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 sm:gap-5 sm:p-6">
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-violet-50 text-xs font-semibold text-violet-700">{step.number}</span>
                    <div><h3 className="text-sm font-semibold text-slate-900">{step.title}</h3><p className="mt-1.5 text-xs leading-5 text-slate-500">{step.description}</p></div>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="about" className="scroll-mt-12 px-5 py-20 sm:px-8 sm:py-24">
          <div className="mx-auto max-w-5xl rounded-[28px] bg-gradient-to-br from-[#17162f] via-[#211b43] to-[#35205e] px-6 py-12 text-center sm:px-12 sm:py-16">
            <span className="mx-auto grid size-11 place-items-center rounded-2xl border border-white/10 bg-white/10 text-violet-200"><Sparkles size={19} /></span>
            <p className="mt-5 text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-200">Your career has a next chapter</p>
            <h2 className="mx-auto mt-3 max-w-2xl text-3xl font-semibold tracking-tight text-white sm:text-4xl">Make space for what comes next.</h2>
            <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-slate-300">Create your CareerLens workspace and bring your next move into focus.</p>
            <Link to="/register" className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-xs font-semibold text-slate-950 transition hover:bg-violet-50">Create your account <ArrowRight size={14} /></Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white px-5 py-7 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 sm:flex-row">
          <BrandMark />
          <p className="text-center text-[10px] text-slate-500">CareerLens AI · Career decisions, grounded in your goals.</p>
          <div className="flex gap-4 text-[10px] text-slate-500"><Link to="/login" className="hover:text-violet-700">Log in</Link><Link to="/register" className="hover:text-violet-700">Register</Link></div>
        </div>
      </footer>
    </div>
  )
}
