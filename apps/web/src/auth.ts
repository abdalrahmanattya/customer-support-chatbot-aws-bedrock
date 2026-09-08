import { isDemo } from "./api";

const TOKEN_KEY = "northstar-operator-token";
const VERIFIER_KEY = "northstar-pkce-verifier";

function encode(value: ArrayBuffer | Uint8Array<ArrayBuffer>) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function operatorToken() { return sessionStorage.getItem(TOKEN_KEY); }

export async function signIn() {
  if (isDemo) { sessionStorage.setItem(TOKEN_KEY, "local-demo-operator"); location.assign("/operator"); return; }
  const domain = import.meta.env.VITE_COGNITO_DOMAIN;
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
  if (!domain || !clientId) throw new Error("Operator identity is not configured.");
  const verifier = encode(crypto.getRandomValues(new Uint8Array(32)));
  const challenge = encode(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  const redirect = `${location.origin}/auth/callback`;
  location.assign(`${domain}/oauth2/authorize?${new URLSearchParams({ client_id: clientId, response_type: "code", scope: "openid email", redirect_uri: redirect, code_challenge_method: "S256", code_challenge: challenge })}`);
}

export async function completeSignIn() {
  const code = new URLSearchParams(location.search).get("code");
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  const domain = import.meta.env.VITE_COGNITO_DOMAIN;
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
  if (!code || !verifier || !domain || !clientId) throw new Error("The sign-in response is incomplete.");
  const response = await fetch(`${domain}/oauth2/token`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ grant_type: "authorization_code", client_id: clientId, code, redirect_uri: `${location.origin}/auth/callback`, code_verifier: verifier }) });
  const body = await response.json();
  if (!response.ok || !body.access_token) throw new Error("Operator sign-in could not be completed.");
  sessionStorage.setItem(TOKEN_KEY, body.access_token);
  sessionStorage.removeItem(VERIFIER_KEY);
  location.replace("/operator");
}

export function signOut() { sessionStorage.removeItem(TOKEN_KEY); location.assign("/"); }
