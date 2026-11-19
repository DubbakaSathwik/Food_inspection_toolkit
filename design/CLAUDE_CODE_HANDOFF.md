# CRATE-SCAN — Claude Code Handoff (FINAL design)

This ZIP is the single source of truth for the final CRATE-SCAN prototype. Where the design changed after the first version, **only the final behaviour is described and shipped.**
All people, products, licence numbers, counts and dates in the design are **fictional sample data**.

CRATE-SCAN is an AI-assisted food-product inspection toolkit for FSSAI Food Safety Inspectors (developer: Sathwik).
Planned stack: React + Vite, FastAPI, MongoDB Atlas (temporary photo storage), Firebase Auth (Google sign-in, admin-activated accounts), Cloudinary, Gemini / NVIDIA / Hugging Face vision, PaddleOCR, ReportLab (PDF), Render.

---
## 1. What is in this ZIP

```
CLAUDE_CODE_HANDOFF.md      ← this file
README.md                   ← quick start
prototype/
  index.html                ← gallery linking all 44 screens
  screens/<Name>.html       ← 22 desktop pages (1440 wide)   ┐ runnable, no build step, open in a browser
  screens/M_<Name>.html     ← 22 mobile pages  (390 wide)    ┘ (double-click, or serve statically)
  runtime/dc-lite.js        ← tiny stand-in for the Claude Design runtime (renders {{bindings}}, if/for, setState)
  build_screens.py          ← how screens/ were generated from source/ (reference only)
source/                     ← the 44 ORIGINAL Claude Design files (*.dc.html). Canonical markup + per-screen logic.
design-system/
  tokens.json / tokens.css  ← colours, type, radii, sizes, motion
  global.css                ← the shared CSS present on every screen (hover, ripple, loader, animations, 760px rules)
  mobile-shell.css          ← extra rules for every in-app mobile screen (top bar, bottom tab bar, stacked tables)
  landing.css               ← landing-only rules (animated nav underline, hero, feature cards, mobile header)
  auth.css                  ← SignIn / Pending extras
assets/
  icons/*.svg (47)          ← every icon used (24×24, stroke 1.6) + _sprite.svg + mobile-tabbar/ (9 icons, stroke 1.7)
  logo/                     ← mark, horizontal lockup, exact HTML used
  illustrations/            ← demo product-pack drawings (HTML/CSS) + generator code
  fonts/README.md           ← Manrope 400–800 (see §9: font files NOT bundled)
screenshots/desktop|mobile  ← full-page JPEG of every screen as rendered from prototype/ (visual reference)
specs/screens.json          ← machine-readable list: every screen, both sizes, artboard + rendered heights, file paths
```
Total size ≈ 8 MB. Nothing unused is included (4 icons that existed in the generator but appear on no screen — filter, calendar, key, grid — were deliberately dropped).

### How to read the source
`source/*.dc.html` uses a tiny templating dialect: `{{path.to.value}}` bindings, `<sc-if value="{{x}}">`, `<sc-for list="{{x}}" as="p">`, and a `<script type="text/x-dc">` holding `class Component extends DCLogic { constructor(){ this.state={…} } renderVals(){ return {…} } }` (React-like `setState`). All styles are inline plus one `<style>` block in `<helmet>`. `prototype/screens/*.html` are the same files converted to run standalone via `runtime/dc-lite.js`.
**Port, don't copy:** rebuild as React components using the tokens/components below; use the HTML as pixel/behaviour reference and the screenshots to compare.

---
## 2. Screens, flow and routes (22 screens × 2 layouts = 44 files)

Suggested routes → file name (desktop `X`, mobile `M_X`).

| Route | File | Role | Purpose / key states |
|---|---|---|---|
| `/` | Main | public | Landing: header w/ nav (Home, Features, How it works, About) + single **Get started** button (= Sign in), hero w/ image slot, "Scan Products" feature cards (green left rule), how-it-works, about, footer. Scroll-spy highlights active nav item; nav hover has animated underline. |
| `/signin` | SignIn | public | One Google button ("Get started"/"Sign in" are the same action). Side image slot. |
| `/pending` | Pending | public | Shown after first Google sign-in until an admin activates the account. |
| `/inspector` | InspectorDashboard | inspector | Welcome, metric cards, "continue where you left off" card, recent inspections, banner image slot. |
| `/inspector/new` | NewInspection | inspector | Step 1 of 5 – photographs. Horizontal-scroll strip of photo slots + one preview below with colour border (green = OK, orange = problem + note saying which image has the issue). "For better results – cover these sections" guidance block (no tick bullets). |
| `/inspector/verify` | VerifyFields | inspector | Step 2 – AI reading popup/animation then editable fields. **High-confidence fields are auto-confirmed; only unconfirmed ones ask the user.** Every field editable. "Replay AI reading" button. |
| `/inspector/ai-review` | AIReview | inspector | Step 3 – AI-working animation (orbit/scan/dots, progress steps ~8 s) then continue. |
| `/inspector/findings/:id` | InspectionResults | inspector | Step 4 – findings, photo switcher, per-finding decision, suggested class **Verified / Not verified / Suspicious** (suggestion only), original AI value kept next to correction. |
| `/inspector/report/:id` | ReportPreview | inspector | Step 5 – report; **View** toggle (print view ⇄ mobile view); Download / Print / Share (same look as View); typed-name signature; generation animation. |
| `/inspector/history` | InspectionHistory | inspector | Filter chips (All/…); list/table. |
| `/inspector/proposals` | InspectorProposals | inspector | "Your proposals" with working **View** (expands detail, state `open`). |
| `/inspector/ask` | AskAI | inspector | Chat; internet-research toggle (off by default; research only when asked). |
| `/inspector/profile` | Profile | inspector | Account details. |
| `/admin` | AdminDashboard | admin | Metrics, pending proposals/approvals. |
| `/admin/reference` | ReferenceDatabase | admin | Reference products table, search, **Add Product** menu. |
| `/admin/reference/:id` | ProductDetail | admin | Record view; edit mode (`editing`, `saved`). |
| `/admin/rules` | ComplianceRules | admin | Rules list (classification rules NOT finalised — shown as editable placeholders). |
| `/admin/proposals` | AdminProposals | admin | Review proposals; outcome state `open/approved/rejected/info` + note. |
| `/admin/users` | UserManagement | admin | Approvals (role select + Approve/Decline), search, role/status filters, row action icons (view/edit/disable all working), Add user panel, notice banner. |
| `/admin/analytics` | Analytics | admin | Charts/metrics. |
| `/admin/audit` | AuditLogs | admin | Audit table. |
| `/admin/settings` | Settings | admin | Tabs; **Website Images** tab uploads hero/signin/banner images (stored `localStorage cs_img_hero|signin|banner` in the prototype → replace with real upload/Cloudinary). |

Main flow: `Main → SignIn → (Pending → admin approves) → InspectorDashboard → NewInspection → VerifyFields → AIReview → InspectionResults → ReportPreview → InspectorDashboard`. Admin: sidebar pages above. Logout → Main.

---
## 3. Screen sizes & breakpoints

There are exactly **two intentionally different layouts**, plus one CSS breakpoint.

| Layout | Device | Artboard viewport | Files |
|---|---|---|---|
| **Desktop** | laptop / desktop web | **1440 px wide** (heights vary per screen, below) | `X.dc.html` |
| **Mobile** | phone web | **390 px wide** (iPhone 14-class) | `M_X.dc.html` |

There is **no separate tablet design**. Between 761 px and 1440 px the desktop layout flexes (flex-wrap, `clamp()` padding, max content width 1280). **≤ 760 px** the shared CSS (`global.css`) switches the *desktop* pages to a compact form too, but the dedicated `M_*` pages are the intended mobile design and should be what you build to.

Artboard heights (px) — desktop / mobile (mobile heights are estimates; real height = content):
Main 3560/6764 · SignIn 900/1710 · Pending 900/1710 · InspectorDashboard 1620/4212 · NewInspection 1560/4056 · VerifyFields 3400/8000 · AIReview 1180/3068 · InspectionResults 3300/8000 · ReportPreview 2300/5980 · InspectionHistory 1420/3692 · InspectorProposals 1180/3068 · AskAI 1280/3328 · Profile 1120/2912 · AdminDashboard 1500/3900 · ReferenceDatabase 1340/3484 · ProductDetail 1700/4420 · ComplianceRules 1480/3848 · AdminProposals 1900/4940 · UserManagement 1620/4212 · Analytics 2050/5330 · AuditLogs 1240/3224 · Settings 1700/4420.
(Actual rendered heights from the exported pages are in `specs/screens.json`.)

### Desktop → Mobile differences (intentional, keep separate)
| Area | Desktop (1440) | Mobile (390) |
|---|---|---|
| App navigation | Left sidebar 256 px (logo, nav, Log out) | Sidebar **hidden**; sticky **top bar** (logo + role pill Inspector/Admin) and fixed **bottom tab bar**. Inspector tabs: Home, Inspect, History, Ask AI, Profile. Admin tabs: Home, Products, Users, Analytics, **More → Settings**. Active tab gets tint + pop animation. Sub-screens highlight their parent tab (e.g. Verify/AI Review/Findings/Report → Inspect). |
| Page padding / gaps | `36px clamp(18px,3.5vw,48px) 56px`, gap 28 | `16px 16px 104px` (space for tab bar), gap 18 |
| Headings | h1 32, h2 20 | h1 22, h2 17 |
| Cards | padding 24 | padding 16 |
| Multi-column grids | up to 4 columns | forced **2 columns** (`repeat(2,minmax(0,1fr))`); public pages → 1 column |
| Tables | real tables w/ header row | header hidden; each row becomes a **stacked card** (border, 12 radius) |
| Stepper (new inspection flow) | 5-step horizontal stepper (`.cs-step-f`) | Hidden; compact card (`.cs-step-c`) shows "STEP n OF 5", the **current step name only**, and a progress bar |
| Report actions | inline buttons | `.cs-pbtns` 2-column grid, ≥48 px tall; View/Download/Print/Share same style |
| Photo strip | horizontal scroll with preview below | same, **never wraps into a grid** (5+ photos scroll sideways); photo buttons sized to their text, all visible |
| Action rows | single row | `.cs-acts` wrap, each ≥46 px |
| Landing header | one row: logo · nav · Get started | Compact: smaller logo (28 px / 17 px text), Get started pill (40 px) top-right, nav drops to a second full-width row with top border, no horizontal scroll; "AI-assisted food inspection" hero spacing reduced (padding 20/44), hero image 300 px high; feature cards get 3 px olive left rule |
| Overflow | — | `overflow-x:hidden` globally — **no horizontal page scroll anywhere** (only the intentional photo strip scrolls) |
| Touch targets | 44 px | 46–52 px |
| Loader | same | same |

Elements that disappear on mobile: sidebar, foot Log out (`.cs-foot`), `.cs-hide-sm` items, table header rows, 5-step stepper. Elements that appear: top bar, bottom tab bar, compact step card.

---
## 4. Design system (see `design-system/`)
- **Look:** calm, cream page `#F6F2E6`, white cards with thin `#E5E4DA` borders, **Deep Sage primary `#56703A`** (button text contrast), brand palette Soft Sage `#C5D89D`, Muted Olive `#9CAB84`, Deep Sage `#89986D`. Monochrome outline icons, **no emoji, no notification bell**.
- **Type:** Manrope 400/500/600/700/800 only. h1 32/700, h2 20/700, body 14–15.5, labels 12.5/600, metric numbers 30/700, logo 800.
- **Radii:** controls/buttons 10, cards 12, chips 6, icon buttons 8, nav items 9, landing hero image 18.
- **Spacing:** 8 px grid; min touch target 44.
- **Status chips** (dot + label, 12.5/600): Verified (ok green), Not verified (neutral), Suspicious (warning orange `#FBEFD9/#7A4808`), Pending, Approved, Rejected (red tint), Info requested (blue-grey), Active, Draft, Archived, Inactive, Awaiting approval, Inspector, Admin, Super Admin, In review. Exact colours in `tokens.json`.
- **Motion:** page enter `csIn` .45 s + staggered children (+.05 s, up to 6); button hover shadow + press-scale .96 + white/olive **ripple** on click; `.cs-working` spinner on buttons; **page-to-page loader** (`#cs-load` ring overlay + `#cs-top` 3 px progress bar, shown on internal link click, never calls preventDefault/location — auto-hides after 1.2 s); AI animations `csScan csOrbit csPulse csDots csShimmer csWrite`; `prefers-reduced-motion` disables all. Keyframes: csIn csFade csSpin csRipple csPulse csScan csOrbit csShimmer csDots csPop csBar csWrite.

---
## 5. Components (React mapping)
Generated by helper functions in the prototype; build each as a component:

| Component | Notes |
|---|---|
| `Logo` | Mark (scan-corners + leaf) + "CRATE-SCAN" 800 weight. Sizes: sidebar 32/19, landing 34/21, mobile top bar 28/17. `assets/logo/` |
| `Button` (primary / secondary) | min-h 44, radius 10, 15/600, optional leading icon 17 px, hover `#485F30`, ripple, press-scale. Small = 10×18 padding, 14 px |
| `IconButton` | 36×36, radius 8, bordered, hover soft-green + olive border; has `aria-label` |
| `Chip`, `Pill` | status chip (dot) / plain pill |
| `Card`, `Metric` | white 12-radius card; metric = icon 24 + 30/700 number + label (highlight variant `#EEF2E1`) |
| `Sidebar`, `Topbar`(page header), `Shell` | 256 sidebar; admin nav shows a "12" badge on Product Proposals |
| `MobileTopBar`, `BottomTabBar` | see §3 |
| `DataTable` → `StackedCardList` on mobile | |
| `Stepper` (+ compact variant) | 5 steps: Photographs, Verify Fields, AI Review, Findings, Report |
| `Field`, `Select`, `SearchBox` | min-h 44, radius 10, border `#D8D6C9` |
| `ImageSlot` (placeholder) | dashed 1.5 px `#C9C6B4`, diagonal cream stripes, image icon + label; replaced by uploaded image via `data-cs-img` key (hero/signin/banner) |
| `PackIllustration` | CSS drawing of a product pack front/back (demo only) |
| `DemoNote`, `SampleTag` | info notices ("sample values for design preview") |
| `Backlink`, `SectionHeading`, `TextLink` | |
| `PhotoStrip` + `PhotoPreview` | horizontal scroll; coloured border green/orange + issue note |
| `FieldCard` (Verify) | editable value, confidence, auto-confirmed badge |
| `FindingCard`, `DecisionControl` | original AI value preserved beside correction |
| `AIWorkingOverlay` | top-pinned (not viewport-centred — the canvas iframe is as tall as the page); orbit + steps |
| `ReportDocument` | print view vs mobile view |
| `Loader` + `TopProgress` | see §4 |

Icons: use the 47 SVGs in `assets/icons` (or `_sprite.svg`, `<use href="#i-home">`). All 24×24 viewBox, `stroke=currentColor`, width 1.6, round caps/joins. Default render size 18; metrics 24; chevrons 15.

---
## 6. Interactions per screen (final behaviour)
- **Global:** link click → loader overlay + progress bar; buttons ripple/press; cards lift 2 px on hover; rows tint; no horizontal scroll.
- **Landing:** nav hover underline slides in; scroll-spy sets `.on`; smooth scroll; "Get started" → SignIn.
- **SignIn/Pending:** Google button → Pending (new user) – prototype links directly; real app = Firebase Google auth then check admin-activation flag.
- **NewInspection:** add/remove photo slots, horizontal strip, preview with green/orange border + "issue on image N" note; mobile progress = current step name only; capture-guidance block.
- **VerifyFields:** on load, "AI reading" popup/animation runs through steps (`readStep`), then fields. Confidence-based auto-confirm; unconfirmed fields prompt the user; every field editable (`editing`, `draft`); `setStatus`; **Replay AI reading** button.
- **AIReview:** timed steps (`step` 1→n) then proceeds.
- **InspectionResults:** `photo` switcher, `choice` (verified / notverified / suspicious — suggestion), `decisions` per finding, edit with `draft`; original AI value kept.
- **ReportPreview:** `view` print|mobile toggle, generating animation (`n`), download/print/share, typed-name signature (not a certified digital signature).
- **InspectorProposals:** `open` index expands proposal detail (View works on mobile too).
- **AskAI:** `msgs`, `web` toggle (internet research only when switched on), `draft`.
- **InspectionHistory:** `filter` chips.
- **UserManagement:** `decisions`, `roles`, `status`, `query`, `roleF`, `statF`, `viewId`, `notice`, `addOpen`, `newName/newEmail`, `added[]` — approve/decline, role change, search, filters, view/edit/disable icons, add user.
- **ProductDetail:** `editing`, `vals`, `saved`.
- **AdminProposals:** `outcome` open/approved/rejected/info + `note`.
- **Settings:** `tab`, `imgs` (Website Images upload/replace/remove), `note`.
- Pure-display screens: AdminDashboard, ReferenceDatabase, ComplianceRules, Analytics, AuditLogs, Profile, InspectorDashboard (links only).

---
## 7. Assets and where they are used
| Asset | Used in |
|---|---|
| Logo mark/lockup | Sidebar, landing header/footer, sign-in, mobile top bar |
| Image slots `hero` | Landing hero (Settings › Website Images) |
| Image slot `signin` | SignIn and Pending side panel |
| Image slot `banner` | InspectorDashboard banner |
| PackIllustration | Photo slots / verify / findings / reference product previews (demo, **simulated product images**) |
| Icons | 47 files in `assets/icons`; groups: nav (home, plus, history, proposal, chat, user, box, rules, users, chart, logs, settings, logout), actions (upload, camera, download, printer, share, edit, trash, refresh, crop, send, link, eye, search, back, arrow, chev, x, tick, check), status (alert, shield, info, flag, lock, clock, play, pause), content (file, doc, sheet, image, scan, sparkle, bulk) |
| Mobile tab-bar icons | `assets/icons/mobile-tabbar` (home, plus, hist, ai, user, box, users, chart, menu) |

Placeholder images are labelled slots by design — the user supplies real images later via Admin › Settings › Website Images.

---
## 8. Post-initial changes (all already baked into the final files)
1. Landing nav on **one line**, animated hover underline + scroll-spy; reduced hero spacing; feature cards green left rule.
2. Admin **Website Images** page for the placeholder images (hero/signin/banner).
3. Full **mobile** set for landing, inspector and admin (separate layouts, bottom tab bar).
4. Mobile fixes: bigger/neat photo buttons; proposals View works; report View toggle + neat 2-col action buttons (Share styled like View); progress shows current step only; capture-guidance block instead of tick bullets; "continue where you left" text no longer overflows; compact landing header/logo.
5. **Loading animations** page-to-page, button click/working animations, **AI working animations**, general motion polish (+ reduced-motion).
6. Fixed "preview navigated itself" (loader no longer sets `location`).
7. Verify Fields: **high-confidence auto-confirm**, all fields editable, top-pinned AI reading popup, Replay button.
8. New Inspection: photo **horizontal scroll** (no grid/stack) with coloured-border preview and per-image issue note.
9. **Horizontal scroll removed everywhere**.
10. User-management icon buttons all functional.
11. "Get started" and "Sign in" merged; **pending-approval** screen added.

---
## 9. Product rules to preserve in the real app
- Decision-support only; the **inspector decides**. Keep the **original AI value and the correction**.
- A licence match is **not** government verification. A missing reference record is **not** "fake". A packaging difference is **not** proof of counterfeiting.
- AI confidence ≠ measured accuracy. Typed signature ≠ certified digital signature.
- Verified / Not verified / Suspicious = **suggested only**; the rules are not finalised (owner will verify them later).
- Internet research **only when the user asks**.
- Photos are stored **temporarily**. New Google sign-ins stay on Pending until an admin activates them.
- Every sample value is fictional and labelled as such.

## 10. Recommended build mapping
React + Vite + React Router (routes in §2), Tailwind or CSS variables from `tokens.css`, `@fontsource-variable/manrope`. FastAPI endpoints: auth/me (Firebase ID-token verify + `active` flag), inspections CRUD, photo upload (Cloudinary), `/ocr` (PaddleOCR), `/analyze` (Gemini/NVIDIA/HF fallback), reference products, rules, proposals, users (approve/role), audit log, analytics, settings/images, `/report/pdf` (ReportLab). Use `source/` for exact markup and `screenshots/` to compare.

## 11. What could not be exported / limitations (honest list)
- **Manrope .woff2 files are not included** — no network/local copy in the design environment. Install via `@fontsource` (see `assets/fonts/README.md`). All weights needed: 400–800.
- Product pack images are **CSS drawings**, not photographs (simulated by design). Website images are placeholders.
- Mobile artboard heights are estimates; use content height.
- Runtime: the original Claude Design runtime (`support.js`) isn't exportable; `prototype/runtime/dc-lite.js` reproduces rendering/state for review. Behaviour is verified by rendering all 44 screens headlessly with no JS errors and no horizontal overflow.
- Canvas x/y positions of the artboards (editor-only metadata) are not included; they are irrelevant to the product.
- No backend exists; every action is front-end simulated.
