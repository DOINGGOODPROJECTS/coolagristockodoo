# Cool Agristock — Website

A marketing/documentation website for Cool Agristock. **This is entirely separate from the
Odoo addon** in `../cool_agristock/` — it has its own dependencies, build process, and
deployment target, and shares nothing with it besides reused brand assets (icon, screenshots) and
links out to the same GitHub documentation.

Stack: Next.js 14 (App Router, static export), TypeScript, Tailwind CSS. No backend, no database,
no server-side rendering at runtime — it builds to plain static HTML/CSS/JS.

## Local development

```bash
cd website
npm install
npm run dev
```

Open <http://localhost:3000>. French is served at `/` (default); English at `/en`.

## Checks

```bash
npm run typecheck   # tsc --noEmit
npm run lint         # next lint
npm run build        # production build + static export to out/
```

`npm run build` produces a fully static `out/` directory — every page is pre-rendered HTML with no
server required at runtime.

## Local preview of the production build

```bash
npm run build
npx serve out        # or: python3 -m http.server -d out 4321
```

## Project structure

```text
website/
  src/
    app/                 # routes (French unprefixed, English under /en/)
      page.tsx            /            (home, FR)
      product/page.tsx     /product
      services/page.tsx    /services
      documentation/page.tsx /documentation
      contact/page.tsx     /contact
      en/...                same five routes, English
      sitemap.ts, robots.ts
      layout.tsx, globals.css
    components/           Header, Footer, PageShell, HtmlLangSync
    views/                page content components (shared between FR/EN page.tsx wrappers)
    content/              en.ts / fr.ts dictionaries + getDictionary()
    types/content.ts       the Dictionary type both languages must satisfy
    lib/metadata.ts        shared SEO/Open Graph metadata builder
  public/images/          reused, already-verified Cool Agristock screenshots + icon
```

## Known limitations (honest, not hidden)

- **Contact form does not send anything.** It's a fully validated, controlled React form, but the
  submit button is disabled and no backend or form-delivery service is wired up. See
  `src/views/ContactView.tsx` — do not remove the `disabled` attribute without also implementing
  real, consented data handling.
- **`<html lang>` is corrected client-side**, not at the static-HTML level, because French (default,
  unprefixed) and English (`/en`) share one root layout for simplicity. See
  `src/components/HtmlLangSync.tsx` for why and the trade-off this implies for pre-JS accessibility
  tools.
- No automated end-to-end or visual regression tests exist yet — validation so far is `tsc`, ESLint,
  a successful static build, and manual link/content checks.

## Deployment

The site is a static export (`output: "export"` in `next.config.mjs`) — any static host or plain
nginx works. Options considered:

| Option | Cost | Notes |
|---|---|---|
| **Self-hosted VPS + nginx** | Already paid for (existing infrastructure) | Used for this deployment — see below. No new recurring cost. |
| Cloudflare Pages | Free tier available | Good option if moving off the VPS later; needs a Cloudflare account/DNS delegation not set up here. |
| Vercel | Free tier available | Simplest for a Next.js app specifically, but this is a static export, so it gains little over plain static hosting. |

### Deploying to the VPS (what was actually done)

1. Build: `npm run build` (produces `out/`).
2. Copy `out/` to the server, e.g.: `rsync -az --delete out/ root@<host>:/var/www/agriware-website/`
3. Nginx server block (HTTP; add TLS via `certbot --nginx` once DNS resolves):

   ```nginx
   server {
       listen 80;
       server_name agriware.agricarecentres.com;
       root /var/www/agriware-website;
       index index.html;
       location / {
           try_files $uri $uri.html $uri/ =404;
       }
       error_page 404 /404.html;
   }
   ```

4. `nginx -t && systemctl reload nginx`.
5. **DNS**: an A record for `agriware.agricarecentres.com` must point at the server's IP before the
   site is reachable publicly, and before `certbot` can issue a TLS certificate (HTTP-01 challenge
   needs the domain to already resolve there). This is a DNS-provider-side change, not something
   done from the server itself.

Not done as part of this deployment: purchasing a domain (the domain/subdomain already belongs to
the existing `agricarecentres.com` zone), any paid hosting service, or public DNS changes (outside
this session's access).
