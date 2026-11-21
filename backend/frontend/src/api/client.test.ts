import { describe, expect, it } from 'vitest'
import { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import { getApiErrorMessage } from './client'

function makeError(detail: string | Array<{ msg?: string }>, status: number, statusText: string) {
  const config: InternalAxiosRequestConfig = {
    headers: new AxiosHeaders(),
    method: 'get',
    url: '/',
  }
  const error = new AxiosError('request failed')
  error.response = {
    data: { detail },
    status,
    statusText,
    headers: new AxiosHeaders(),
    config,
  }
  return error
}

describe('getApiErrorMessage', () => {
  it('returns a server-provided detail message', () => {
    const error = makeError('Resume is too large.', 413, 'Payload Too Large')
    expect(getApiErrorMessage(error)).toBe('Resume is too large.')
  })

  it('returns the first validation issue', () => {
    const error = makeError([{ msg: 'Invalid email address.' }], 422, 'Unprocessable Entity')
    expect(getApiErrorMessage(error)).toBe('Invalid email address.')
  })

  it('provides a safe message for an unknown error', () => {
    expect(getApiErrorMessage(new Error('internal'))).toBe('The request could not be completed.')
  })
})
