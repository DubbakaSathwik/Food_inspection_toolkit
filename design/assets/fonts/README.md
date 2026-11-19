# Fonts

The whole design uses ONE family: **Manrope**, weights **400, 500, 600, 700, 800** (nothing else; no italics).
Fallback stack: `Manrope, Inter, system-ui, sans-serif`.

## NOT BUNDLED (genuinely not exportable here)
The design environment had no network access and no local copy of the Manrope font files, so the .woff2 files could not be included.
The prototype loads them from Google Fonts:

```html
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
```

For production (recommended, offline/privacy friendly) run in the React project:

```
npm i @fontsource-variable/manrope     # or @fontsource/manrope for static 400/500/600/700/800
```
and `import '@fontsource-variable/manrope'` in `main.jsx`. Manrope is SIL OFL-licensed.
Weight use: 400 body/inputs, 500 nav/secondary, 600 labels/buttons, 700 headings/active nav/metrics, 800 logo wordmark + pack art.
