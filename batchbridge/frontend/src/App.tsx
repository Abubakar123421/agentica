import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api } from "./api";
import type {
  AgentRun,
  CaseDetail,
  CaseSummary,
  Escalation,
  Inspection,
  Proposal,
  User,
} from "./types";

const agentMeta = {
  triage: { number: "01", title: "Triage", description: "Normalizes the report and missing facts" },
  traceability: {
    number: "02",
    title: "Traceability",
    description: "Matches the exact lot and shipment recipients",
  },
  escalation: {
    number: "03",
    title: "Escalation",
    description: "Builds a manufacturer evidence packet",
  },
} as const;

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDate(value: string | null) {
  if (!value) return "Pending";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function asArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
}

function Pill({ value }: { value: string }) {
  const tone =
    value.includes("approved") || value.includes("completed") || value.includes("responded")
      ? "success"
      : value.includes("failed") || value.includes("rejected")
        ? "danger"
        : value.includes("waiting") || value.includes("pending") || value.includes("human")
          ? "warning"
          : "neutral";
  return <span className={`pill pill-${tone}`}>{label(value)}</span>;
}

function PublicReport({ onLogin }: { onLogin: () => void }) {
  const [form, setForm] = useState({
    reporter_name: "",
    reporter_email: "",
    retailer_code: "RETAILER-A",
    product_name: "SweetCo Alpine Milk Chocolate 100g",
    batch_number: "38",
    purchase_date: "",
    description: "",
  });
  const [created, setCreated] = useState<Awaited<ReturnType<typeof api.report>> | null>(null);
  const [trackingToken, setTrackingToken] = useState("");
  const [tracked, setTracked] = useState<Awaited<ReturnType<typeof api.track>> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, value]) => value));
      setCreated(await api.report(payload));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to submit report");
    } finally {
      setBusy(false);
    }
  }

  async function track(event: FormEvent) {
    event.preventDefault();
    setError("");
    setTracked(null);
    try {
      setTracked(await api.track(trackingToken.trim()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to find report");
    }
  }

  return (
    <main className="public-shell">
      <nav className="public-nav">
        <a className="brand" href="/" aria-label="BatchBridge home">
          <span className="brand-mark">BB</span>
          <span>BatchBridge</span>
        </a>
        <button className="button button-ghost" onClick={onLogin}>Staff sign in</button>
      </nav>
      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">Human-approved food safety investigations</span>
          <h1>Trace one complaint across an entire supply chain.</h1>
          <p>
            Report a suspected product issue. BatchBridge helps the importer connect the exact lot
            to recorded retailers while people control every safety decision.
          </p>
          <div className="trust-row">
            <span>01 · Report</span><span>02 · Verify</span><span>03 · Coordinate</span>
          </div>
          <form className="tracking-box" onSubmit={track}>
            <div><strong>Already submitted?</strong><span>Use your private token to check progress.</span></div>
            <div className="tracking-controls"><input aria-label="Private tracking token" required value={trackingToken} onChange={(event) => setTrackingToken(event.target.value)} placeholder="Paste tracking token" /><button className="button button-secondary">Track</button></div>
            {tracked && <div className="tracking-result"><div><strong>{tracked.case_id}</strong><span>{tracked.product_name}</span></div><Pill value={tracked.status} /><Pill value={tracked.safety_verdict} /></div>}
          </form>
        </div>
        <form className="report-card" onSubmit={submit}>
          <div>
            <span className="eyebrow">Public report</span>
            <h2>Tell us what happened</h2>
            <p className="muted">A report starts an investigation. It does not confirm contamination.</p>
          </div>
          <div className="form-grid two">
            <label>Name<input value={form.reporter_name} onChange={(event) => setForm({ ...form, reporter_name: event.target.value })} /></label>
            <label>Email<input type="email" value={form.reporter_email} onChange={(event) => setForm({ ...form, reporter_email: event.target.value })} /></label>
          </div>
          <label>Product<input required minLength={2} value={form.product_name} onChange={(event) => setForm({ ...form, product_name: event.target.value })} /></label>
          <div className="form-grid two">
            <label>Retailer code<input value={form.retailer_code} onChange={(event) => setForm({ ...form, retailer_code: event.target.value })} /></label>
            <label>Batch or lot<input value={form.batch_number} onChange={(event) => setForm({ ...form, batch_number: event.target.value })} /></label>
          </div>
          <label>Purchase date<input type="date" value={form.purchase_date} onChange={(event) => setForm({ ...form, purchase_date: event.target.value })} /></label>
          <label>What did you observe?<textarea required minLength={10} rows={4} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          {error && <div className="alert danger">{error}</div>}
          {created && (
            <div className="alert success">
              <strong>Report {created.case_id} created.</strong>
              <span>Save this private tracking token: <code>{created.tracking_token}</code></span>
            </div>
          )}
          <button className="button button-primary" disabled={busy}>{busy ? "Submitting…" : "Submit suspected issue"}</button>
        </form>
      </section>
    </main>
  );
}

function Login({ onSuccess, onBack }: { onSuccess: (user: User) => void; onBack: () => void }) {
  const [email, setEmail] = useState("importer@batchbridge.demo");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onSuccess(await api.login(email, password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <button className="back-link" onClick={onBack}>← Return to report form</button>
      <form className="login-card" onSubmit={submit}>
        <span className="brand-mark large">BB</span>
        <div><span className="eyebrow">Operations portal</span><h1>Continue your investigation</h1></div>
        <label>Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>Password<input required type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error && <div className="alert danger">{error}</div>}
        <button className="button button-primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="muted small">Use a seeded account and the configured DEMO_PASSWORD.</p>
      </form>
    </main>
  );
}

function AgentCard({ agent, run }: { agent: keyof typeof agentMeta; run?: AgentRun }) {
  const meta = agentMeta[agent];
  const result = run?.result;
  const toolCalls = asArray(result?.tool_calls);
  const confidence = typeof result?.confidence === "string" ? result.confidence : null;
  const recommendation =
    typeof result?.recommendation === "string" ? result.recommendation : null;
  return (
    <article className={`agent-card ${run ? "active" : "locked"}`}>
      <div className="agent-heading">
        <span className="agent-number">{meta.number}</span>
        <div><h3>{meta.title} Agent</h3><p>{meta.description}</p></div>
        <Pill value={run?.status ?? "locked"} />
      </div>
      {run ? (
        <div className="agent-body">
          <div className="metric-row">
            {confidence && <span><small>Confidence</small><strong>{label(confidence)}</strong></span>}
            {recommendation && <span><small>Recommendation</small><strong>{label(recommendation)}</strong></span>}
            <span><small>MCP calls</small><strong>{toolCalls.length}</strong></span>
          </div>
          {toolCalls.length > 0 && (
            <div className="tool-list">
              {toolCalls.map((call, index) => (
                <span key={`${String(call.tool)}-${index}`}>{String(call.tool)} · {String(call.record_count ?? 0)} records</span>
              ))}
            </div>
          )}
          {run.error && <div className="alert danger">{run.error}</div>}
        </div>
      ) : <p className="locked-copy">Complete the previous human checkpoint to unlock this stage.</p>}
    </article>
  );
}

function ProposalReview({ proposal, caseId, onDone }: { proposal: Proposal; caseId: string; onDone: () => Promise<void> }) {
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const retailers = asArray(proposal.payload.retailers);

  async function decide(decision: "approved" | "rejected") {
    setBusy(true);
    setError("");
    try {
      await api.approve(caseId, proposal.id, decision, notes);
      await onDone();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Decision failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel approval-panel">
      <div className="section-heading"><div><span className="eyebrow">Human checkpoint</span><h2>{label(proposal.type)}</h2></div><Pill value={proposal.status} /></div>
      <p className="muted">Review the exact action and evidence before anything is sent or assigned.</p>
      {retailers.length > 0 && (
        <div className="recipient-grid">
          {retailers.map((retailer) => (
            <div className="recipient" key={String(retailer.retailer_id)}>
              <strong>{String(retailer.retailer_name)}</strong>
              <span>{Number(retailer.quantity).toLocaleString()} units</span>
            </div>
          ))}
        </div>
      )}
      {proposal.type === "manufacturer_escalation_packet" && (
        <details><summary>Preview manufacturer packet</summary><pre>{JSON.stringify(proposal.payload.manufacturer_packet, null, 2)}</pre></details>
      )}
      <label>Reviewer notes<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Record the reason for your decision" /></label>
      {error && <div className="alert danger">{error}</div>}
      <div className="action-row">
        <button className="button button-primary" disabled={busy} onClick={() => void decide("approved")}>Approve action</button>
        <button className="button button-danger" disabled={busy} onClick={() => void decide("rejected")}>Reject</button>
      </div>
    </section>
  );
}

function RetailerActions({ detail, inspections, onDone }: { detail: CaseDetail; inspections: Inspection[]; onDone: () => Promise<void> }) {
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const inspection = inspections.find((item) => item.case_id === detail.case.id);

  async function review(decision: string) {
    setBusy(true);
    try { await api.reviewCase(detail.case.id, decision, notes || "Reviewed by retailer safety manager."); await onDone(); } finally { setBusy(false); }
  }
  async function finding(value: string) {
    if (!inspection) return;
    setBusy(true);
    try { await api.submitFinding(inspection.id, value, notes || "Stock inspected by retailer safety manager."); await onDone(); } finally { setBusy(false); }
  }

  if (inspection && inspection.status !== "completed") {
    return (
      <section className="panel approval-panel">
        <span className="eyebrow">Assigned inspection</span><h2>Record the human finding</h2>
        <label>Inspection notes<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
        <div className="action-row">
          <button className="button button-danger" disabled={busy} onClick={() => void finding("issue_observed")}>Issue observed</button>
          <button className="button button-secondary" disabled={busy} onClick={() => void finding("no_issue_observed")}>No issue observed</button>
          <button className="button button-ghost" disabled={busy} onClick={() => void finding("unable_to_assess")}>Unable to assess</button>
        </div>
      </section>
    );
  }
  if (detail.case.status === "new_report") {
    return (
      <section className="panel approval-panel">
        <span className="eyebrow">Retailer checkpoint</span><h2>Review customer complaint</h2>
        <label>Review notes<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
        <div className="action-row">
          <button className="button button-primary" disabled={busy} onClick={() => void review("forwarded")}>Forward to importer</button>
          <button className="button button-secondary" disabled={busy} onClick={() => void review("needs_customer_information")}>Request information</button>
        </div>
      </section>
    );
  }
  return null;
}

function ImportPanel() {
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);
  async function upload(kind: "batches" | "shipments", file?: File) {
    if (!file) return;
    setBusy(true);
    try {
      const response = await api.importCsv(kind, file);
      setResult(`${label(kind)}: ${response.inserted} inserted, ${response.skipped} skipped, ${response.errors.length} errors.`);
    } catch (reason) {
      setResult(reason instanceof Error ? reason.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel compact-panel">
      <div><span className="eyebrow">Importer records</span><h2>Update traceability data</h2></div>
      <div className="import-grid">
        <label className="file-button">Batch CSV<input type="file" accept=".csv,text/csv" disabled={busy} onChange={(event) => void upload("batches", event.target.files?.[0])} /></label>
        <label className="file-button">Shipment CSV<input type="file" accept=".csv,text/csv" disabled={busy} onChange={(event) => void upload("shipments", event.target.files?.[0])} /></label>
      </div>
      {result && <p className="muted small">{result}</p>}
    </section>
  );
}

function CaseWorkspace({ user, summary }: { user: User; summary: CaseSummary }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    const next = await api.caseDetail(summary.id);
    setDetail(next);
    if (user.role === "retailer_safety_manager") setInspections(await api.inspections());
  }, [summary.id, user.role]);

  useEffect(() => { void refresh().catch((reason) => setError(String(reason))); }, [refresh]);

  const latestRuns = useMemo(() => {
    const result: Partial<Record<AgentRun["agent_type"], AgentRun>> = {};
    for (const run of detail?.agent_runs ?? []) result[run.agent_type] = run;
    return result;
  }, [detail]);

  async function start(agent: AgentRun["agent_type"]) {
    setBusy(agent); setError("");
    try {
      const started = await api.startAgent(summary.id, agent);
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 350));
        const next = await api.caseDetail(summary.id);
        setDetail(next);
        const run = next.agent_runs.find((item) => item.id === started.run_id);
        if (run && ["awaiting_human", "completed", "failed"].includes(run.status)) break;
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Agent failed"); }
    finally { setBusy(""); }
  }

  if (!detail) return <div className="empty-state">Loading case evidence…</div>;
  const pending = detail.proposals.find((proposal) => proposal.status === "pending");
  const traceabilityApproved = detail.proposals.some(
    (proposal) =>
      ["triage_recommendation", "retailer_inspections"].includes(proposal.type) &&
      proposal.status === "approved",
  );
  const hasCompletedFinding = detail.inspections.some((item) => item.status === "completed");

  return (
    <div className="workspace">
      <header className="case-header">
        <div><span className="eyebrow">Case {detail.case.public_id}</span><h1>{detail.case.product_name}</h1><p>{detail.description}</p></div>
        <div className="case-badges"><Pill value={detail.case.status} /><Pill value={detail.case.safety_verdict} /></div>
      </header>
      {error && <div className="alert danger">{error}</div>}
      {user.role === "importer_investigator" && <ImportPanel />}
      <section>
        <div className="section-heading"><div><span className="eyebrow">Agent workflow</span><h2>Evidence before action</h2></div><button className="button button-ghost" onClick={() => void refresh()}>Refresh</button></div>
        <div className="agent-grid">
          <AgentCard agent="triage" run={latestRuns.triage} />
          <AgentCard agent="traceability" run={latestRuns.traceability} />
          <AgentCard agent="escalation" run={latestRuns.escalation} />
        </div>
        {user.role === "importer_investigator" && (
          <div className="action-row top-gap">
            <button className="button button-secondary" disabled={Boolean(busy) || !traceabilityApproved} title={!traceabilityApproved ? "Requires retailer triage approval" : undefined} onClick={() => void start("traceability")}>{busy === "traceability" ? "Tracing…" : "Run Traceability Agent"}</button>
            <button className="button button-primary" disabled={Boolean(busy) || !traceabilityApproved || !hasCompletedFinding} title={!hasCompletedFinding ? "Requires a completed retailer finding" : undefined} onClick={() => void start("escalation")}>{busy === "escalation" ? "Preparing…" : "Run Escalation Agent"}</button>
          </div>
        )}
      </section>
      {pending && user.role === "importer_investigator" && <ProposalReview proposal={pending} caseId={detail.case.id} onDone={refresh} />}
      {user.role === "retailer_safety_manager" && <RetailerActions detail={detail} inspections={inspections} onDone={refresh} />}
      <section className="panel">
        <div className="section-heading"><div><span className="eyebrow">Audit trail</span><h2>Case timeline</h2></div><span className="muted">{detail.timeline.length} events</span></div>
        <div className="timeline">
          {detail.timeline.map((event) => <div className="timeline-item" key={event.id}><span className="timeline-dot" /><div><strong>{label(event.event_type)}</strong><small>{formatDate(event.created_at)}</small></div></div>)}
        </div>
      </section>
    </div>
  );
}

function ManufacturerInbox() {
  const [items, setItems] = useState<Escalation[]>([]);
  const [selected, setSelected] = useState<Escalation | null>(null);
  const [response, setResponse] = useState("");
  const refresh = useCallback(async () => { const next = await api.escalations(); setItems(next); setSelected((current) => next.find((item) => item.id === current?.id) ?? next[0] ?? null); }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  async function submit() { if (!selected || !response.trim()) return; await api.respond(selected.id, response); setResponse(""); await refresh(); }
  return (
    <div className="manufacturer-grid">
      <aside className="case-list"><div className="list-heading"><span className="eyebrow">Manufacturer</span><h2>Escalations</h2></div>{items.map((item) => <button className={`case-row ${selected?.id === item.id ? "selected" : ""}`} key={item.id} onClick={() => setSelected(item)}><strong>{String(item.packet.case_public_id)}</strong><span>{String((item.packet.product as Record<string, unknown>)?.name ?? "Product")}</span><Pill value={item.status} /></button>)}</aside>
      <main className="workspace">{selected ? <><header className="case-header"><div><span className="eyebrow">Evidence packet</span><h1>{String(selected.packet.case_public_id)}</h1><p>Review the verified trace and retailer findings before responding.</p></div><Pill value={selected.status} /></header><section className="panel"><details open><summary>Approved manufacturer packet</summary><pre>{JSON.stringify(selected.packet, null, 2)}</pre></details></section>{selected.status !== "responded" && <section className="panel approval-panel"><h2>Manufacturer response</h2><label>Investigation result<textarea rows={5} value={response} onChange={(event) => setResponse(event.target.value)} /></label><button className="button button-primary" onClick={() => void submit()}>Submit human response</button></section>}</> : <div className="empty-state">No manufacturer escalations yet.</div>}</main>
    </div>
  );
}

function StaffApp({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selected, setSelected] = useState<CaseSummary | null>(null);
  useEffect(() => {
    if (user.role === "manufacturer_reviewer") return;
    void api.cases().then((items) => { setCases(items); setSelected(items[0] ?? null); });
  }, [user.role]);
  return (
    <div className="app-shell">
      <header className="app-bar"><div className="brand"><span className="brand-mark">BB</span><span>BatchBridge</span></div><div className="user-block"><div><strong>{user.display_name}</strong><span>{label(user.role)}</span></div><button className="button button-ghost" onClick={onLogout}>Sign out</button></div></header>
      {user.role === "manufacturer_reviewer" ? <ManufacturerInbox /> : (
        <div className="dashboard-grid">
          <aside className="case-list"><div className="list-heading"><span className="eyebrow">Operational queue</span><h2>Cases</h2><span>{cases.length} active records</span></div>{cases.map((item) => <button className={`case-row ${selected?.id === item.id ? "selected" : ""}`} key={item.id} onClick={() => setSelected(item)}><div><strong>{item.public_id}</strong><span>{item.product_name}</span></div><Pill value={item.status} /><small>Lot {item.batch_number ?? "unknown"}</small></button>)}</aside>
          <main>{selected ? <CaseWorkspace user={user} summary={selected} /> : <div className="empty-state">No cases are available for this organization.</div>}</main>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [screen, setScreen] = useState<"public" | "login">("public");
  const [loading, setLoading] = useState(true);
  useEffect(() => { void api.me().then(setUser).catch(() => undefined).finally(() => setLoading(false)); }, []);
  async function logout() { await api.logout(); setUser(null); setScreen("public"); }
  if (loading) return <div className="loading-screen"><span className="brand-mark large">BB</span><p>Loading trusted records…</p></div>;
  if (user) return <StaffApp user={user} onLogout={() => void logout()} />;
  if (screen === "login") return <Login onSuccess={setUser} onBack={() => setScreen("public")} />;
  return <PublicReport onLogin={() => setScreen("login")} />;
}
