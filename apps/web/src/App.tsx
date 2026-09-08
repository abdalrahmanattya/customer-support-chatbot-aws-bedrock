import { FormEvent, useEffect, useRef, useState } from "react";
import { ArrowRight, Check, ChevronRight, CircleUserRound, ExternalLink, Headphones, Inbox, LifeBuoy, LoaderCircle, LockKeyhole, LogOut, MessageCircle, Plus, RotateCcw, Search, Send, ShieldCheck, Sparkles, TicketCheck, X } from "lucide-react";
import { api, isDemo } from "./api";
import { completeSignIn, operatorToken, signIn, signOut } from "./auth";
import type { Message, Session, Ticket, TicketDraft, TicketStatus } from "./types";

const suggestions = ["What is your return policy?", "How can I track my delivery?", "The checkout page is broken"];
const greeting: Message = { id: "hello", role: "assistant", text: "Hi, I’m Nova. I can answer questions about orders, shipping and returns, or help you prepare a support ticket." };

function Brand() { return <a className="brand" href="/" aria-label="Northstar Support home"><span className="brand-mark"><Sparkles size={20}/></span><span>Northstar <b>Support</b></span></a>; }
function DemoBadge() { return isDemo ? <span className="demo-badge"><span/> Demo mode</span> : <span className="live-badge"><span/> AWS connected</span>; }

function CustomerApp() {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([greeting]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showTicket, setShowTicket] = useState(false);
  const [ticketId, setTicketId] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.createSession().then(setSession).catch((e) => setError(e.message)); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  async function send(text: string) {
    const clean = text.trim(); if (!clean || !session || busy) return;
    setMessages((items) => [...items, { id: crypto.randomUUID(), role: "customer", text: clean }]);
    setInput(""); setBusy(true); setError("");
    try {
      const job = await api.sendMessage(session, clean);
      if (job.status === "FAILED") throw new Error(job.error || "The assistant is unavailable.");
      setMessages((items) => [...items, { id: job.request_id, role: "assistant", text: job.response || "", citations: job.citations }]);
    } catch (e) { setError(e instanceof Error ? e.message : "Something went wrong."); }
    finally { setBusy(false); }
  }

  function reset() { setMessages([greeting]); setTicketId(""); api.createSession().then(setSession).catch((e) => setError(e.message)); }

  return <div className="page-shell">
    <header className="topbar"><Brand/><nav><a href="#how-it-works">How it works</a><a href="/operator">Operator desk</a><DemoBadge/></nav></header>
    <main className="customer-layout">
      <section className="intro-panel">
        <span className="eyebrow"><ShieldCheck size={15}/> Grounded support</span>
        <h1>Answers you can<br/><em>act on.</em></h1>
        <p>Clear help from verified store policies, with a human-ready ticket when you need more.</p>
        <div className="trust-list"><span><Check/> Policy citations</span><span><Check/> Review before submit</span><span><Check/> No real customer data</span></div>
        <div className="intro-note"><LifeBuoy/><div><strong>Need an operator?</strong><p>Create a ticket from this conversation. This demo does not represent staffed live support.</p></div></div>
      </section>
      <section className="chat-card" aria-label="Support chat">
        <div className="chat-header"><div className="agent-avatar">N</div><div><strong>Nova</strong><span><i/> Support assistant</span></div><button className="icon-button" onClick={reset} aria-label="Reset conversation"><RotateCcw size={18}/></button></div>
        <div className="messages" aria-live="polite">
          {messages.map((message) => <div key={message.id} className={`message-row ${message.role}`}><div className="message-bubble">{message.text}{message.citations?.length ? <div className="citations"><span>Sources</span>{message.citations.map((citation) => <button key={citation.id}><ShieldCheck size={13}/>{citation.title}<ExternalLink size={12}/></button>)}</div> : null}</div></div>)}
          {busy && <div className="message-row assistant"><div className="message-bubble typing"><i/><i/><i/><span>Checking store policies</span></div></div>}
          {error && <div className="inline-error" role="alert">{error}<button onClick={() => setError("")}>Dismiss</button></div>}
          <div ref={endRef}/>
        </div>
        {messages.length === 1 && <div className="suggestions">{suggestions.map((item) => <button key={item} onClick={() => send(item)}>{item}<ChevronRight size={14}/></button>)}</div>}
        {ticketId && <div className="ticket-success"><TicketCheck/><div><strong>Ticket submitted</strong><span>{ticketId} · Open</span></div></div>}
        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}><label htmlFor="message">Ask a support question</label><div><textarea id="message" rows={1} maxLength={2000} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }} placeholder="Ask about returns, shipping, or an issue…"/><button disabled={!input.trim() || busy || !session} aria-label="Send message"><Send size={18}/></button></div><footer><button type="button" className="ticket-link" onClick={() => setShowTicket(true)}><Plus size={15}/> Create a ticket</button><span>{input.length}/2000</span></footer></form>
      </section>
    </main>
    <section id="how-it-works" className="steps-strip"><span>01 <b>Ask</b><small>Describe what you need</small></span><ArrowRight/><span>02 <b>Verify</b><small>See the policy source</small></span><ArrowRight/><span>03 <b>Escalate</b><small>Review and submit a ticket</small></span></section>
    {showTicket && session && (
      <TicketModal
        session={session}
        onClose={() => setShowTicket(false)}
        onCreated={(id) => { setTicketId(id); setShowTicket(false); }}
      />
    )}
  </div>;
}

function TicketModal({ session, onClose, onCreated }: { session: Session; onClose: () => void; onCreated: (id: string) => void }) {
  const [values, setValues] = useState({ description: "", steps_to_reproduce: "", environment: "" });
  const [draft, setDraft] = useState<TicketDraft | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const field = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValues({ ...values, [key]: e.target.value });
  async function review(e: FormEvent) { e.preventDefault(); setBusy(true); setError(""); try { setDraft(await api.createDraft(session, values)); } catch (err) { setError(err instanceof Error ? err.message : "Could not prepare draft"); } finally { setBusy(false); } }
  async function confirm() { if (!draft) return; setBusy(true); try { const ticket = await api.confirmDraft(session, draft); onCreated(ticket.ticket_id); } catch (err) { setError(err instanceof Error ? err.message : "Could not submit ticket"); setBusy(false); } }
  return <div className="modal-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="ticket-title"><header><div><span className="eyebrow">Support escalation</span><h2 id="ticket-title">{draft ? "Review your ticket" : "Create a support ticket"}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close"><X/></button></header>{!draft ? <form onSubmit={review}><label>What happened?<textarea required value={values.description} onChange={field("description")} placeholder="Describe the problem and what you expected…"/></label><label>Steps to reproduce<textarea required value={values.steps_to_reproduce} onChange={field("steps_to_reproduce")} placeholder="1. Open checkout&#10;2. Select Pay…"/></label><label>Device and browser<input required value={values.environment} onChange={field("environment")} placeholder="Chrome 128 on macOS"/></label>{error && <p className="form-error">{error}</p>}<button className="primary-button" disabled={busy}>{busy ? <LoaderCircle className="spin"/> : null} Review ticket <ArrowRight/></button></form> : <div className="review-card"><Review label="Issue" value={draft.description}/><Review label="Steps" value={draft.steps_to_reproduce}/><Review label="Environment" value={draft.environment}/><div className="review-notice"><ShieldCheck/>Nothing is submitted until you confirm.</div>{error && <p className="form-error">{error}</p>}<div className="modal-actions"><button className="secondary-button" onClick={() => setDraft(null)}>Edit</button><button className="primary-button" onClick={confirm} disabled={busy}>{busy ? <LoaderCircle className="spin"/> : <TicketCheck/>} Confirm & submit</button></div></div>}</section></div>;
}
function Review({ label, value }: { label: string; value: string }) { return <div className="review-row"><span>{label}</span><p>{value}</p></div>; }

function OperatorApp() {
  const [token, setToken] = useState(operatorToken()); const [tickets, setTickets] = useState<Ticket[]>([]); const [filter, setFilter] = useState<TicketStatus | "ALL">("ALL"); const [selected, setSelected] = useState<Ticket | null>(null); const [error, setError] = useState("");
  const load = () => token && api.listTickets(token, filter === "ALL" ? undefined : filter).then(({ tickets }) => { setTickets(tickets); if (selected) setSelected(tickets.find((t) => t.ticket_id === selected.ticket_id) || null); }).catch((e) => setError(e.message));
  useEffect(() => { void load(); }, [token, filter]);
  async function advance(ticket: Ticket) { if (!token) return; const next = ticket.status === "OPEN" ? "IN_PROGRESS" : "RESOLVED"; try { const updated = await api.updateTicket(token, ticket.ticket_id, next); setSelected(updated); load(); } catch (e) { setError(e instanceof Error ? e.message : "Update failed"); } }
  if (!token) return <div className="login-page"><Brand/><section className="login-card"><span className="login-icon"><LockKeyhole/></span><span className="eyebrow">Restricted access</span><h1>Operator desk</h1><p>Sign in to review customer tickets and update their progress.</p><button className="primary-button" onClick={() => signIn().then(() => setToken(operatorToken())).catch((e) => setError(e.message))}><CircleUserRound/> Sign in with Cognito</button>{error && <p className="form-error">{error}</p>}<a href="/">Return to customer support</a></section></div>;
  return <div className="operator-shell"><aside><Brand/><nav><a className="active"><Inbox/> Tickets</a><a href="/"><MessageCircle/> Customer chat</a></nav><div className="operator-user"><span>OA</span><div><strong>Operator</strong><small>{isDemo ? "Local demonstration" : "Verified account"}</small></div><button onClick={signOut} aria-label="Sign out"><LogOut/></button></div></aside><main><header><div><span className="eyebrow">Support operations</span><h1>Ticket queue</h1><p>Review customer issues and keep their status current.</p></div><DemoBadge/></header><div className="queue-toolbar"><div className="filter-tabs">{(["ALL", "OPEN", "IN_PROGRESS", "RESOLVED"] as const).map((value) => <button className={filter === value ? "active" : ""} onClick={() => setFilter(value)} key={value}>{value === "ALL" ? "All tickets" : value.replace("_", " ")}</button>)}</div><label className="search"><Search/><input placeholder="Search tickets" onChange={(e) => { const query=e.target.value.toLowerCase(); if (!query) load(); else setTickets((items) => items.filter((t) => `${t.ticket_id} ${t.description}`.toLowerCase().includes(query))); }}/></label></div>{error && <div className="inline-error">{error}</div>}<section className="ticket-table"><div className="table-head"><span>Ticket</span><span>Issue</span><span>Status</span><span>Created</span><span/></div>{tickets.length ? tickets.map((ticket) => <button className="ticket-row" key={ticket.ticket_id} onClick={() => setSelected(ticket)}><strong>{ticket.ticket_id}</strong><span>{ticket.description}</span><Status value={ticket.status}/><time>{new Date(ticket.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</time><ChevronRight/></button>) : <div className="empty-state"><span><Inbox/></span><h2>No tickets here</h2><p>New customer tickets will appear in this queue.</p></div>}</section></main>{selected && <div className="drawer-backdrop" onMouseDown={(e) => e.target === e.currentTarget && setSelected(null)}><aside className="ticket-drawer"><header><div><small>Ticket</small><h2>{selected.ticket_id}</h2></div><button className="icon-button" onClick={() => setSelected(null)}><X/></button></header><Status value={selected.status}/><Review label="Issue" value={selected.description}/><Review label="Steps to reproduce" value={selected.steps_to_reproduce}/><Review label="Environment" value={selected.environment}/><div className="timeline"><span className="done"><Check/></span><div><strong>Ticket received</strong><small>{new Date(selected.created_at).toLocaleString()}</small></div></div>{selected.status !== "RESOLVED" && <button className="primary-button" onClick={() => advance(selected)}>{selected.status === "OPEN" ? "Start progress" : "Mark resolved"}<ArrowRight/></button>}</aside></div>}</div>;
}
function Status({ value }: { value: TicketStatus }) { return <span className={`status status-${value.toLowerCase()}`}>{value.replace("_", " ")}</span>; }
function Callback() { const [error, setError] = useState(""); useEffect(() => { completeSignIn().catch((e) => setError(e.message)); }, []); return <div className="login-page"><section className="login-card"><LoaderCircle className="spin"/><h1>Completing sign-in</h1>{error && <p className="form-error">{error}</p>}</section></div>; }
export function App() { if (location.pathname === "/operator") return <OperatorApp/>; if (location.pathname === "/auth/callback") return <Callback/>; return <CustomerApp/>; }
