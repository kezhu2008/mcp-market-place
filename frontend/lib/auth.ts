"use client";

import { Amplify } from "aws-amplify";
import { fetchAuthSession, signInWithRedirect, signOut } from "aws-amplify/auth";

let configured = false;

export function configureAmplify() {
  if (configured) return;
  const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID;
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
  const domain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN;
  const redirectUri = process.env.NEXT_PUBLIC_COGNITO_REDIRECT_URI;

  if (!userPoolId || !clientId || !domain || !redirectUri) {
    // Allow local dev without auth configured yet.
    return;
  }

  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId: clientId,
        loginWith: {
          oauth: {
            domain,
            scopes: ["openid", "email", "profile"],
            redirectSignIn: [redirectUri],
            redirectSignOut: [redirectUri],
            responseType: "code",
          },
        },
      },
    },
  });
  configured = true;
}

export async function getIdToken(): Promise<string | null> {
  configureAmplify();
  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.toString() ?? null;
  } catch {
    return null;
  }
}

export async function login() {
  configureAmplify();
  await signInWithRedirect();
}

export async function logout() {
  configureAmplify();
  await signOut();
}
