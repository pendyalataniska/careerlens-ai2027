import { Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

export function BrandMark({ light = false }: { light?: boolean }) {
  return (
    <Link
      to="/"
      className={`inline-flex items-center gap-2.5 text-lg font-semibold tracking-tight ${
        light ? 'text-white' : 'text-slate-950'
      }`}
    >
      <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-500 text-white shadow-md shadow-violet-900/20">
        <Sparkles size={17} />
      </span>
      CareerLens<span className="-ml-2 text-violet-500">.</span>
    </Link>
  )
}
