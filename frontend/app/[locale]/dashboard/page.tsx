import { redirect } from 'next/navigation';

// The OAuth `redirect_uri` registered for BSGateway is `${origin}/dashboard`
// (see `src/hooks/useAuth.ts`), but the dashboard canonically lives at the
// `[locale]` root (`/` — `app/[locale]/page.tsx`). Redirect `/dashboard` → `/`
// so the post-login landing reaches the app shell, which consumes the
// `#access_token` fragment. The browser preserves the URL fragment across
// this redirect (the `Location` carries no fragment of its own).
//
// Without this route the dynamic build's global 404 handles `/dashboard`,
// never mounts `<AppShell>`, and the token is dropped — login dead-ends.
export default function Page() {
  redirect('/');
}
