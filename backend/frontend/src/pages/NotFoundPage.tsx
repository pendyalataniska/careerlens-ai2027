import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-8">
      <p className="text-sm font-semibold text-indigo-600">404</p>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">
        Page not found
      </h1>
      <p className="mt-2 text-slate-600">
        The page you requested does not exist.
      </p>
      <Link
        to="/"
        className="mt-5 inline-block font-semibold text-indigo-700 hover:text-indigo-900"
      >
        Return to dashboard
      </Link>
    </section>
  )
}
