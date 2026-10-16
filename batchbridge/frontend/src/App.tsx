import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { api } from "./api";
import { createDemoPhoto } from "./demoPhoto";
import type {
  AgentRun,
  CaseDetail,
  CaseSummary,
  DemoBarcodeMatch,
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
    retailer_code: "",
    purchase_date: "",
    description: "",
  });
  const [created, setCreated] = useState<Awaited<ReturnType<typeof api.report>> | null>(null);
  const [trackingToken, setTrackingToken] = useState("");
  const [tracked, setTracked] = useState<Awaited<ReturnType<typeof api.track>> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retailers, setRetailers] = useState<{ code: string; name: string }[]>([]);
  const [photos, setPhotos] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);

  useEffect(() => {
    void api.retailers().then(setRetailers).catch(() => setError("Unable to load supermarkets. Please refresh."));
  }, []);
  useEffect(() => {
    const urls = photos.map((file) => URL.createObjectURL(file));
    setPreviews(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [photos]);

  function selectPhotos(files: File[]) {
    setError("");
    if (files.length > 3 || files.some((file) => !["image/jpeg", "image/png"].includes(file.type) || file.size > 5 * 1024 * 1024)) {
      setError("Choose up to three JPEG or PNG photos, each no larger than 5 MB.");
      return;
    }
    setPhotos(files);
  }

  async function useDemoPhoto() {
    setBusy(true); setError("");
    try {
      setPhotos([await createDemoPhoto()]);
      setForm((current) => ({ ...current, retailer_code: "RETAILER-A", description: current.description || "The sealed chocolate had an unusual smell and visible discoloration." }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to create demo photo"); }
    finally { setBusy(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (!photos.length) throw new Error("Add a product photo or use the demo photo below.");
      const payload = new FormData();
      for (const [key, value] of Object.entries(form)) if (value) payload.append(key, value);
      for (const photo of photos) payload.append("files", photo);
      const result = await api.photoReport(payload);
      setCreated(result);
      setTrackingToken(result.tracking_token);
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
          <h1>Something wrong with your food? Start here.</h1>
          <p>
            Share a photo and tell us what happened. Your supermarket’s food safety officer will
            check the product details and forward the verified complaint for investigation.
          </p>
          <div className="trust-row">
            <span>01 · Share a photo</span><span>02 · Officer verifies</span><span>03 · We investigate</span>
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
            <p className="muted">No product codes needed. Your supermarket officer will verify the product and batch.</p>
          </div>
          <div className="form-grid two">
            <label>Name<input value={form.reporter_name} onChange={(event) => setForm({ ...form, reporter_name: event.target.value })} /></label>
            <label>Email<input type="email" value={form.reporter_email} onChange={(event) => setForm({ ...form, reporter_email: event.target.value })} /></label>
          </div>
          <label>Where did you buy it?<select required disabled={busy || Boolean(created)} value={form.retailer_code} onChange={(event) => setForm({ ...form, retailer_code: event.target.value })}>
            <option value="">Choose your supermarket</option>
            {retailers.map((retailer) => <option key={retailer.code} value={retailer.code}>{retailer.name}</option>)}
          </select></label>
          <div className="photo-upload">
            <span className="eyebrow">Product photos</span>
            <strong>Show us the packaging and the problem</strong>
            <p className="muted small" id="photo-help">Include a clear photo of the barcode or printed code. Up to 3 JPEG/PNG photos, 5 MB each.</p>
            <input aria-label="Product photos" aria-describedby="photo-help" type="file" accept="image/jpeg,image/png" multiple disabled={busy || Boolean(created)} onChange={(event) => selectPhotos(Array.from(event.target.files ?? []))} />
            <div className="photo-preview-grid">{photos.map((photo, index) => <figure key={`${photo.name}-${index}`}><img src={previews[index]} alt={`Selected product photo ${index + 1}`} /><figcaption>{photo.name}</figcaption></figure>)}</div>
            <button type="button" className="button button-secondary" disabled={busy || Boolean(created)} onClick={() => void useDemoPhoto()}>Try with a demo photo</button>
            <span className="muted small">Fictional chocolate packaging for trying the full workflow.</span>
          </div>
          <label>Purchase date<input type="date" value={form.purchase_date} onChange={(event) => setForm({ ...form, purchase_date: event.target.value })} /></label>
          <label>What did you observe?<textarea required minLength={10} rows={4} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          {error && <div className="alert danger">{error}</div>}
          {created && (
            <div className="alert success">
              <strong>Report {created.case_id} created.</strong>
              <span>Your supermarket officer will review the photos and verify the product.</span>
              <span>Save this private tracking token: <code>{created.tracking_token}</code></span>
              <button type="button" className="button button-secondary" onClick={() => { setCreated(null); setPhotos([]); setForm((current) => ({ ...current, description: "" })); }}>Report another issue</button>
            </div>
          )}
          <button className="button button-primary" disabled={busy || Boolean(created)}>{busy ? "Preparing report…" : created ? "Report received" : "Send to supermarket officer"}</button>
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
  const assessment = result?.ai_assessment as { summary?: string; unanswered_questions?: string[] } | undefined;
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
          {result && <span className="pill pill-neutral">{result.execution_mode === "llm" ? `Groq · ${String(result.model)} · ${String(result.llm_turns)} model turns` : "Previous demo rules run"}</span>}
          {assessment?.summary && <p className="muted small">{assessment.summary}</p>}
          {assessment?.unanswered_questions && assessment.unanswered_questions.length > 0 && <div className="small"><strong>Follow-up questions</strong><ul>{assessment.unanswered_questions.map((question, index) => <li key={index}>{question}</li>)}</ul></div>}
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
      <p className="muted">Review proposal version {proposal.version} before anything is sent or assigned.</p>
      {proposal.review_block_reason && <div className="alert">{proposal.review_block_reason}</div>}
      {proposal.payload.recommendation != null && <p><strong>Recommendation:</strong> {label(String(proposal.payload.recommendation))}</p>}
      {asArray(proposal.payload.rationale).map((reason, index) => <p key={index}>{String(reason)}</p>)}
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
        <button className="button button-primary" disabled={busy || Boolean(proposal.review_block_reason)} onClick={() => void decide("approved")}>Approve action</button>
        <button className="button button-danger" disabled={busy || Boolean(proposal.review_block_reason)} onClick={() => void decide("rejected")}>Reject</button>
      </div>
    </section>
  );
}

function CaseInformation({ detail, onDone }: { detail: CaseDetail; onDone: () => Promise<void> }) {
  const [notes, setNotes] = useState("");
  const [product, setProduct] = useState("");
  const [batch, setBatch] = useState("");
  const [verdict, setVerdict] = useState("unconfirmed");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save(close: boolean) {
    setBusy(true); setError("");
    try {
      if (close) await api.closeCase(detail.case.id, notes, verdict);
      else await api.addInformation(detail.case.id, notes, product, batch);
      setNotes(""); await onDone();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to save"); }
    finally { setBusy(false); }
  }
  return <section className="panel"><details><summary>Add investigation information or close the case</summary>
    <p className="muted">Saving information requires a new triage run and approval. Identity corrections are allowed before supermarket checks are assigned.</p>
    <label>Additional facts / decision notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
    {detail.inspections.length === 0 && <><label>Corrected product (optional)<input value={product} onChange={(event) => setProduct(event.target.value)} /></label><label>Corrected lot (optional)<input value={batch} onChange={(event) => setBatch(event.target.value)} /></label></>}
    <button className="button button-secondary" disabled={busy || notes.trim().length < 3} onClick={() => void save(false)}>Save information</button>
    {detail.manufacturer_response && <><label>Final human verdict<select value={verdict} onChange={(event) => setVerdict(event.target.value)}>{["unconfirmed", "suspected", "confirmed", "not_supported"].map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label><button className="button button-primary" disabled={busy || notes.trim().length < 3} onClick={() => void save(true)}>Record verdict and close</button></>}
    {error && <div className="alert danger">{error}</div>}
  </details></section>;
}

function RetailerActions({ detail, inspections, onDone }: { detail: CaseDetail; inspections: Inspection[]; onDone: () => Promise<void> }) {
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [barcode, setBarcode] = useState("");
  const [match, setMatch] = useState<DemoBarcodeMatch | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const inspection = inspections.find((item) => item.case_id === detail.case.id);
  const needsVerification = detail.case.source === "customer_photo";

  async function lookup() {
    setBusy(true); setError(""); setMatch(null); setConfirmed(false);
    try { setMatch(await api.lookupBarcode(detail.case.id, barcode)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Barcode lookup failed"); }
    finally { setBusy(false); }
  }

  async function review(decision: string) {
    setBusy(true); setError("");
    try {
      await api.reviewCase(detail.case.id, decision, notes || "Packaging reviewed by supermarket officer.", match?.barcode);
      await onDone();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to forward case"); }
    finally { setBusy(false); }
  }
  async function finding(value: string) {
    if (!inspection) return;
    setBusy(true); setError("");
    try { await api.submitFinding(inspection.id, value, notes || "Stock inspected by retailer safety manager."); await onDone(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to record finding"); }
    finally { setBusy(false); }
  }

  if (inspection && inspection.status !== "completed") {
    return (
      <section className="panel approval-panel">
        <span className="eyebrow">Assigned inspection</span><h2>Record the human finding</h2>
        <label>Inspection notes<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
        {error && <div className="alert danger" role="alert">{error}</div>}
        <div className="action-row">
          <button className="button button-danger" disabled={busy} onClick={() => void finding("issue_observed")}>Issue observed</button>
          <button className="button button-secondary" disabled={busy} onClick={() => void finding("no_issue_observed")}>No issue observed</button>
          <button className="button button-ghost" disabled={busy} onClick={() => void finding("unable_to_assess")}>Unable to assess</button>
        </div>
      </section>
    );
  }
  if (!inspection && detail.retailer_review?.decision !== "forwarded") {
    return (
      <section className="panel approval-panel">
        <span className="eyebrow">Supermarket food safety officer</span><h2>Verify, then forward</h2>
        {needsVerification && <div className="verification-box">
          <div className="section-heading"><strong>Identify the product from the photo</strong><span className="pill pill-warning">Simulated barcode lookup</span></div>
          <p className="muted small">Review the uploaded packaging, then enter its demo code. This demo uses a fixed product and batch mapping; it does not decode images.</p>
          <label>Demo barcode<input value={barcode} placeholder="e.g. DEMO-CHOC-38" onChange={(event) => { setBarcode(event.target.value); setMatch(null); setConfirmed(false); }} /></label>
          <div className="action-row">
            <button className="button button-secondary" disabled={busy || !barcode.trim()} onClick={() => void lookup()}>{busy ? "Checking…" : "Look up demo barcode"}</button>
            <button className="button button-ghost" disabled={busy} onClick={() => { setBarcode("DEMO-CHOC-38"); setMatch(null); setConfirmed(false); }}>Use demo code</button>
          </div>
          {match && <div className="verified-match" role="status">
            <span className="eyebrow">Match from demo records</span><h3>{match.product_name}</h3>
            <div className="metric-row"><span><small>Product</small><strong>{match.sku}</strong></span><span><small>Manufacturer lot</small><strong>{match.batch_number}</strong></span></div>
            <label className="confirmation"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />I reviewed the photos and confirm this demo product and batch match.</label>
          </div>}
        </div>}
        <label>Review notes<textarea rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
        {error && <div className="alert danger" role="alert">{error}</div>}
        <div className="action-row">
          <button className="button button-primary" disabled={busy || (needsVerification && (!match || !confirmed))} onClick={() => void review("forwarded")}>Verify & forward to importer</button>
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

  useEffect(() => {
    if (!detail?.agent_runs.some((run) => ["queued", "running"].includes(run.status))) return;
    const timer = window.setTimeout(() => { void refresh().catch((reason) => setError(String(reason))); }, 1000);
    return () => window.clearTimeout(timer);
  }, [detail, refresh]);

  const latestRuns = useMemo(() => {
    const result: Partial<Record<AgentRun["agent_type"], AgentRun>> = {};
    for (const run of detail?.agent_runs ?? []) result[run.agent_type] = run;
    return result;
  }, [detail]);

  async function start(agent: AgentRun["agent_type"]) {
    setBusy(agent); setError("");
    try {
      await api.startAgent(summary.id, agent);
      await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Agent failed"); }
    finally { setBusy(""); }
  }

  if (!detail) return <div className="empty-state">Loading case evidence…</div>;
  const pending = detail.proposals.filter((proposal) => proposal.status === "pending" && Object.values(detail.workflow).some((step) => step.latest_proposal_id === proposal.id));
  const agentRunning = Boolean(busy) || detail.agent_runs.some((run) => ["queued", "running"].includes(run.status));

  return (
    <div className="workspace">
      <header className="case-header">
        <div><span className="eyebrow">Case {detail.case.public_id}</span><h1>{detail.case.product_name}</h1><p>{detail.description}</p></div>
        <div className="case-badges"><Pill value={detail.case.status} /><Pill value={detail.case.safety_verdict} /></div>
      </header>
      {error && <div className="alert danger">{error}</div>}
      {user.role === "importer_investigator" && <ImportPanel />}
      {detail.demo_verification && <section className="panel verified-match">
        <span className="eyebrow">Human-verified product identity</span><h2>{detail.demo_verification.product_name}</h2>
        <p>Product {detail.demo_verification.sku} · Lot {detail.demo_verification.batch_number}</p>
        <span className="muted small">Confirmed by the supermarket officer using simulated code {detail.demo_verification.barcode}. See the timeline for the review record.</span>
      </section>}
      {detail.evidence.length > 0 && <section className="panel">
        <div className="section-heading"><div><span className="eyebrow">Customer evidence</span><h2>Packaging & reported issue</h2></div><span className="muted small">{detail.evidence.length} attachment(s)</span></div>
        <div className="evidence-grid">{detail.evidence.map((item) => <a key={item.id} href={item.url} target="_blank" rel="noreferrer" className="evidence-card">
          {item.content_type.startsWith("image/") ? <img src={item.url} alt={`Submitted evidence: ${item.filename}`} /> : <span>PDF evidence</span>}
          <span>{item.filename} ↗</span>
        </a>)}</div>
      </section>}
      {detail.case.source === "customer_photo" && detail.retailer_review?.decision !== "forwarded" && user.role === "importer_investigator" && <div className="alert" role="status">Awaiting supermarket officer verification. Product identification and tracing become available after the officer forwards the case.</div>}
      {user.role === "retailer_safety_manager" && <RetailerActions key={detail.case.id} detail={detail} inspections={inspections} onDone={refresh} />}
      <section>
        <div className="section-heading"><div><span className="eyebrow">Agent workflow</span><h2>Evidence before action</h2></div><button className="button button-ghost" onClick={() => void refresh()}>Refresh</button></div>
        <div className="agent-grid">
          <AgentCard agent="triage" run={latestRuns.triage} />
          <AgentCard agent="traceability" run={latestRuns.traceability} />
          <AgentCard agent="escalation" run={latestRuns.escalation} />
        </div>
        {user.role === "importer_investigator" && (
          <div className="action-row top-gap">
            <button className="button button-secondary" disabled={agentRunning || !detail.workflow.triage.can_run} title={detail.workflow.triage.blocked_reason ?? undefined} onClick={() => void start("triage")}>Run Triage Agent</button>
            <button className="button button-secondary" disabled={agentRunning || !detail.workflow.traceability.can_run} title={detail.workflow.traceability.blocked_reason ?? undefined} onClick={() => void start("traceability")}>Run Traceability Agent</button>
            <button className="button button-primary" disabled={agentRunning || !detail.workflow.escalation.can_run} title={detail.workflow.escalation.blocked_reason ?? undefined} onClick={() => void start("escalation")}>Run Escalation Agent</button>
          </div>
        )}
      </section>
      {agentRunning && <div className="alert" role="status">Agent investigation is running. This page refreshes automatically until it finishes or needs human review.</div>}
      {user.role === "importer_investigator" && <>
        {Object.entries(detail.workflow).map(([stage, step]) => step.blocked_reason && <p className="muted" key={stage}><strong>{label(stage)}:</strong> {step.blocked_reason}</p>)}
        {pending.map((proposal) => <ProposalReview key={proposal.id} proposal={proposal} caseId={detail.case.id} onDone={refresh} />)}
        {detail.case.status !== "closed" && <CaseInformation key={detail.case.id} detail={detail} onDone={refresh} />}
      </>}
      {detail.inspections.length > 0 && <section className="panel"><span className="eyebrow">Supermarket checks</span><h2>{detail.inspections.filter((item) => item.status === "completed").length} / {detail.inspections.length} responses received</h2>{detail.inspections.map((item) => <p key={item.id}><strong>{item.retailer_name}</strong> · {label(item.status)}{item.finding && ` · ${label(item.finding)}`}<br />{item.notes}</p>)}</section>}
      {detail.manufacturer_response && <section className="panel"><h2>Manufacturer response</h2><p>{detail.manufacturer_response}</p></section>}
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
