import { useQuery } from '@tanstack/react-query'
import { candidateApi } from '../api/candidate'

export function useCandidateDashboard() {
  return useQuery({
    queryKey: ['candidate-dashboard'],
    queryFn: candidateApi.dashboard,
    staleTime: 60_000,
  })
}
