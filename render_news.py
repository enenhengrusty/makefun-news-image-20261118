#!/usr/bin/env python3
"""render_news.py -- dev-time renderer for the WORLD NEWS front page.

Draws a 1024x1024 broadsheet-style front page for Wednesday 18 November 2026
as pure HTML + inline SVG, screenshots it at 2x with Playwright (system Chrome),
downscales to a crisp 1024x1024 ``entry.png`` with Pillow, and writes a 300x300
preview to ``out/preview_300.png`` for local inspection.

The submitted entrypoint is ``main.py``; this script only produces the image.
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
<style>
  :root {
    --paper: #f6f1e6;   /* newsprint cream   */
    --card:  #faf6ea;   /* panel surface     */
    --ink:   #16140e;   /* primary ink       */
    --ink2:  #57523f;   /* secondary ink     */
    --mut:   #8a8271;   /* muted / smallcaps */
    --rule:  #d8cfb8;   /* hairline rules    */
    --red:    #b3261e;  /* lead / breaking   */
    --blue:   #2f5d9e;  /* space             */
    --green:  #2e6b36;  /* climate           */
    --gold:   #a3781b;  /* finance           */
    --violet: #50449a;  /* security          */
    --magenta:#b04a86;  /* culture           */
    --goldbright: #f0d284; /* date ribbon text */
    --neutral: #b9b09b; /* gray bar (context) */
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1024px; height: 1024px; overflow: hidden;
    background: var(--paper);
    font-family: Arial, "Segoe UI", sans-serif;
    color: var(--ink);
  }
  .page {
    width: 1024px; height: 1024px; padding: 20px;
    display: grid;
    grid-template-columns: 316px 18px 316px 18px 316px;
    grid-template-rows: 100px 42px 14px 362px 14px 264px 14px 150px 24px;
  }

  /* ---------- masthead ---------- */
  .mast {
    grid-column: 1 / 6; grid-row: 1; position: relative;
    border-bottom: 1px solid var(--ink);
    display: flex; flex-direction: column;
  }
  .mast .topline {
    display: flex; justify-content: space-between; align-items: center;
    border-top: 3px solid var(--ink); border-bottom: 1px solid var(--rule);
    padding: 4px 2px;
    font-size: 9.5px; font-weight: bold; letter-spacing: .18em;
    color: var(--ink2); text-transform: uppercase;
  }
  .mast .nameplate {
    flex: 1 1 auto; min-height: 0;
    display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
  }
  .mast h1 {
    grid-column: 2;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 60px; font-weight: 700; line-height: 1;
    letter-spacing: .045em; color: var(--ink);
    white-space: nowrap;
  }
  .mast h1 .star { color: var(--red); font-size: 24px; vertical-align: 12px; }
  .mast .datestamp {
    grid-column: 3; justify-self: end;
    text-align: center; line-height: 1.08; white-space: nowrap;
    border: 2px solid var(--ink); padding: 5px 8px 4px; background: var(--card);
  }
  .mast .datestamp b {
    display: block; font-family: Georgia, serif;
    font-size: 21px; letter-spacing: .02em;
  }
  .mast .datestamp span {
    font-size: 8px; font-weight: bold; letter-spacing: .16em;
    color: var(--red); text-transform: uppercase;
  }
  .mast .subline {
    display: flex; justify-content: space-between;
    padding: 2px 2px 4px;
    font-size: 9px; font-weight: bold; letter-spacing: .14em;
    color: var(--mut); text-transform: uppercase;
  }

  /* ---------- date ribbon ---------- */
  .ribbon {
    grid-column: 1 / 6; grid-row: 2;
    display: flex; justify-content: space-between; align-items: center;
    background: var(--red);
    border: 2px solid var(--ink);
    padding: 0 16px;
    color: var(--goldbright);
  }
  .ribbon .side {
    font-size: 10px; font-weight: bold; letter-spacing: .18em;
    color: var(--paper); text-transform: uppercase;
  }
  .ribbon .date {
    font-family: Georgia, serif; font-weight: 700;
    font-size: 27px; letter-spacing: .06em; color: var(--goldbright);
  }

  /* ---------- shared panel chrome ---------- */
  .panel {
    background: var(--card);
    border: 2px solid var(--ink);
    padding: 12px 14px;
    display: flex; flex-direction: column;
    overflow: hidden;
    min-height: 0;
  }
  .panel .fig { flex: 1 1 auto; min-height: 0; }
  .panel .fig svg { width: 100%; height: 100%; display: block; }
  .tagrow { display: flex; justify-content: space-between; align-items: center; }
  .chip {
    color: #ffffff; font-size: 10px; font-weight: bold;
    letter-spacing: .14em; text-transform: uppercase;
    padding: 4px 8px;
  }
  .chip.red    { background: var(--red); }
  .chip.blue   { background: var(--blue); }
  .chip.green  { background: var(--green); }
  .chip.gold   { background: var(--gold); }
  .chip.violet { background: var(--violet); }
  .tagside { font-size: 9.5px; font-weight: bold; letter-spacing: .14em; color: var(--mut); text-transform: uppercase; }
  h2.head {
    font-family: Georgia, serif; font-weight: 700;
    color: var(--ink); line-height: 1.05; letter-spacing: -.005em;
  }
  .dek { font-size: 12.5px; line-height: 1.38; color: var(--ink2); }
  .caption {
    font-size: 9.5px; font-weight: bold; letter-spacing: .1em;
    color: var(--mut); text-transform: uppercase;
  }
  .rule-double { border-top: 3px solid var(--ink); border-bottom: 1px solid var(--ink); height: 5px; }

  /* ---------- lead story ---------- */
  .lead { grid-column: 1 / 4; grid-row: 4; padding: 14px 16px 10px; }
  .lead h2 { font-size: 33px; margin-top: 8px; }
  .lead .dek { margin-top: 7px; font-size: 13.5px; }
  .lead .fig { margin-top: 6px; }

  /* ---------- voyager ---------- */
  .voyager { grid-column: 5 / 6; grid-row: 4; padding: 12px 14px 10px; }
  .voyager h2 { font-size: 22.5px; margin-top: 7px; }
  .voyager .hero {
    margin-top: 6px; font-family: Georgia, serif; font-weight: 700;
    font-size: 36px; line-height: 1.02; color: var(--ink);
    border-bottom: 4px solid var(--blue); padding-bottom: 4px;
  }
  .voyager .stats { display: flex; margin-top: 8px; }
  .voyager .stat { flex: 1; }
  .voyager .stat b { display: block; font-size: 15px; font-family: Georgia, serif; }
  .voyager .stat span { font-size: 8px; font-weight: bold; letter-spacing: .1em; color: var(--mut); text-transform: uppercase; }
  .voyager .fig { margin-top: 8px; }
  .voyager .caption { margin-top: 7px; }

  /* ---------- middle row ---------- */
  .ecb   { grid-column: 1 / 2; grid-row: 6; }
  .cop31 { grid-column: 3 / 4; grid-row: 6; }
  .yemen { grid-column: 5 / 6; grid-row: 6; }
  .mid h2 { font-size: 21.5px; margin-top: 7px; }
  .mid .hero {
    margin-top: 5px; font-family: Georgia, serif; font-weight: 700;
    font-size: 40px; line-height: 1.1; display: flex; align-items: baseline;
  }
  .mid .hero .unit { font-size: 13px; line-height: 1.1; margin-left: 7px; color: var(--ink2); font-family: Arial, sans-serif; font-weight: bold; }
  .mid .dek { margin-top: 6px; font-size: 12px; }
  .mid .fig { margin-top: auto; }
  .mid .caption { margin-top: 5px; }

  /* ---------- wire strip ---------- */
  .wire { grid-column: 1 / 6; grid-row: 8; display: flex; flex-direction: column; }
  .wire .whead {
    display: flex; justify-content: space-between; align-items: center;
    padding: 3px 2px 5px;
    font-size: 10px; font-weight: bold; letter-spacing: .18em;
    color: var(--mut); text-transform: uppercase;
    border-bottom: 1px solid var(--rule);
  }
  .wire .whead .t { color: var(--ink); }
  .wire .wbody { flex: 1; display: flex; gap: 12px; padding-top: 8px; }
  .wcell {
    flex: 1; background: var(--card); border: 2px solid var(--ink);
    padding: 9px 10px; display: flex; flex-direction: column;
  }
  .wcell .wrow { display: flex; gap: 9px; align-items: flex-start; }
  .wcell .icon { flex: 0 0 42px; }
  .wcell h3 {
    font-family: Georgia, serif; font-weight: 700;
    font-size: 16.5px; line-height: 1.06;
  }
  .wcell .wdetail { margin-top: 5px; font-size: 10px; line-height: 1.32; color: var(--ink2); }

  /* ---------- footer ---------- */
  .footer {
    grid-column: 1 / 6; grid-row: 9;
    border-top: 1px solid var(--ink);
    display: flex; justify-content: center; align-items: flex-end;
    padding-top: 5px;
    font-size: 9px; font-weight: bold; letter-spacing: .16em;
    color: var(--mut); text-transform: uppercase;
  }
</style>
</head>
<body>
<div class="page">

  <!-- ================= MASTHEAD ================= -->
  <header class="mast">
    <div class="topline">
      <span>Vol. CXIV &middot; No. 322</span>
      <span>The Daily Record of the Planet</span>
      <span>Price: Free</span>
    </div>
    <div class="nameplate">
      <h1><span class="star">&#10022;</span> WORLD NEWS <span class="star">&#10022;</span></h1>
      <div class="datestamp" data-qa="datestamp">
        <b>18.11.2026</b>
        <span>Wednesday</span>
      </div>
    </div>
    <div class="subline">
      <span>Single-sheet evening edition</span>
      <span>All times UTC</span>
      <span>Est. MMXXVI</span>
    </div>
  </header>

  <!-- ================= DATE RIBBON ================= -->
  <div class="ribbon">
    <span class="side">One Day &middot; One Front Page</span>
    <span class="date">WED &middot; 18 NOVEMBER 2026</span>
    <span class="side">Edition 0118 &middot; UTC</span>
  </div>

  <!-- ================= LEAD: APEC ================= -->
  <section class="panel lead" data-qa="lead">
    <div class="tagrow">
      <span class="chip red">Lead &middot; Asia-Pacific</span>
      <span class="tagside">Shenzhen &middot; China &middot; 33rd Summit</span>
    </div>
    <h2 class="head">Xi Welcomes Trump and Putin as APEC Opens</h2>
    <p class="dek">33rd APEC Leaders&rsquo; Meeting, Nov 18&ndash;19. Xi calls for open trade
      and AI cooperation; Putin criticises Western sanctions, ahead of tomorrow&rsquo;s
      three-way talks.</p>
    <div class="fig" data-qa="lead-fig">
      <svg viewBox="0 0 620 132" width="620" height="132" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="620" height="132" fill="#efe5cc"/>
        <!-- sun -->
        <circle cx="60" cy="52" r="23" fill="#e2b34c" stroke="#16140e" stroke-width="1.5"/>
        <!-- Shenzhen skyline -->
        <path fill="#16140e" d="M0,94 L0,66 L30,66 L30,94 L44,94 L44,40 L70,40 L70,94 L86,94 L86,58
                 L108,58 L108,94 L118,94 L120,20 L126,8 L132,20 L134,94 L152,94 L152,52 L184,52 L184,94
                 L200,94 L200,64 L226,64 L226,94 L244,94 L244,44 L270,44 L270,94 L286,94 L286,70 L314,70
                 L314,94 L332,94 L332,54 L358,54 L358,94 L374,94 L374,64 L400,64 L400,94 L418,94 L418,46
                 L444,46 L444,94 L462,94 L462,70 L490,70 L490,94 L508,94 L508,58 L534,58 L534,94 L550,94
                 L550,66 L580,66 L580,94 L600,94 L600,60 L620,60 L620,94 Z"/>
        <!-- flags -->
        <g stroke="#16140e" stroke-width="1">
          <line x1="112" y1="92" x2="112" y2="30"/>
          <line x1="308" y1="92" x2="308" y2="26"/>
          <line x1="508" y1="92" x2="508" y2="30"/>
        </g>
        <g stroke="#16140e" stroke-width="1">
          <!-- China -->
          <rect x="112" y="30" width="26" height="17" fill="#b3261e"/>
          <circle cx="120" cy="36" r="2.6" fill="#f0d284"/>
          <circle cx="127" cy="34" r="1.1" fill="#f0d284"/><circle cx="129" cy="37" r="1.1" fill="#f0d284"/>
          <circle cx="128" cy="40" r="1.1" fill="#f0d284"/><circle cx="125" cy="42" r="1.1" fill="#f0d284"/>
          <!-- United States -->
          <rect x="308" y="26" width="26" height="17" fill="#faf6ea"/>
          <rect x="308" y="26" width="11" height="9" fill="#2f5d9e"/>
          <rect x="308" y="37.5" width="26" height="2.2" fill="#b3261e"/>
          <rect x="308" y="41" width="26" height="2.2" fill="#b3261e"/>
          <!-- Russia -->
          <rect x="508" y="30" width="26" height="17" fill="#faf6ea"/>
          <rect x="508" y="30" width="26" height="5.6" fill="#faf6ea"/>
          <rect x="508" y="35.6" width="26" height="5.7" fill="#2f5d9e"/>
          <rect x="508" y="41.3" width="26" height="5.7" fill="#b3261e"/>
        </g>
        <!-- ground -->
        <rect x="0" y="94" width="620" height="38" fill="#16140e"/>
        <!-- three leaders, cream cut-outs (busts end at y=112, above the labels) -->
        <g fill="#faf6ea">
          <!-- Xi Jinping -->
          <path d="M150,112 L152,102 Q185,92 218,102 L220,112 Z"/>
          <circle cx="185" cy="76" r="13.5"/>
          <path d="M171.5,73 Q185,60 198.5,73 L198.5,71.5 Q198.5,69.5 196,68.5 Q185,66 174,68.5 Q171.5,69.5 171.5,71.5 Z"/>
          <!-- Donald Trump -->
          <path d="M276,112 L278,102 Q310,90 342,102 L344,112 Z"/>
          <circle cx="310" cy="73" r="14.5"/>
          <path d="M296,69 Q296,58 306,54 Q318,49 327,56 Q330,58 330,61 Q331,64 327,65 Q322,61 316,62 Q310,63 307,65 Q299,67 296,69 Z"/>
          <!-- Vladimir Putin -->
          <path d="M404,112 L406,102 Q436,92 466,102 L468,112 Z"/>
          <circle cx="435" cy="76" r="13.5"/>
          <path d="M421.5,72 Q435,61 448.5,72 L448.5,70 Q435,58 421.5,70 Z"/>
          <!-- handshake arms -->
          <path d="M220,108 Q252,100 268,102 Q280,104 282,110 Q280,116 268,114 L222,112 Z"/>
          <path d="M340,104 Q372,98 390,102 Q402,106 402,110 Q398,114 388,112 L344,112 Z"/>
        </g>
        <!-- "shakes hands" callout on its own dark pill -->
        <rect x="284" y="99" width="56" height="14" rx="3" fill="#16140e"
              stroke="#e2b34c" stroke-width="0.8"/>
        <text x="312" y="109" font-family="Arial, sans-serif" font-size="8" font-weight="bold"
              letter-spacing=".1em" fill="#e2b34c" text-anchor="middle">SHAKES HANDS</text>
        <!-- name plaques on the ink ground, clear of the busts -->
        <g fill="#16140e" stroke="#faf6ea" stroke-width="0.8">
          <rect x="155" y="117" width="60" height="13" rx="3"/>
          <rect x="268" y="117" width="84" height="13" rx="3"/>
          <rect x="390" y="117" width="90" height="13" rx="3"/>
        </g>
        <g font-family="Arial, sans-serif" font-size="8" font-weight="bold"
           letter-spacing=".12em" fill="#faf6ea" text-anchor="middle">
          <text x="185" y="126.5">XI JINPING</text>
          <text x="310" y="126.5">DONALD TRUMP</text>
          <text x="435" y="126.5">VLADIMIR PUTIN</text>
        </g>
      </svg>
    </div>
  </section>

  <!-- ================= VOYAGER 1 ================= -->
  <section class="panel voyager" data-qa="voyager">
    <div class="tagrow">
      <span class="chip blue">Space &middot; NASA</span>
      <span class="tagside">Deep Space</span>
    </div>
    <h2 class="head">Voyager 1 Passes 1 Light-Day</h2>
    <div class="hero" data-qa="voyager-hero">1 LIGHT-DAY</div>
    <div class="stats">
      <div class="stat"><b>25.9B</b><span>km from Earth</span></div>
      <div class="stat"><b>173</b><span>AU from Sun</span></div>
      <div class="stat"><b>24H</b><span>one-way radio</span></div>
    </div>
    <div class="fig" data-qa="voyager-fig">
      <svg viewBox="0 0 284 118" width="284" height="118" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="284" height="118" fill="#16140e"/>
        <!-- stars -->
        <g fill="#faf6ea">
          <circle cx="30" cy="16" r="1.4"/><circle cx="66" cy="26" r="1"/><circle cx="102" cy="12" r="1.6"/>
          <circle cx="140" cy="22" r="1"/><circle cx="176" cy="10" r="1.3"/><circle cx="216" cy="18" r="1"/>
          <circle cx="250" cy="8" r="1.2"/><circle cx="268" cy="26" r="1.6"/><circle cx="48" cy="44" r="1"/>
          <circle cx="92" cy="58" r="1.3"/><circle cx="158" cy="52" r="1"/><circle cx="206" cy="42" r="1.2"/>
          <circle cx="240" cy="88" r="1"/><circle cx="120" cy="86" r="1.4"/><circle cx="60" cy="98" r="1"/>
          <circle cx="180" cy="98" r="1.3"/><circle cx="24" cy="80" r="1"/><circle cx="96" cy="38" r="0.8"/>
          <circle cx="226" cy="64" r="0.8"/><circle cx="14" cy="110" r="1.1"/><circle cx="276" cy="112" r="1"/>
        </g>
        <!-- sun -->
        <circle cx="18" cy="58" r="10" fill="#e2b34c"/>
        <g stroke="#e2b34c" stroke-width="1.6" stroke-linecap="round">
          <line x1="18" y1="42" x2="18" y2="34"/><line x1="34" y1="58" x2="42" y2="58"/>
          <line x1="18" y1="74" x2="18" y2="82"/><line x1="6" y1="46" x2="2" y2="42"/>
          <line x1="6" y1="70" x2="2" y2="74"/><line x1="30" y1="46" x2="34" y2="42"/>
        </g>
        <!-- trajectory -->
        <line x1="30" y1="58" x2="226" y2="54" stroke="#faf6ea" stroke-width="1.4" stroke-dasharray="6 5"/>
        <path d="M228,54 l-7,-3 M228,54 l-7,3" stroke="#faf6ea" stroke-width="1.4"/>
        <!-- probe -->
        <g stroke="#faf6ea" fill="none" stroke-width="1.8" stroke-linecap="round">
          <path d="M232,54 a11,11 0 1 0 20,8"/>
          <rect x="243" y="46" width="9" height="15" rx="2" fill="#faf6ea" stroke="none"/>
          <line x1="243" y1="42" x2="236" y2="30"/>
          <rect x="233" y="26" width="8" height="5" fill="#faf6ea" stroke="none"/>
        </g>
        <!-- labels -->
        <g font-family="Arial, sans-serif" font-size="10" font-weight="bold"
           letter-spacing=".14em" text-anchor="middle">
          <text x="126" y="40" fill="#faf6ea">1 LIGHT-DAY</text>
          <text x="126" y="72" fill="#e2b34c">24 H RADIO LAG</text>
          <text x="238" y="108" fill="#cfc5a8" font-size="8.5">10:16 UTC</text>
        </g>
      </svg>
    </div>
    <p class="caption">Reported by NASA &middot; 10:16 UTC &middot; 18 Nov 2026</p>
  </section>

  <!-- ================= ECB ================= -->
  <section class="panel mid ecb" data-qa="ecb">
    <div class="tagrow">
      <span class="chip gold">Finance &middot; Frankfurt</span>
      <span class="tagside">FSR</span>
    </div>
    <h2 class="head">ECB Warns: $4T Off-Book AI Debt</h2>
    <div class="hero" data-qa="ecb-hero">$4T<span class="unit">off-balance-sheet</span></div>
    <p class="dek">AI data-centre borrowing flagged in the Financial Stability Review as a
      systemic, subprime-like risk.</p>
    <div class="fig" data-qa="ecb-fig">
      <svg viewBox="0 0 284 60" width="284" height="60" xmlns="http://www.w3.org/2000/svg">
        <!-- three server racks -->
        <g fill="#faf6ea" stroke="#16140e" stroke-width="1.6">
          <rect x="14" y="8" width="46" height="40"/>
          <rect x="119" y="8" width="46" height="40"/>
          <rect x="224" y="8" width="46" height="40"/>
        </g>
        <g stroke="#16140e" stroke-width="1.2">
          <line x1="20" y1="18" x2="54" y2="18"/><line x1="20" y1="26" x2="54" y2="26"/>
          <line x1="20" y1="34" x2="54" y2="34"/><line x1="20" y1="42" x2="54" y2="42"/>
          <line x1="125" y1="18" x2="159" y2="18"/><line x1="125" y1="26" x2="159" y2="26"/>
          <line x1="125" y1="34" x2="159" y2="34"/><line x1="125" y1="42" x2="159" y2="42"/>
          <line x1="230" y1="18" x2="264" y2="18"/><line x1="230" y1="26" x2="264" y2="26"/>
          <line x1="230" y1="34" x2="264" y2="34"/><line x1="230" y1="42" x2="264" y2="42"/>
        </g>
        <!-- LEDs -->
        <g fill="#2e6b36">
          <circle cx="52" cy="14" r="1.6"/><circle cx="52" cy="22" r="1.6"/><circle cx="52" cy="30" r="1.6"/>
          <circle cx="157" cy="14" r="1.6"/><circle cx="157" cy="22" r="1.6"/><circle cx="157" cy="30" r="1.6"/>
          <circle cx="262" cy="14" r="1.6"/><circle cx="262" cy="22" r="1.6"/><circle cx="262" cy="30" r="1.6"/>
        </g>
        <g fill="#b3261e">
          <circle cx="52" cy="38" r="1.6"/><circle cx="157" cy="38" r="1.6"/><circle cx="262" cy="38" r="1.6"/>
        </g>
        <!-- warning above the middle rack, clear of everything -->
        <path d="M142,2 L149,12 L135,12 Z" fill="#a3781b" stroke="#16140e" stroke-width="1.2"/>
        <text x="142" y="11" font-family="Arial, sans-serif" font-size="8" font-weight="bold"
              fill="#16140e" text-anchor="middle">!</text>
        <!-- rack captions in a clean bottom band -->
        <g font-family="Arial, sans-serif" font-size="8" font-weight="bold" letter-spacing=".1em"
           fill="#57523f" text-anchor="middle">
          <text x="37" y="57">AI</text><text x="142" y="57">AI DEBT</text><text x="247" y="57">AI</text>
        </g>
      </svg>
    </div>
    <p class="caption">ECB Financial Stability Review &middot; 18 Nov</p>
  </section>

  <!-- ================= COP31 ================= -->
  <section class="panel mid cop31" data-qa="cop31">
    <div class="tagrow">
      <span class="chip green">Climate &middot; Antalya</span>
      <span class="tagside">COP31</span>
    </div>
    <h2 class="head">Stocktake Opens at COP31</h2>
    <p class="dek">Second Global Stocktake begins in T&uuml;rkiye amid a financing row:
      pledges fall far short of COP30.</p>
    <div class="fig" data-qa="cop31-fig">
      <svg viewBox="0 0 284 62" width="284" height="62" xmlns="http://www.w3.org/2000/svg">
        <!-- title, clear of the tall bar's label -->
        <text x="16" y="8" font-family="Arial, sans-serif" font-size="8" font-weight="bold"
              letter-spacing=".08em" fill="#8a8271">ADAPTATION FUND PLEDGES</text>
        <!-- baseline -->
        <line x1="16" y1="52" x2="268" y2="52" stroke="#16140e" stroke-width="1.6"/>
        <!-- COP31 bar ($50M) -->
        <path d="M70,42 Q70,38 74,38 L146,38 Q150,38 150,42 L150,52 L70,52 Z" fill="#2e6b36"/>
        <!-- COP30 bar ($135M) -->
        <path d="M170,18 Q170,14 174,14 L246,14 Q250,14 250,18 L250,52 L170,52 Z" fill="#b9b09b"/>
        <!-- values, clear of the bar tops and the viewBox top -->
        <g font-family="Arial, sans-serif" font-weight="bold" text-anchor="middle">
          <text x="110" y="33" font-size="11.5" fill="#16140e">$50M</text>
          <text x="210" y="10" font-size="11.5" fill="#16140e">$135M</text>
        </g>
        <!-- category labels, clear of everything -->
        <g font-family="Arial, sans-serif" font-size="8.5" font-weight="bold"
           letter-spacing=".1em" fill="#57523f" text-anchor="middle">
          <text x="110" y="60">COP31 &middot; NOW</text>
          <text x="210" y="60">COP30</text>
        </g>
      </svg>
    </div>
    <p class="caption">Pledges down 63% vs COP30 &middot; 18 Nov</p>
  </section>

  <!-- ================= YEMEN ================= -->
  <section class="panel mid yemen" data-qa="yemen">
    <div class="tagrow">
      <span class="chip violet">Security &middot; Middle East</span>
      <span class="tagside">Yemen</span>
    </div>
    <h2 class="head">60 Houthi Targets Struck</h2>
    <div class="hero" data-qa="yemen-hero">60<span class="unit">military targets</span></div>
    <p class="dek">Coalition strikes 60 Houthi targets; air defence downs cruise missiles
      aimed at Riyadh.</p>
    <div class="fig" data-qa="yemen-fig">
      <svg viewBox="0 0 284 62" width="284" height="62" xmlns="http://www.w3.org/2000/svg">
        <!-- radar rings -->
        <g fill="none" stroke="#50449a">
          <circle cx="52" cy="30" r="10" stroke-width="1.4" opacity=".85"/>
          <circle cx="52" cy="30" r="20" stroke-width="1.2" opacity=".55"/>
          <circle cx="52" cy="30" r="29" stroke-width="1" opacity=".32"/>
        </g>
        <line x1="52" y1="30" x2="82" y2="30" stroke="#50449a" stroke-width="1" opacity=".55"/>
        <circle cx="52" cy="30" r="2.2" fill="#50449a"/>
        <!-- targets -->
        <g fill="#b3261e">
          <circle cx="62" cy="25" r="2.8"/><circle cx="46" cy="39" r="2.8"/><circle cx="34" cy="23" r="2.8"/>
          <circle cx="68" cy="41" r="2.8"/><circle cx="55" cy="49" r="2.8"/><circle cx="26" cy="35" r="2.8"/>
        </g>
        <!-- strike jet -->
        <g fill="#16140e">
          <path d="M196,8 L212,14 L236,18 L244,18 L228,22 L224,26 L236,26 L246,20 L252,22 L252,26
                   L244,28 L224,30 L212,26 Z"/>
        </g>
        <g stroke="#16140e" stroke-width="1.2" stroke-dasharray="4 3" opacity=".7">
          <line x1="176" y1="16" x2="190" y2="16"/>
        </g>
        <!-- Riyadh: buildings, shield arc, and a clean labelled pill below -->
        <g>
          <rect x="196" y="38" width="12" height="12" fill="#16140e"/>
          <rect x="212" y="42" width="10" height="8" fill="#16140e"/>
          <rect x="226" y="38" width="9" height="12" fill="#16140e"/>
          <path d="M180,50 Q206,30 232,50" fill="none" stroke="#50449a" stroke-width="2.2"/>
        </g>
        <rect x="168" y="52" width="78" height="9" rx="3" fill="#16140e"
              stroke="#50449a" stroke-width="0.8"/>
        <text x="207" y="58.5" font-family="Arial, sans-serif" font-size="7" font-weight="bold"
              letter-spacing=".1em" fill="#faf6ea" text-anchor="middle">RIYADH DEFENDED</text>
      </svg>
    </div>
    <p class="caption">Saudi-led coalition announcement &middot; 18 Nov</p>
  </section>

  <!-- ================= WIRE STRIP ================= -->
  <section class="wire" data-qa="wire">
    <div class="whead">
      <span class="t">&#9670; The Wire</span>
      <span>The day&rsquo;s other stories</span>
    </div>
    <div class="wbody">
      <div class="wcell" data-qa="w1">
        <div class="wrow">
          <div class="icon">
            <svg viewBox="0 0 42 42" width="42" height="42" xmlns="http://www.w3.org/2000/svg">
              <rect x="1" y="13" width="22.5" height="16" fill="#2f5d9e"/>
              <rect x="25" y="13" width="16" height="16" fill="#b3261e"/>
              <text x="12" y="25" font-family="Arial, sans-serif" font-size="8.5" font-weight="bold"
                    fill="#ffffff" text-anchor="middle">56</text>
              <text x="33" y="25" font-family="Arial, sans-serif" font-size="8.5" font-weight="bold"
                    fill="#ffffff" text-anchor="middle">44</text>
              <text x="12" y="37" font-family="Arial, sans-serif" font-size="6.5" font-weight="bold"
                    fill="#ffffff" text-anchor="middle">D</text>
              <text x="33" y="37" font-family="Arial, sans-serif" font-size="6.5" font-weight="bold"
                    fill="#ffffff" text-anchor="middle">R</text>
            </svg>
          </div>
          <div>
            <h3>Senate Sealed at 56&ndash;44</h3>
            <p class="wdetail">Peltola wins Alaska with 50.1% &mdash; Democrats hold the chamber.</p>
          </div>
        </div>
      </div>
      <div class="wcell" data-qa="w2">
        <div class="wrow">
          <div class="icon">
            <svg viewBox="0 0 42 42" width="42" height="42" xmlns="http://www.w3.org/2000/svg">
              <rect x="3" y="27" width="8" height="11" fill="#a3781b"/>
              <rect x="14" y="21" width="8" height="17" fill="#a3781b"/>
              <rect x="25" y="14" width="8" height="24" fill="#a3781b"/>
              <path d="M29,10 L36,4 M36,4 L36,10 M36,4 L29,4" fill="none"
                    stroke="#16140e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <text x="21" y="8" font-family="Arial, sans-serif" font-size="8" font-weight="bold"
                    fill="#16140e" text-anchor="middle">6.00%</text>
            </svg>
          </div>
          <div>
            <h3>Bank Indonesia Hikes to 6.00%</h3>
            <p class="wdetail">Surprise 25 bps to defend the rupiah &middot; UK CPI 3.6%, Ofgem cap +26%.</p>
          </div>
        </div>
      </div>
      <div class="wcell" data-qa="w3">
        <div class="wrow">
          <div class="icon">
            <svg viewBox="0 0 42 42" width="42" height="42" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="8" width="30" height="21" fill="none" stroke="#50449a" stroke-width="2.2"/>
              <line x1="19" y1="29" x2="19" y2="35" stroke="#50449a" stroke-width="2.2"/>
              <line x1="12" y1="37" x2="28" y2="37" stroke="#50449a" stroke-width="2.2"/>
              <circle cx="19" cy="18" r="5" fill="none" stroke="#16140e" stroke-width="1.8"/>
              <circle cx="19" cy="18" r="1.8" fill="#16140e"/>
              <text x="30" y="12" font-family="Arial, sans-serif" font-size="6.5" font-weight="bold"
                    fill="#50449a">AI</text>
            </svg>
          </div>
          <div>
            <h3>8,400 Anti-AI Exam Monitors</h3>
            <p class="wdetail">South Korea adds proctors across 1,312 Suneung test centres.</p>
          </div>
        </div>
      </div>
      <div class="wcell" data-qa="w4">
        <div class="wrow">
          <div class="icon">
            <svg viewBox="0 0 42 42" width="42" height="42" xmlns="http://www.w3.org/2000/svg">
              <path d="M21,3 L25.8,14.2 L37,14.6 L28.7,22 L31.5,34 L21,27.4 L10.5,34 L13.3,22 L5,14.6 L16.2,14.2 Z"
                    fill="#a3781b" stroke="#16140e" stroke-width="1.2"/>
              <text x="21" y="25" font-family="Arial, sans-serif" font-size="11" font-weight="bold"
                    fill="#16140e" text-anchor="middle">99</text>
            </svg>
          </div>
          <div>
            <h3>GTA VI Reviews: 99/100</h3>
            <p class="wdetail">Embargo lifts today on Metacritic &middot; game launches Nov 19.</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ================= FOOTER ================= -->
  <footer class="footer">
    <span>World News &middot; Compiled 18.11.2026 &middot; All times UTC &middot; The day in one front page</span>
  </footer>

</div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

QA_PROBE = r"""
() => {
  const bad = [];
  document.querySelectorAll('[data-qa]').forEach((el) => {
    const r = el.getBoundingClientRect();
    const ok = el.scrollWidth <= el.clientWidth + 1 && el.scrollHeight <= el.clientHeight + 1
      && r.left >= -1 && r.top >= -1 && r.right <= 1025 && r.bottom <= 1025;
    if (!ok) {
      bad.push(el.getAttribute('data-qa') + ': rect=' + [r.left, r.top, r.right, r.bottom].map(n => Math.round(n)).join(',')
        + ' scroll=' + el.scrollWidth + 'x' + el.scrollHeight + ' client=' + el.clientWidth + 'x' + el.clientHeight);
    }
  });
  return bad;
}
"""


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
        page.evaluate("document.fonts.ready.then(() => {})")
        page.wait_for_timeout(120)

        overflow = page.evaluate(QA_PROBE)
        if overflow:
            browser.close()
            raise RuntimeError("layout overflow detected:\n  " + "\n  ".join(overflow))

        shot = page.screenshot(
            clip={"x": 0, "y": 0, "width": SIZE, "height": SIZE}
        )
        browser.close()

    hi = Image.open(io.BytesIO(shot)).convert("RGB")
    if hi.size != (SIZE * SS_RATIO, SIZE * SS_RATIO):
        raise RuntimeError(f"unexpected screenshot size {hi.size}")
    (OUT_DIR / "shot2x.png").write_bytes(shot)  # dev artifact for filter QA

    # BOX is the exact 2:1 decimation filter: no ringing, no artefacts.
    img = hi.resize((SIZE, SIZE), Image.Resampling.BOX)

    OUT_DIR.mkdir(exist_ok=True)
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
