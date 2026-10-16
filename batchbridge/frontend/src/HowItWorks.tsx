const steps = [
  { phase: "Signal", title: "Capture evidence", description: "Complaint, product photos, purchase context, and source stay connected." },
  { phase: "Verify", title: "Confirm identity", description: "Retailer officer verifies product and manufacturer lot before tracing starts." },
  { phase: "Trace", title: "Find exact recipients", description: "Read-only records identify every shipment tied to exact product and lot." },
  { phase: "Decide", title: "Approve next action", description: "Authorized humans review proposals, retailer findings, and manufacturer response." },
];

const permissions = [
  { role: "Consumer", allowed: [true, false, false, false, false] },
  { role: "Retailer safety manager", allowed: [true, true, false, false, false] },
  { role: "Importer", allowed: [false, false, true, true, false] },
  { role: "Manufacturer", allowed: [false, false, false, false, true] },
];

export function HowItWorks({ onLogin }: { onLogin: () => void }) {
  return (
    <div className="how-page" id="how-it-works">
      <section className="how-overview" aria-labelledby="how-title">
        <header className="how-intro">
          <span className="eyebrow">One accountable workflow</span>
          <h1 id="how-title">From complaint to<br />approved action.</h1>
          <p>BatchBridge turns scattered reports into a precise investigation. Every handoff is approved by a person.</p>
          <a className="text-link" href="#investigation-workflow">Explore the workflow <span aria-hidden="true">↓</span></a>
          <figure className="how-mini-graph">
            <figcaption>LangGraph workflow</figcaption>
            <ol aria-label="Start, run the selected agent, pause for human review, end">
              <li>Start</li>
              <li>Run stage</li>
              <li className="how-mini-gate">Human review</li>
              <li>End</li>
            </ol>
            <small>Triage · Traceability · Escalation</small>
          </figure>
        </header>
        <ol className="how-steps">
          {steps.map((step, index) => (
            <li key={step.phase}>
              <span className="how-step-number">0{index + 1}</span>
              <div><span className="eyebrow">{step.phase}</span><h2>{step.title}</h2><p>{step.description}</p></div>
            </li>
          ))}
        </ol>
      </section>

      <section className="how-workflow" id="investigation-workflow" aria-labelledby="workflow-title">
        <header className="how-section-header">
          <span className="eyebrow">Three agents · Two human approvals</span>
          <h2 id="workflow-title">Agents prepare the work.<br />People make every call.</h2>
          <p>The two importer approvals shown below control shop assignments and manufacturer escalation. The importer also reviews the complaint assessment before tracing.</p>
        </header>
        <ol className="how-flow" aria-label="Investigation workflow, in order">
          <li className="how-flow-stage">
            <div className="how-flow-heading"><span>01</span><h3>Review the report</h3></div>
            <div className="how-sources"><span>Consumer report</span><span>Retailer report</span></div>
            <span className="how-flow-arrow" aria-hidden="true">↓</span>
            <div className="how-agent"><span className="eyebrow">Agent work</span><strong>Triage agent</strong><small>Groq-powered</small></div>
            <p className="how-flow-note">The retailer verifies the product and lot. The importer reviews the complaint assessment before tracing.</p>
          </li>
          <li className="how-flow-stage">
            <div className="how-flow-heading"><span>02</span><h3>Check the shops</h3></div>
            <div className="how-agent"><span className="eyebrow">Agent work</span><strong>Traceability agent</strong><small>Rule-based · exact lot</small></div>
            <span className="how-flow-arrow" aria-hidden="true">↓</span>
            <div className="how-human"><span aria-hidden="true">✓</span><div><strong>Importer approves</strong><small>Shop checks are assigned only after approval.</small></div></div>
            <span className="how-flow-arrow" aria-hidden="true">↓</span>
            <div className="how-shops"><span>Shop A</span><span>Shop B</span><span>Shop C</span></div>
            <p className="how-flow-note">Retailers inspect and report. Every assigned shop must submit a finding before escalation.</p>
          </li>
          <li className="how-flow-stage">
            <div className="how-flow-heading"><span>03</span><h3>Prepare the handoff</h3></div>
            <div className="how-agent"><span className="eyebrow">Agent work</span><strong>Escalation agent</strong><small>Rule-based · every finding in</small></div>
            <span className="how-flow-arrow" aria-hidden="true">↓</span>
            <div className="how-human"><span aria-hidden="true">✓</span><div><strong>Importer approves again</strong><small>Reviews the evidence and proposed handoff.</small></div></div>
            <span className="how-flow-arrow" aria-hidden="true">↓</span>
            <div className="how-destination">Sent to manufacturer <span aria-hidden="true">↗</span></div>
          </li>
        </ol>
        <div className="how-legend" aria-label="Workflow legend"><span><i className="how-line-agent" />Agent work, reading records only</span><span><i className="how-line-human" />Human decision or inspection</span></div>
        <dl className="how-facts">
          <div><dt>0</dt><dd>automated safety verdicts</dd></div>
          <div><dt>2</dt><dd>importer approvals before escalation</dd></div>
          <div><dt>1</dt><dd>exact product and lot match to trace</dd></div>
        </dl>
      </section>

      <section className="how-permissions" aria-labelledby="permissions-title">
        <header className="how-section-header">
          <span className="eyebrow">Safety controls</span>
          <h2 id="permissions-title">Each role can only do its own part.</h2>
          <p>No tool or model creates retailer tasks before the importer approves. Manufacturer escalation needs every assigned retailer finding and a second approval.</p>
        </header>
        <div className="how-table-scroll" role="region" aria-label="Role permissions table, scroll horizontally on small screens" tabIndex={0}>
          <table className="how-role-table">
            <caption>Role permissions at a glance</caption>
            <thead><tr><th scope="col">Role</th>{["Report issue", "Add evidence", "Review trace", "Approve handoff", "Get escalation"].map(title => <th scope="col" key={title}>{title}</th>)}</tr></thead>
            <tbody>{permissions.map(({ role, allowed }) => <tr key={role}><th scope="row">{role}</th>{allowed.map((value, index) => <td key={index}><span className={value ? "how-permission-yes" : "how-permission-no"} aria-hidden="true">{value ? "●" : "—"}</span><span className="how-sr-only">{value ? "Allowed" : "Not available"}</span></td>)}</tr>)}</tbody>
          </table>
        </div>
        <p className="how-permission-key"><span className="how-permission-yes" aria-hidden="true">●</span> Available to this role <span aria-hidden="true">—</span> Not available</p>
      </section>
      <footer className="how-footer">
        <a className="brand" href="/">Batch<span className="brand-accent">Bridge</span></a>
        <nav aria-label="Footer navigation"><a href="/how-it-works" aria-current="page">How it works</a><a href="/safety-controls">Safety controls</a><button type="button" onClick={onLogin}>Staff portal ↗</button></nav>
      </footer>
    </div>
  );
}
