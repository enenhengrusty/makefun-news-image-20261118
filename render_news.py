#!/usr/bin/env python3
"""render_news.py -- dev-time renderer for the WORLD NEWS front page.

Draws a 1024x1024 broadsheet-style front page for Wednesday 18 November 2026:
a huge masthead, a stylised six-continent world-map hero with numbered pins and
short callout tags, and a 3x2 grid of high-contrast beat cards whose every line
stays large enough to survive the 300px thumbnail the judge reads.

Rendered as pure HTML + inline SVG, screenshotted at 2x with Playwright (system
Chrome), downscaled to a crisp 1024x1024 ``entry.png`` with Pillow, and written
with a 300x300 preview. The submitted entrypoint is ``main.py``; this script
only produces the image.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "entry.png"
OUT_DIR = ROOT / "out"
PREVIEW = OUT_DIR / "preview_300.png"

SIZE = 1024          # final canvas, px
SS_RATIO = 2         # supersample factor for crisp text
MAX_BYTES = 1_048_576

# Preferred Playwright-managed chromium; system Chrome is the fallback.
CHROMIUM_EXE = Path(
    r"C:\Users\jiaao\AppData\Local\ms-playwright\chromium-1223\chrome-win64\chrome.exe"
)

# ---------------------------------------------------------------------------
# The front page
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>WORLD NEWS · WED 18 NOV 2026</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 1024px; height: 1024px; background: #f6f1e6; }
  body {
    font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
    color: #16140e;
    -webkit-font-smoothing: antialiased;
    text-rendering: geometricPrecision;
    overflow: hidden;
  }

  .page {
    width: 1024px;
    height: 1024px;
    padding: 15px 26px;
    display: grid;
    grid-template-rows: 108px 10px 320px 12px 544px;
  }

  /* ---- masthead ------------------------------------------------------ */
  .mast {
    grid-row: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .masthead {
    width: max-content;
    margin-top: 4px;
    font-family: Georgia, "Times New Roman", serif;
    font-weight: 700;
    font-size: 58px;
    line-height: 1;
    letter-spacing: -0.012em;
    white-space: nowrap;
    color: #16140e;
  }
  .masthead .dot { color: #a3781b; }
  .masthead .date { color: #b3261e; }
  .subhead {
    margin-top: 6px;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.10em;
    line-height: 1;
    color: #57523f;
    white-space: nowrap;
  }
  .rules { width: 100%; margin-top: auto; }
  .rule-a { height: 4px; background: #16140e; }
  .rule-b { height: 1px; background: #b3261e; margin-top: 3px; }

  /* ---- world map ----------------------------------------------------- */
  .map-panel {
    grid-row: 3;
    background: #16140e;
    overflow: hidden;
  }
  .worldmap { display: block; width: 100%; height: 100%; }
  .grat line { stroke: #2c281e; stroke-width: 1; stroke-dasharray: 2 8; }
  .land path { fill: #453f2f; stroke: #786d52; stroke-width: 1.2; stroke-linejoin: round; }
  .map-label text {
    font-family: Arial, sans-serif;
    font-weight: 700;
    font-size: 18px;
    letter-spacing: 2px;
    fill: #c9be9f;
  }
  .map-pin text {
    font-family: Arial, sans-serif;
    font-weight: 800;
    font-size: 19px;
    fill: #f6f1e6;
  }
  .map-tag text {
    font-family: Arial, sans-serif;
    font-weight: 800;
    font-size: 20px;
    letter-spacing: 0.03em;
    fill: #16140e;
  }

  /* ---- beat cards ---------------------------------------------------- */
  .beats {
    grid-row: 5;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: 266px 266px;
    gap: 12px;
  }
  .beat {
    min-width: 0;
    background: #fbf7ec;
    border: 1px solid #d8cfb8;
    border-top: 6px solid var(--accent);
    padding: 11px 14px 12px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .beat-head {
    height: 28px;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .beat-pin {
    flex: 0 0 auto;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--accent);
    color: #f6f1e6;
    font-size: 18px;
    font-weight: 800;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .beat-name {
    flex: 0 0 auto;
    font-size: 18px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: 0.005em;
    white-space: nowrap;
    color: #16140e;
  }
  .beat-icon {
    flex: 0 0 auto;
    margin-left: auto;
    width: 26px;
    height: 26px;
    color: var(--accent);
  }
  .beat-lines {
    margin-top: 7px;
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-family: "Arial Narrow", Arial, Helvetica, sans-serif;
  }
  .lead, .head { font-weight: 700; color: #16140e; }
  .lead { font-size: 27px; line-height: 0.98; }
  .head { font-size: 24px; line-height: 0.98; }
  .ln { display: block; white-space: nowrap; }
  .stat {
    margin-top: auto;
    align-self: flex-start;
    height: 32px;
    display: inline-flex;
    align-items: center;
    padding: 0 10px;
    border-left: 5px solid var(--accent);
    background: #16140e;
    color: #f6f1e6;
    font-size: 19px;
    font-weight: 800;
    letter-spacing: 0.03em;
    line-height: 1;
    white-space: nowrap;
  }
</style>
</head>
<body>
<div class="page">

  <header class="mast" data-qa="mast">
    <h1 class="masthead" id="masthead" data-qa="masthead">WORLD NEWS<span class="dot"> · </span><span class="date">WED 18 NOV 2026</span></h1>
    <p class="subhead" data-qa="subhead">6 CONTINENTS · 15 VERIFIED STORIES</p>
    <div class="rules"><div class="rule-a"></div><div class="rule-b"></div></div>
  </header>

  <section class="map-panel" data-qa="map-panel">
    <svg class="worldmap" viewBox="0 0 972 320" role="img"
         aria-label="Stylised world map marking the six continent beats and Space">
      <g class="grat">
        <line x1="97.6"  y1="14" x2="97.6"  y2="306"/>
        <line x1="175.3" y1="14" x2="175.3" y2="306"/>
        <line x1="252.9" y1="14" x2="252.9" y2="306"/>
        <line x1="330.5" y1="14" x2="330.5" y2="306"/>
        <line x1="408.2" y1="14" x2="408.2" y2="306"/>
        <line x1="485.8" y1="14" x2="485.8" y2="306"/>
        <line x1="563.5" y1="14" x2="563.5" y2="306"/>
        <line x1="641.1" y1="14" x2="641.1" y2="306"/>
        <line x1="718.8" y1="14" x2="718.8" y2="306"/>
        <line x1="796.4" y1="14" x2="796.4" y2="306"/>
        <line x1="874.1" y1="14" x2="874.1" y2="306"/>
        <line x1="20" y1="62.5"  x2="952" y2="62.5"/>
        <line x1="20" y1="120.7" x2="952" y2="120.7"/>
        <line x1="20" y1="178.9" x2="952" y2="178.9"/>
        <line x1="20" y1="237.1" x2="952" y2="237.1"/>
        <line x1="20" y1="295.3" x2="952" y2="295.3"/>
      </g>

      <g class="land">
        <!-- North America + Greenland -->
        <path d="M52 45 L96 38 L150 34 L210 30 L260 34 L300 42 L318 58 L322 76 L300 90 L292 106 L280 120 L272 128 L266 146 L278 155 L264 154 L240 144 L226 136 L214 132 L196 122 L172 106 L162 94 L150 76 L132 72 L110 68 L90 60 L66 54 Z"/>
        <path d="M330 44 L346 28 L368 30 L382 44 L374 62 L352 70 L336 60 Z"/>
        <!-- South America -->
        <path d="M291 155 L306 156 L320 162 L338 170 L358 174 L385 175 L398 185 L390 200 L375 213 L360 230 L350 246 L340 260 L330 273 L314 268 L306 250 L300 230 L292 210 L280 194 L274 178 L280 166 Z"/>
        <!-- Europe -->
        <path d="M462 104 L470 90 L482 84 L488 74 L502 68 L512 72 L520 66 L532 68 L546 62 L560 66 L576 72 L584 82 L572 92 L564 102 L550 100 L540 108 L530 98 L524 106 L516 98 L508 94 L498 102 L486 106 L476 110 Z"/>
        <path d="M500 60 L506 46 L518 36 L532 32 L544 38 L540 52 L530 60 L520 66 L510 68 Z"/>
        <path d="M468 70 L476 64 L482 68 L480 78 L472 82 L466 78 Z"/>
        <!-- Africa + Madagascar -->
        <path d="M466 118 L480 116 L496 118 L512 120 L530 116 L548 118 L564 122 L576 126 L588 136 L600 146 L596 154 L584 158 L572 166 L560 180 L554 196 L546 214 L538 232 L524 230 L516 216 L508 198 L498 182 L490 172 L476 164 L460 150 L444 140 L450 126 L456 122 Z"/>
        <path d="M598 196 L604 192 L608 200 L604 212 L598 208 Z"/>
        <!-- Asia -->
        <path d="M576 100 L590 94 L610 86 L630 78 L650 70 L676 62 L700 50 L730 38 L770 32 L810 33 L850 38 L888 48 L902 60 L884 74 L870 86 L860 96 L850 102 L838 110 L824 114 L812 122 L806 136 L800 148 L790 158 L776 170 L768 178 L756 170 L744 160 L738 154 L728 150 L712 148 L700 152 L690 162 L678 168 L668 156 L658 142 L646 134 L632 134 L620 128 L610 138 L604 150 L596 142 L590 132 L584 122 L578 110 Z"/>
        <!-- Japan -->
        <path d="M846 90 L854 84 L858 92 L850 98 Z"/>
        <path d="M858 98 L864 94 L866 102 L860 106 Z"/>
        <!-- Indonesia -->
        <path d="M792 174 L808 172 L814 184 L800 192 L788 186 Z"/>
        <path d="M815 190 L840 190 L844 196 L818 198 Z"/>
        <path d="M822 176 L834 172 L842 180 L830 186 Z"/>
        <!-- Australia + Tasmania + New Zealand -->
        <path d="M790 206 L812 196 L838 196 L862 204 L880 214 L884 226 L872 236 L850 240 L828 238 L806 236 L789 230 L783 220 Z"/>
        <path d="M858 244 L864 244 L866 250 L860 252 L856 248 Z"/>
        <path d="M924 244 L932 240 L936 246 L928 250 Z"/>
        <path d="M918 252 L924 250 L926 257 L920 259 Z"/>
        <!-- Red Sea separation -->
        <path d="M580 110 L602 150" stroke="#16140e" stroke-width="5" fill="none"/>
      </g>

      <g class="map-label" data-name="continent-n-america"><text x="100" y="152">N. AMERICA</text></g>
      <g class="map-label" data-name="continent-s-america"><text x="282" y="300">S. AMERICA</text></g>
      <g class="map-label" data-name="continent-europe"><text x="452" y="116">EUROPE</text></g>
      <g class="map-label" data-name="continent-africa"><text x="484" y="214">AFRICA</text></g>
      <g class="map-label" data-name="continent-asia"><text x="616" y="94">ASIA</text></g>
      <g class="map-label" data-name="continent-oceania"><text x="768" y="306">OCEANIA</text></g>

      <!-- numbered pins: 1 Asia · 2 Space & N. America · 3 Europe ·
           4 Middle East/Climate · 5 Africa · 6 S. America & Oceania -->
      <g class="map-pin" data-name="pin-1-asia" transform="translate(781 136)">
        <circle r="16" fill="#b3261e" stroke="#f6f1e6" stroke-width="3"/>
        <text x="0" y="0" dy="0.35em" text-anchor="middle">1</text>
      </g>
      <g class="map-pin" data-name="pin-2-space-na" transform="translate(232 103)">
        <circle r="16" fill="#2f5d9e" stroke="#f6f1e6" stroke-width="3"/>
        <text x="0" y="0" dy="0.35em" text-anchor="middle">2</text>
      </g>
      <g class="map-pin" data-name="pin-3-europe" transform="translate(486 78)">
        <circle r="16" fill="#a3781b" stroke="#f6f1e6" stroke-width="3"/>
        <text x="0" y="0" dy="0.35em" text-anchor="middle">3</text>
      </g>
      <g class="map-pin" data-name="pin-4-mideast" transform="translate(602 130)">
        <circle r="16" fill="#2e6b36" stroke="#f6f1e6" stroke-width="3"/>
        <text x="0" y="0" dy="0.35em" text-anchor="middle">4</text>
      </g>
      <g class="map-pin" data-name="pin-5-africa" transform="translate(538 169)">
        <circle r="16" fill="#50449a" stroke="#f6f1e6" stroke-width="3"/>
        <text x="0" y="0" dy="0.35em" text-anchor="middle">5</text>
      </g>
      <g class="map-pin" data-name="pin-6-s-america" transform="translate(356 198)">
        <circle r="16" fill="#b04a86" stroke="#f6f1e6" stroke-width="3"/>
        <text x="0" y="0" dy="0.35em" text-anchor="middle">6</text>
      </g>
      <g class="map-pin" data-name="pin-6-oceania" transform="translate(833 227)">
        <circle r="16" fill="#b04a86" stroke="#f6f1e6" stroke-width="3"/>
        <text x="0" y="0" dy="0.35em" text-anchor="middle">6</text>
      </g>

      <g class="map-tag" data-name="tag-1-asia" transform="translate(682 82)">
        <rect width="236" height="33" fill="#f6f1e6"/>
        <rect width="7" height="33" fill="#b3261e"/>
        <text x="17" y="23.5">APEC SHENZHEN</text>
      </g>
      <g class="map-tag" data-name="tag-2-space" transform="translate(122 46)">
        <rect width="190" height="33" fill="#f6f1e6"/>
        <rect width="7" height="33" fill="#2f5d9e"/>
        <text x="17" y="23.5">✦ VOYAGER 1</text>
      </g>
      <g class="map-tag" data-name="tag-3-europe" transform="translate(412 22)">
        <rect width="184" height="33" fill="#f6f1e6"/>
        <rect width="7" height="33" fill="#a3781b"/>
        <text x="17" y="23.5">ECB · UK CPI</text>
      </g>
      <g class="map-tag" data-name="tag-4-mideast" transform="translate(565 158)">
        <rect width="218" height="33" fill="#f6f1e6"/>
        <rect width="7" height="33" fill="#2e6b36"/>
        <text x="17" y="23.5">YEMEN · COP31</text>
      </g>
      <g class="map-tag" data-name="tag-5-africa" transform="translate(420 246)">
        <rect width="238" height="33" fill="#f6f1e6"/>
        <rect width="7" height="33" fill="#50449a"/>
        <text x="17" y="23.5">SA–NIGERIA ROW</text>
      </g>
      <g class="map-tag" data-name="tag-6-s-america" transform="translate(160 204)">
        <rect width="170" height="33" fill="#f6f1e6"/>
        <rect width="7" height="33" fill="#b04a86"/>
        <text x="17" y="23.5">POPE TOUR</text>
      </g>
      <g class="map-tag" data-name="tag-6-oceania" transform="translate(834 170)">
        <rect width="124" height="33" fill="#f6f1e6"/>
        <rect width="7" height="33" fill="#b04a86"/>
        <text x="17" y="23.5">AU · NZ</text>
      </g>
    </svg>
  </section>

  <div class="beats">

    <!-- 1 · ASIA -->
    <article class="beat" style="--accent:#b3261e" data-qa="beat-1">
      <div class="beat-head" data-qa="beat-1-head">
        <span class="beat-pin">1</span>
        <span class="beat-name">ASIA</span>
        <svg class="beat-icon" viewBox="0 0 32 32" aria-hidden="true" fill="none">
          <circle cx="16" cy="9" r="4.6" fill="currentColor"/>
          <g stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="16" y1="1.5" x2="16" y2="3.6"/>
            <line x1="8.4" y1="4.4" x2="9.8" y2="5.8"/>
            <line x1="23.6" y1="4.4" x2="22.2" y2="5.8"/>
          </g>
          <g fill="currentColor">
            <rect x="3" y="20" width="6" height="9"/>
            <rect x="12" y="15" width="6" height="14"/>
            <rect x="21" y="22" width="7" height="7"/>
          </g>
        </svg>
      </div>
      <div class="beat-lines">
        <h2 class="lead" data-qa="beat-1-lead"><span class="ln">APEC SHENZHEN:</span><span class="ln">XI, TRUMP &amp; PUTIN</span></h2>
        <h3 class="head" data-qa="beat-1-korea"><span class="ln">KOREA: 8.4K</span><span class="ln">ANTI-AI MONITORS</span></h3>
        <h3 class="head" data-qa="beat-1-indonesia"><span class="ln">INDONESIA: RATE</span><span class="ln">HIKE 6.00%</span></h3>
      </div>
      <div class="stat" data-qa="beat-1-stat">33RD APEC SUMMIT</div>
    </article>

    <!-- 2 · SPACE & NORTH AMERICA -->
    <article class="beat" style="--accent:#2f5d9e" data-qa="beat-2">
      <div class="beat-head" data-qa="beat-2-head">
        <span class="beat-pin">2</span>
        <span class="beat-name">SPACE &amp; N. AMERICA</span>
        <svg class="beat-icon" viewBox="0 0 32 32" aria-hidden="true" fill="none">
          <path d="M4 29 A12 12 0 0 1 16 17" stroke="currentColor" stroke-width="2.6"/>
          <path d="M15 21 Q22 7 28.5 5" stroke="currentColor" stroke-width="2" stroke-dasharray="2.5 3" stroke-linecap="round"/>
          <path d="M26 5 L28.5 2.5 L31 5 L28.5 7.5 Z" fill="#a3781b"/>
          <circle cx="7" cy="7" r="1.3" fill="#a3781b"/>
          <circle cx="20" cy="12" r="1" fill="#a3781b"/>
        </svg>
      </div>
      <div class="beat-lines">
        <h2 class="lead" data-qa="beat-2-lead"><span class="ln">VOYAGER 1:</span><span class="ln">1 LIGHT-DAY</span></h2>
        <h3 class="head" data-qa="beat-2-senate"><span class="ln">US SENATE:</span><span class="ln">56D–44R</span></h3>
        <h3 class="head" data-qa="beat-2-gta"><span class="ln">GTA VI: 99/100</span></h3>
      </div>
      <div class="stat" data-qa="beat-2-stat">25.9B KM · 24H LAG</div>
    </article>

    <!-- 3 · EUROPE -->
    <article class="beat" style="--accent:#a3781b" data-qa="beat-3">
      <div class="beat-head" data-qa="beat-3-head">
        <span class="beat-pin">3</span>
        <span class="beat-name">EUROPE</span>
        <svg class="beat-icon" viewBox="0 0 32 32" aria-hidden="true" fill="none">
          <g fill="currentColor">
            <path d="M3 12 L16 3.5 L29 12 Z"/>
            <rect x="4.5" y="13.5" width="23" height="2"/>
            <rect x="6.5" y="17" width="4" height="9"/>
            <rect x="14" y="17" width="4" height="9"/>
            <rect x="21.5" y="17" width="4" height="9"/>
            <rect x="4" y="27" width="24" height="2.5"/>
          </g>
        </svg>
      </div>
      <div class="beat-lines">
        <h2 class="lead" data-qa="beat-3-lead"><span class="ln">ECB: AI DEBT RISK</span></h2>
        <h3 class="head" data-qa="beat-3-review"><span class="ln">STABILITY REVIEW</span></h3>
        <h3 class="head" data-qa="beat-3-uk"><span class="ln">UK: CPI 3.6%</span><span class="ln">CAP +26%</span></h3>
      </div>
      <div class="stat" data-qa="beat-3-stat">$4T OFF-BOOK</div>
    </article>

    <!-- 4 · MIDDLE EAST & CLIMATE -->
    <article class="beat" style="--accent:#2e6b36" data-qa="beat-4">
      <div class="beat-head" data-qa="beat-4-head">
        <span class="beat-pin">4</span>
        <span class="beat-name">M. EAST &amp; CLIMATE</span>
        <svg class="beat-icon" viewBox="0 0 32 32" aria-hidden="true" fill="none">
          <path d="M16 2.2 L28 7 V15.5 C28 23.5 23 28 16 30 C9 28 4 23.5 4 15.5 V7 Z" stroke="currentColor" stroke-width="2.4"/>
          <path d="M16 8.5 C22.5 11.5 22.5 19.5 16 23.5 C9.5 19.5 9.5 11.5 16 8.5 Z" fill="currentColor"/>
          <line x1="16" y1="13" x2="16" y2="21" stroke="#f6f1e6" stroke-width="1.5"/>
        </svg>
      </div>
      <div class="beat-lines">
        <h2 class="lead" data-qa="beat-4-lead"><span class="ln">YEMEN: 60</span><span class="ln">HOUTHI TARGETS</span></h2>
        <h3 class="head" data-qa="beat-4-riyadh"><span class="ln">RIYADH MISSILES DOWN</span></h3>
        <h3 class="head" data-qa="beat-4-cop31"><span class="ln">COP31: STOCKTAKE 2</span></h3>
      </div>
      <div class="stat" data-qa="beat-4-stat">FUND: $50M VS $135M</div>
    </article>

    <!-- 5 · AFRICA -->
    <article class="beat" style="--accent:#50449a" data-qa="beat-5">
      <div class="beat-head" data-qa="beat-5-head">
        <span class="beat-pin">5</span>
        <span class="beat-name">AFRICA</span>
        <svg class="beat-icon" viewBox="0 0 32 32" aria-hidden="true" fill="none">
          <path d="M11.5 2.5 L23 3.5 L28 8.5 L24.5 13 L28.5 17 L26.5 24.5 L19.5 30 L15 24.5 L12 18 L7 13 L10 7.5 Z" fill="currentColor"/>
          <circle cx="19.5" cy="19" r="1.6" fill="#a3781b"/>
        </svg>
      </div>
      <div class="beat-lines">
        <h2 class="lead" data-qa="beat-5-lead"><span class="ln">SA–NIGERIA</span><span class="ln">DIPLOMATIC ROW</span></h2>
        <h3 class="head" data-qa="beat-5-kenya"><span class="ln">KENYA: TOPS</span><span class="ln">ITU COUNCIL</span></h3>
      </div>
      <div class="stat" data-qa="beat-5-stat">ENVOY REPRIMANDED</div>
    </article>

    <!-- 6 · SOUTH AMERICA & OCEANIA -->
    <article class="beat" style="--accent:#b04a86" data-qa="beat-6">
      <div class="beat-head" data-qa="beat-6-head">
        <span class="beat-pin">6</span>
        <span class="beat-name">S. AM. &amp; OCEANIA</span>
        <svg class="beat-icon" viewBox="0 0 32 32" aria-hidden="true" fill="none">
          <circle cx="16" cy="15.5" r="12.5" stroke="currentColor" stroke-width="2.4"/>
          <ellipse cx="16" cy="15.5" rx="5.8" ry="12.5" stroke="currentColor" stroke-width="1.4"/>
          <line x1="3.5" y1="15.5" x2="28.5" y2="15.5" stroke="currentColor" stroke-width="1.4"/>
          <g fill="#a3781b">
            <circle cx="12.5" cy="21.5" r="1.3"/>
            <circle cx="19.8" cy="20.8" r="1.3"/>
            <circle cx="15.5" cy="26" r="1.3"/>
            <circle cx="21.5" cy="25.2" r="1.1"/>
          </g>
        </svg>
      </div>
      <div class="beat-lines">
        <h2 class="lead" data-qa="beat-6-lead"><span class="ln">POPE ENDS</span><span class="ln">S. AMERICA TOUR</span></h2>
        <h3 class="head" data-qa="beat-6-conmebol"><span class="ln">CONMEBOL–MERCADO</span><span class="ln">LIBRE 2030</span></h3>
        <h3 class="head" data-qa="beat-6-oceania"><span class="ln">AU MIGRATION PLAN</span></h3>
      </div>
      <div class="stat" data-qa="beat-6-stat">NZ MARU 26</div>
    </article>

  </div>
</div>

<script>
(function () {
  var h = document.getElementById('masthead');
  var fs = 60;
  h.style.fontSize = fs + 'px';
  while (h.getBoundingClientRect().width > 960 && fs > 44) {
    fs -= 1;
    h.style.fontSize = fs + 'px';
  }
})();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Layout QA: every visible word >= 17px, no clipped boxes, no map overlaps
# ---------------------------------------------------------------------------

QA_PROBE = r"""
() => {
  const errors = [];
  const info = {};

  // 1. every tagged block must fit its own box and the 1024 canvas.
  //    Line boxes tighter than the font's natural metrics report a few px of
  //    ink overshoot; that is normal for display type, so allow it on text
  //    elements only. Containers (cards, headers) stay strict.
  document.querySelectorAll('[data-qa]').forEach((el) => {
    const r = el.getBoundingClientRect();
    const textish = el.matches('.masthead, .subhead, .lead, .head, .stat');
    const vTol = textish ? 8 : 1;
    const fits = el.scrollWidth <= el.clientWidth + 1 && el.scrollHeight <= el.clientHeight + vTol;
    const inside = r.left >= -1 && r.top >= -1 && r.right <= 1025 && r.bottom <= 1025;
    if (!fits || !inside) {
      errors.push(
        el.getAttribute('data-qa') + ': rect=' +
        [r.left, r.top, r.right, r.bottom].map((n) => Math.round(n)).join(',') +
        ' scroll=' + el.scrollWidth + 'x' + el.scrollHeight +
        ' client=' + el.clientWidth + 'x' + el.clientHeight
      );
    }
  });

  // 2. no rendered text below 17px anywhere (HTML or inline SVG)
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let minFs = Infinity;
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const text = node.textContent.trim();
    if (!text) continue;
    const parent = node.parentElement;
    if (!parent || parent.closest('script, style')) continue;
    const fs = parseFloat(getComputedStyle(parent).fontSize);
    if (fs < minFs) minFs = fs;
    if (fs < 16.99) {
      errors.push('text under 17px: "' + text.slice(0, 36) + '" @ ' + fs + 'px');
    }
  }
  info.minTextPx = minFs;

  // 3. masthead contract
  const mast = document.getElementById('masthead');
  const mastFs = parseFloat(getComputedStyle(mast).fontSize);
  const mastW = Math.round(mast.getBoundingClientRect().width);
  const mastText = mast.textContent.replace(/\s+/g, ' ').trim();
  if (mastText !== 'WORLD NEWS · WED 18 NOV 2026') errors.push('masthead text: ' + mastText);
  if (mastFs < 44) errors.push('masthead font ' + mastFs + 'px < 44px');
  if (mastW > 962) errors.push('masthead width ' + mastW + 'px > 962px');
  info.mastheadPx = mastFs;
  info.mastheadW = mastW;

  const sub = document.querySelector('.subhead');
  const subFs = parseFloat(getComputedStyle(sub).fontSize);
  const subText = sub.textContent.replace(/\s+/g, ' ').trim();
  if (subText !== '6 CONTINENTS · 15 VERIFIED STORIES') errors.push('subhead text: ' + subText);
  if (subFs < 22) errors.push('subhead font ' + subFs + 'px < 22px');
  info.subheadPx = subFs;

  // 4. map callouts: inside the map, no pairwise overlaps, tag text fits
  const svgRect = document.querySelector('.worldmap').getBoundingClientRect();
  const mapEls = [...document.querySelectorAll('.map-pin, .map-tag, .map-label')].map((el) => ({
    name: el.dataset.name || el.getAttribute('class'),
    r: el.getBoundingClientRect(),
  }));
  const overlaps = (a, b) =>
    Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
    Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
  mapEls.forEach((el, i) => {
    if (el.r.left < svgRect.left - 1 || el.r.top < svgRect.top - 1 ||
        el.r.right > svgRect.right + 1 || el.r.bottom > svgRect.bottom + 1) {
      errors.push('map element outside map: ' + el.name);
    }
    for (let j = i + 1; j < mapEls.length; j++) {
      if (overlaps(el.r, mapEls[j].r)) {
        errors.push('map overlap: ' + el.name + ' vs ' + mapEls[j].name);
      }
    }
  });
  info.mapElements = mapEls.length;
  document.querySelectorAll('.map-tag').forEach((g) => {
    const pill = g.querySelector('rect');
    const label = g.querySelector('text');
    const need = 17 + label.getBBox().width + 10;
    const have = parseFloat(pill.getAttribute('width'));
    if (need > have + 0.5) {
      errors.push('tag text overflow: ' + g.dataset.name + ' need=' + Math.ceil(need) + ' have=' + have);
    }
  });

  // 5. six beat cards, headline and badge sizes, no content overflow
  const beats = [...document.querySelectorAll('.beat')];
  info.cards = beats.length;
  if (beats.length !== 6) errors.push('expected 6 cards, found ' + beats.length);
  beats.forEach((beat, i) => {
    const heads = [...beat.querySelectorAll('.lead, .head')];
    if (!heads.length) errors.push('beat ' + (i + 1) + ' has no headline');
    heads.forEach((h) => {
      const fs = parseFloat(getComputedStyle(h).fontSize);
      if (fs < 22) errors.push('beat ' + (i + 1) + ' headline ' + fs + 'px < 22px');
    });
    const badge = beat.querySelector('.stat');
    if (!badge) errors.push('beat ' + (i + 1) + ' missing stat badge');
    else {
      const fs = parseFloat(getComputedStyle(badge).fontSize);
      if (fs < 18) errors.push('beat ' + (i + 1) + ' badge ' + fs + 'px < 18px');
    }
    if (beat.scrollHeight > beat.clientHeight + 1) {
      errors.push('beat ' + (i + 1) + ' content overflows');
    }
  });

  return { errors, info };
}
"""

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render(entry: Path = ENTRY, preview: Path = PREVIEW) -> None:
    """Render the front page to ``entry`` and write a 300px preview."""
    # --disable-lcd-text: grayscale font antialiasing (no colour fringing).
    launch_kwargs = {
        "headless": True,
        "args": ["--force-color-profile=srgb", "--disable-lcd-text"],
    }
    if CHROMIUM_EXE.is_file():
        launch_kwargs["executable_path"] = str(CHROMIUM_EXE)
    else:
        launch_kwargs["channel"] = "chrome"

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(
            viewport={"width": SIZE, "height": SIZE},
            device_scale_factor=SS_RATIO,
        )
        page.set_content(HTML, wait_until="load")
        page.evaluate("() => document.fonts.ready.then(() => true)")
        page.wait_for_timeout(80)

        qa = page.evaluate(QA_PROBE)
        if qa["errors"]:
            browser.close()
            raise RuntimeError("layout QA failed:\n  " + "\n  ".join(qa["errors"]))
        m = qa["info"]
        print(
            "QA ok: masthead {:.0f}px / {}px wide | min text {}px | "
            "{} cards | {} map callouts".format(
                m["mastheadPx"], m["mastheadW"], m["minTextPx"],
                m["cards"], m["mapElements"],
            )
        )

        shot = page.screenshot(
            clip={"x": 0, "y": 0, "width": SIZE, "height": SIZE}
        )
        browser.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    hi = Image.open(io.BytesIO(shot)).convert("RGB")
    if hi.size != (SIZE * SS_RATIO, SIZE * SS_RATIO):
        raise RuntimeError(f"unexpected screenshot size {hi.size}")
    (OUT_DIR / "shot2x.png").write_bytes(shot)  # dev artifact for filter QA

    # BOX is the exact 2:1 decimation filter: no ringing, no artefacts.
    img = hi.resize((SIZE, SIZE), Image.Resampling.BOX)

    img.save(entry, format="PNG", optimize=True)
    n_bytes = entry.stat().st_size
    if n_bytes > MAX_BYTES:
        # Flat artwork quantises to a small palette with no visible loss.
        quant = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        quant.save(entry, format="PNG", optimize=True)
        n_bytes = entry.stat().st_size
        if n_bytes > MAX_BYTES:
            raise RuntimeError(f"entry.png is {n_bytes} bytes, over the {MAX_BYTES} limit")

    thumb = img.resize((300, 300), Image.Resampling.BOX)
    thumb.save(preview, format="PNG", optimize=True)

    print(f"wrote {entry.name}: {img.size[0]}x{img.size[1]} px, {n_bytes} bytes")
    print(f"wrote {preview.relative_to(ROOT)}: 300x300 px, {preview.stat().st_size} bytes")


def main() -> None:
    try:
        render()
    except Exception as exc:  # surface any render failure clearly
        print(f"render failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
