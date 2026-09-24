import { useEffect, useMemo, useState } from 'react'
import { loadGovernanceData } from './dataLayer.js'

const NAV = [
  ['overview', 'Overview'],
  ['risk', 'Risk Environment'],
  ['network', 'Governance Network'],
  ['events', 'Contagion Events'],
  ['methodology', 'Methodology'],
]

const COLORS = {
  green: '#18864b',
  yellow: '#b77900',
  red: '#c63d32',
  navy: '#0b1f3a',
}

function levelClass(level) {
  return String(level || '').toLowerCase()
}

function fmt(value, digits = 3) {
  return Number(value ?? 0).toFixed(digits)
}

function latest(data) {
  return data?.monthly_ews?.[data.monthly_ews.length - 1] || {}
}

function MiniLine({ rows, field, color = '#0b1f3a', threshold = null }) {
  if (!rows?.length) return null
  const values = rows.map(r => Number(r[field]) || 0)
  const w = 760, h = 205, padX = 22, padY = 24
  const max = Math.max(1, ...values, threshold ?? 0)
  const min = Math.min(0, ...values, threshold ?? 0)
  const x = i => padX + (i * (w - padX * 2)) / Math.max(1, values.length - 1)
  const y = v => h - padY - ((v - min) / Math.max(0.0001, max - min)) * (h - padY * 2)
  const points = values.map((v, i) => `${x(i)},${y(v)}`).join(' ')
  const latestX = x(values.length - 1), latestY = y(values.at(-1))
  return (
    <div className="trend-wrap">
      <div className="trend-legend">
        <span><i className="legend-line" /> EWS signal</span>
        <span><i className="legend-dash" /> Yellow threshold</span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="sparkline" role="img" aria-label={`${field} monthly trend`}>
        <rect x={0} y={y(1)} width={w} height={Math.max(0, y(0.9)-y(1))} className="risk-band-high" />
        <rect x={0} y={y(0.75)} width={w} height={Math.max(0, y(0.9)-y(0.75))} className="risk-band-watch" />
        <line x1={padX} x2={w-padX} y1={y(0.75)} y2={y(0.75)} className="grid-line" />
        <line x1={padX} x2={w-padX} y1={y(0.5)} y2={y(0.5)} className="grid-line" />
        {threshold !== null && <line x1={padX} x2={w-padX} y1={y(threshold)} y2={y(threshold)} className="threshold-line" />}
        <polyline points={points} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        {values.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={i === values.length - 1 ? 6 : 2.7} className={i === values.length - 1 ? 'trend-point latest' : 'trend-point'} />)}
        <g className="latest-label">
          <rect x={Math.min(w-78, latestX+10)} y={Math.max(8, latestY-22)} width="68" height="25" rx="8" />
          <text x={Math.min(w-44, latestX+44)} y={Math.max(25, latestY-5)} textAnchor="middle">{fmt(values.at(-1))}</text>
        </g>
      </svg>
      <div className="trend-scale"><span>Jan 2024</span><span>Sep 2026</span></div>
    </div>
  )
}
function RiskBars({ rows }) {
  const max = Math.max(...rows.map(r => Number(r.mean_score) || 0), 0.001)
  return (
    <div className="risk-bars">
      {rows.map(row => (
        <div className="risk-row" key={row.dimension}>
          <div className="risk-row-head">
            <span>{row.dimension.replaceAll('_', ' ')}</span>
            <strong>{fmt(row.mean_score)}</strong>
          </div>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${(row.mean_score / max) * 100}%` }} /></div>
          <div className="risk-meta">{row.documents} documents · {fmt(row.prevalence_pct, 2)}%</div>
        </div>
      ))}
    </div>
  )
}

function Network({ nodes, edges }) {
  const positions = {
    Quota_Governance: [18, 28],
    Hajj_Fund_Management: [78, 22],
    Public_Trust_Reputation: [58, 40],
    BPKH_Governance: [35, 60],
    Corruption_Investigation: [72, 76],
    Governance_Oversight: [16, 86],
  }
  const nodeMap = Object.fromEntries(nodes.map(n => [n.node, n]))
  return (
    <div className="network-box">
      <svg viewBox="0 0 900 520" className="network-svg">
        {edges.map((e, i) => {
          const a = positions[e.source], b = positions[e.target]
          if (!a || !b) return null
          const width = Math.max(1.5, Math.min(8, Number(e.association_strength || 1) * 1.5))
          return <g key={i}>
            <line x1={a[0]*9} y1={a[1]*5.2} x2={b[0]*9} y2={b[1]*5.2} stroke="#a7b0bd" strokeWidth={width} opacity=".75" />
            <text x={(a[0]*9+b[0]*9)/2} y={(a[1]*5.2+b[1]*5.2)/2-6} className="edge-label">{e.cooccurrence_count}</text>
          </g>
        })}
        {nodes.map(n => {
          const p = positions[n.node]
          if (!p) return null
          const r = 22 + Number(n.NCI || 0) * 24
          return <g key={n.node}>
            <circle cx={p[0]*9} cy={p[1]*5.2} r={r} className="node-circle" />
            <text x={p[0]*9} y={p[1]*5.2+4} textAnchor="middle" className="node-nci">{fmt(n.NCI)}</text>
            <text x={p[0]*9} y={p[1]*5.2+r+18} textAnchor="middle" className="node-label">{n.label}</text>
          </g>
        })}
      </svg>
      <div className="network-note">Node size reflects NCI; edge labels show document co-occurrence counts.</div>
    </div>
  )
}

export default function App() {
  const [data, setData] = useState(null)
  const [manifest, setManifest] = useState(null)
  const [page, setPage] = useState('overview')
  const [error, setError] = useState('')

  useEffect(() => {
    loadGovernanceData()
      .then(({ data: dataset, manifest: metadata }) => {
        setData(dataset)
        setManifest(metadata)
      })
      .catch(e => setError(e.message))
  }, [])

  const current = latest(data)
  const topEvents = useMemo(() => {
    return [...(data?.contagion_events || [])]
      .sort((a, b) => Number(b.document_contagion_score) - Number(a.document_contagion_score))
      .slice(0, 5)
  }, [data])

  if (error) return <div className="error-screen"><h1>Data unavailable</h1><p>{error}</p></div>
  if (!data) return <div className="loading">Loading governance intelligence…</div>

  const snapshotLabel = manifest?.dataset_version || '—'
  const observationLabel = `${manifest?.observation_start || '—'} — ${manifest?.observation_end || '—'}`
  const modeLabels = { remote: 'REMOTE · GITHUB', cached_remote: 'CACHED REMOTE', local_fallback: 'LOCAL FALLBACK', fallback: 'LOCAL FALLBACK' }
  const loadMode = modeLabels[manifest?.load_mode] || 'DATA LAYER'
  const loadModeClass = manifest?.load_mode === 'remote' ? '' : 'fallback'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><span>B</span><small>G</small></div>
          <div>
            <div className="brand-title">BPKH Governance Intelligence</div>
            <div className="brand-sub">Governance Contagion · Early Warning</div>
          </div>
        </div>
        <nav>
          {NAV.map(([id, label]) => (
            <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => setPage(id)}>
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="dot green"></span>
          Research snapshot
          <small>{snapshotLabel} · {manifest?.analytical_status || 'frozen'}</small>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">GOVERNANCE CONTAGION EARLY WARNING</div>
            <h1>{NAV.find(x => x[0] === page)?.[1]}</h1>
          </div>
          <div className="topbar-meta">
            <span className="research-badge"><i /> RESEARCH PROTOTYPE</span>
            <span className={`data-badge ${loadModeClass}`}><i /> {loadMode}</span>
            <div className="snapshot"><span>Latest analytical period</span><strong>{current.month || '—'}</strong></div>
          </div>
        </header>

        {page === 'overview' && (
          <>
            <section className="hero">
              <div className="hero-copy">
                <div className="hero-overline"><span className="pulse-dot" /> CURRENT GOVERNANCE-RISK SIGNAL</div>
                <h2>Governance-risk environment</h2>
                <p>External governance narratives, BPKH exposure, public trust, network connectedness, and unusual observations are monitored as complementary decision-support signals.</p>
                <div className="hero-meta"><span>Observation period</span><b>{observationLabel}</b></div>
              </div>
              <div className={`status-panel ${levelClass(current.ews_level)}`}>
                <span>EWS STATUS</span><strong>{current.ews_level}</strong><small>Current analytical signal</small>
              </div>
            </section>

            <section className="metric-grid">
              <Metric title="AI-based EWS" value={fmt(current.ews)} level={current.ews_level} primary />
              <Metric title="Governance Contagion Risk" value={fmt(current.gcr)} level={current.gcr_level} />
              <Metric title="Network Contagion Index" value={fmt(current.nci)} caption="Structural connectedness" />
              <Metric title="Anomaly Signal" value={fmt(current.anomaly_score)} caption="Unusual multivariate condition" />
            </section>

            <section className="grid-2">
              <Card title="EWS trajectory" subtitle="Monthly analytical signal">
                <MiniLine rows={data.monthly_ews} field="ews" color={COLORS.navy} threshold={0.572} />
              </Card>
              <Card title="Risk dimensions" subtitle="Semantic profile from the research corpus">
                <RiskBars rows={data.risk_dimensions} />
              </Card>
            </section>

            <section className="grid-2">
              <Card title="Highest contagion events" subtitle="Ranked by analytical contagion score">
                <div className="event-list">
                  {topEvents.map((e, i) => (
                    <div className="event-item" key={e.event_id}>
                      <span className="event-rank">{String(i + 1).padStart(2, '0')}</span>
                      <div className="event-main">
                        <strong>{e.event_id}</strong>
                        <span>{String(e.risk_dimensions).replaceAll(';', ' · ').replaceAll('_', ' ')}</span>
                      </div>
                      <b>{fmt(e.document_contagion_score)}</b>
                    </div>
                  ))}
                </div>
              </Card>
              <Card title="Interpretation" subtitle="How to use the signal">
                <div className="interpretation">
                  <div className="interpretation-icon">!</div>
                  <p>The EWS is an analytical decision-support signal. It is not an official BPKH risk rating, a corruption detector, or evidence of causal risk transmission.</p>
                </div>
                <div className="decision-strip"><span>INSTITUTIONAL USE</span><strong>Detect · Assess · Alert · Respond · Learn</strong></div>
              </Card>
            </section>
          </>
        )}

        {page === 'risk' && (
          <section className="page-content">
            <Card title="Risk environment" subtitle="Seven dimensions used in the guided semantic mapping">
              <RiskBars rows={data.risk_dimensions} />
            </Card>
            <div className="info-grid">
              <Info title="External crisis" text="Quota Governance, Corruption / Investigation, and Governance Oversight." />
              <Info title="BPKH exposure" text="BPKH Governance and Hajj Fund Management." />
              <Info title="Trust risk" text="Public Trust / Reputation." />
              <Info title="Response" text="Clarification / Response is treated as mitigation, not contagion evidence." />
            </div>
          </section>
        )}

        {page === 'network' && (
          <section className="page-content">
            <Card title="Governance risk co-occurrence network" subtitle="Structural connectedness among risk dimensions">
              <Network nodes={data.network_nodes} edges={data.network_edges} />
            </Card>
            <div className="node-grid">
              {data.network_nodes.map(n => (
                <div className="node-card" key={n.node}>
                  <span>{n.label}</span>
                  <strong>{fmt(n.NCI)}</strong>
                  <small>NCI</small>
                </div>
              ))}
            </div>
          </section>
        )}

        {page === 'events' && (
          <section className="page-content">
            <Card title="Governance contagion events" subtitle="Event size and contagion score are analytically distinct">
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Event</th><th>Documents</th><th>Score</th><th>Risk dimensions</th></tr></thead>
                  <tbody>
                    {[...(data.contagion_events || [])].sort((a,b) => Number(b.document_contagion_score)-Number(a.document_contagion_score)).map(e => (
                      <tr key={e.event_id}>
                        <td><strong>{e.event_id}</strong></td>
                        <td>{e.event_size}</td>
                        <td>{fmt(e.document_contagion_score)}</td>
                        <td>{String(e.risk_dimensions).replaceAll(';', ' · ').replaceAll('_', ' ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </section>
        )}

        {page === 'methodology' && (
          <section className="page-content">
            <div className="method-flow">
              {['Guided semantic mapping', 'GCI', 'Network analysis', 'Temporal analysis', 'Isolation Forest', 'AI-based EWS'].map((x, i) => (
                <div className="method-step" key={x}><span>{i + 1}</span><strong>{x}</strong></div>
              ))}
            </div>
            <Card title="Responsible interpretation" subtitle="Research prototype">
              <p className="method-copy">The Governance Contagion EWS is an analytical decision-support framework for monitoring governance-risk conditions. It does not constitute an official BPKH risk rating, a probability of corruption, a prediction of financial loss, or evidence of causal transmission.</p>
            </Card>
          </section>
        )}

        <footer className="footer">
          <span>BPKH Governance Intelligence · Research prototype v0.4</span>
          <span>Dataset {snapshotLabel} · {loadMode}</span>
        </footer>
      </main>
    </div>
  )
}

function Metric({ title, value, level, caption, primary }) {
  return (
    <div className={`metric-card ${primary ? 'metric-primary' : ''}`}>
      <span>{title}</span>
      <strong>{value}</strong>
      {level ? <em className={levelClass(level)}>{level}</em> : <small>{caption}</small>}
    </div>
  )
}

function Card({ title, subtitle, children }) {
  return <section className="card">
    <div className="card-head"><div><h3>{title}</h3><p>{subtitle}</p></div></div>
    {children}
  </section>
}

function Info({ title, text }) {
  return <div className="info-card"><strong>{title}</strong><p>{text}</p></div>
}
