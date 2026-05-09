/**
 * Typed API client for the Spencer backend.
 */

import type {
  AnalysisRequest,
  AnalysisResult,
  AppError,
  CriticalCircleRequest,
  CriticalCircleResult,
  JobCreateResponse,
  JobStatus,
  ErrorResponse,
  ValidationResponse,
} from './types';

export const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Generic fetch helper
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = 60_000,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...init,
    });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('TIMEOUT', `La requête a expiré après ${timeoutMs / 1000}s. Vérifiez que le serveur backend est démarré.`);
    }
    throw new ApiError('NETWORK_ERROR', 'Impossible de joindre le serveur. Vérifiez que le backend est démarré sur le port 8000.');
  }
  clearTimeout(timer);

  if (!res.ok) {
    let errorPayload: ErrorResponse | null = null;
    try {
      errorPayload = (await res.json()) as ErrorResponse;
    } catch {
      // Response body was not JSON
    }

    if (errorPayload?.error) {
      const err: AppError = errorPayload.error;
      throw new ApiError(err.code, err.message, err.details);
    }

    throw new ApiError('HTTP_ERROR', `HTTP ${res.status}: ${res.statusText}`);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

/**
 * Run a full Spencer analysis for the given request.
 */
export async function runAnalysis(req: AnalysisRequest): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>('/api/analysis/evaluate-circle', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

/**
 * Search the critical slip circle synchronously.
 */
export async function runCriticalCircle(
  req: CriticalCircleRequest,
): Promise<CriticalCircleResult> {
  return apiFetch<CriticalCircleResult>('/api/analysis/critical-circle', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

/**
 * Create a background critical-circle job for heavy searches.
 */
export async function createAnalysisJob(
  req: CriticalCircleRequest,
): Promise<JobCreateResponse> {
  return apiFetch<JobCreateResponse>('/api/analysis/jobs', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function getAnalysisJob(jobId: string): Promise<JobStatus> {
  return apiFetch<JobStatus>(`/api/analysis/jobs/${jobId}`);
}

/**
 * Validate geometry and layer inputs without running the solver.
 */
export async function validateGeometry(
  req: AnalysisRequest,
): Promise<ValidationResponse> {
  return apiFetch<ValidationResponse>('/api/analysis/validate', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}
