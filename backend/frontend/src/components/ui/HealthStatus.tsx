import { getApiErrorMessage } from '../../api/client'
import { useHealth } from '../../hooks/useHealth'

export function HealthStatus() {
  const health = useHealth()

  if (health.isPending) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <p className="text-sm font-medium text-slate-700">Checking API status…</p>
      </div>
    )
  }

  if (health.isError) {
    return (
      <div
        role="status"
        className="rounded-xl border border-rose-200 bg-rose-50 p-5"
      >
        <p className="font-semibold text-rose-800">API unavailable</p>
        <p className="mt-1 text-sm text-rose-700">
          {getApiErrorMessage(health.error)}
        </p>
      </div>
    )
  }

  return (
    <div
      role="status"
      className="rounded-xl border border-emerald-200 bg-emerald-50 p-5"
    >
      <p className="font-semibold text-emerald-800">API connected</p>
      <p className="mt-1 text-sm text-emerald-700">
        Backend status: {health.data.status}
      </p>
    </div>
  )
}
