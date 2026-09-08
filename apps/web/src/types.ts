export type TicketStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED";

export interface Citation { id: string; title: string; score?: number }
export interface Message { id: string; role: "assistant" | "customer"; text: string; citations?: Citation[] }
export interface Session { sessionId: string; sessionToken: string; expiresAt: string }
export interface ChatJob { request_id: string; status: "PENDING" | "COMPLETE" | "FAILED"; response?: string; error?: string; citations: Citation[] }
export interface TicketDraft { draft_id: string; description: string; steps_to_reproduce: string; environment: string; expires_at: string }
export interface Ticket { ticket_id: string; description: string; steps_to_reproduce: string; environment: string; status: TicketStatus; created_at: string; updated_at: string }
