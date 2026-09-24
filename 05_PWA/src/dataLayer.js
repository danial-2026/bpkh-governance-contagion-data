const LOCAL_MANIFEST_URL = '/data/manifest.json'
const LOCAL_FALLBACK = '/data/pwa_data.json'

// Step 5B: GitHub is the remote source of truth for versioned research releases.
// The local manifest + dataset remain available as the offline/research fallback.
const REMOTE_BASE_URL = 'https://raw.githubusercontent.com/danial-2026/bpkh-governance-contagion-data/main/'
const REMOTE_MANIFEST_URL = `${REMOTE_BASE_URL}manifest.json`
const REMOTE_FALLBACK = `${REMOTE_BASE_URL}pwa_data.json`
const REMOTE_CACHE_KEY = 'bpkh-governance-remote-cache-v1'

async function fetchJson(url, options = {}) {
  const response = await fetch(url, { cache: 'no-store', ...options })
  if (!response.ok) throw new Error(`Data request failed (${response.status}): ${url}`)
  return response.json()
}

function resolveDatasetUrl(manifest, baseUrl) {
  const path = manifest?.dataset_path || 'pwa_data.json'
  return new URL(path.replace(/^\//, ''), baseUrl).toString()
}

function localFallbackManifest(loadMode = 'fallback') {
  return {
    dataset_id: 'bpkh-governance-contagion',
    dataset_version: 'fallback',
    schema_version: '1.0',
    status: 'research_snapshot',
    analytical_status: 'frozen',
    observation_start: '2024-01-01',
    observation_end: '2026-09-03',
    last_updated: null,
    source_label: 'BPKH Governance Contagion Research',
    dataset_path: LOCAL_FALLBACK,
    fallback_path: LOCAL_FALLBACK,
    load_mode: loadMode,
  }
}

export async function loadGovernanceData() {
  // 1) Prefer the remote GitHub manifest and its versioned release.
  try {
    const manifest = await fetchJson(REMOTE_MANIFEST_URL)
    const datasetUrl = resolveDatasetUrl(manifest, REMOTE_BASE_URL)
    const data = await fetchJson(datasetUrl)

    // Persist the last-known-good remote release for offline continuity.
    try {
      localStorage.setItem(REMOTE_CACHE_KEY, JSON.stringify({ manifest, data, cached_at: new Date().toISOString() }))
    } catch {
      // Storage may be unavailable in private/restricted browser contexts; the live result is still valid.
    }

    return {
      data,
      manifest: {
        ...manifest,
        load_mode: 'remote',
        source_url: datasetUrl,
        source_label: manifest.source_label || 'BPKH Governance Contagion Research',
      },
    }
  } catch (remoteError) {
    // 2) Remote unavailable: use the last-known-good remote release if one was cached.
    try {
      const cached = JSON.parse(localStorage.getItem(REMOTE_CACHE_KEY) || 'null')
      if (cached?.data && cached?.manifest) {
        return {
          data: cached.data,
          manifest: {
            ...cached.manifest,
            load_mode: 'cached_remote',
            cached_at: cached.cached_at || null,
          },
        }
      }
    } catch {
      // Ignore malformed/unavailable cache and continue to the local snapshot.
    }

    // 3) No cached remote release: use the local versioned snapshot.
    try {
      const manifest = await fetchJson(LOCAL_MANIFEST_URL)
      const datasetUrl = resolveDatasetUrl(manifest, window.location.origin)
      const data = await fetchJson(datasetUrl)
      return {
        data,
        manifest: {
          ...manifest,
          load_mode: 'local_fallback',
          source_url: datasetUrl,
        },
      }
    } catch (localVersionedError) {
      // 4) Final fallback: the local root snapshot.
      try {
        const data = await fetchJson(LOCAL_FALLBACK)
        return {
          data,
          manifest: localFallbackManifest('local_fallback'),
        }
      } catch (localError) {
        throw new Error('Research data could not be loaded from the remote or local data layer.')
      }
    }
  }
}

export { REMOTE_MANIFEST_URL, REMOTE_FALLBACK }
