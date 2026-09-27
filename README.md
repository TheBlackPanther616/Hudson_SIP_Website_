# Joseph Hudson Jr. — SIP / Boards Website (SIP311)

Static site: no build step, no framework. Six pages + one stylesheet.

## Publish on GitHub Pages (≈5 minutes)
1. Create a new **public** repo named `YOUR-GITHUB.github.io` (site at the root URL) — or any name, e.g. `sip-site` (site at `https://YOUR-GITHUB.github.io/sip-site/`).
2. Upload everything in this folder (drag-and-drop on github.com works, or `git add . && git commit -m "SIP site" && git push`).
3. Repo → **Settings → Pages → Source: Deploy from a branch → main / (root) → Save**.
4. Wait ~1 minute; the URL appears at the top of the Pages settings. Paste it in the discussion post.

## Before you post — find-and-replace these placeholders
| Placeholder | Where | Replace with |
|---|---|---|
| `YOUR-GITHUB` | all pages (footer, SIP, Projects, Contact) | your GitHub username |
| `YOUR-FORM-ID` | contact.html | free Formspree endpoint (formspree.io → New form → copy the /f/xxxx id). Until then the form has no backend. |


## Images and documents to drop in
- Headshot is already in place (`img/headshot.png`).
- `img/` — logos, UML, mockup, n8n screenshot (names listed on each placeholder). Replace each `<div class="placeholder ...">` with `<img src="img/name.png" alt="...">`.
- SRS PDF, pitch deck (PDF + PPTX), logo video and stills, and UML figures are already in `docs/` and `img/`. Still to add: `docs/Hudson_SIP_Brief.pdf` (SIP Brief subpage embeds it automatically) and `img/thecallai-logo.png`.

## Pages
index · sip (with #claim #description #architecture #prototype #visuals #code #brief #roadmap) · sip-brief · boards · projects · contact
