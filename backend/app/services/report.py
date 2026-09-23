"""Compliance report rendering — HTML and PDF, from one scan's persisted data.

M3 owns the *content* (ATLAS text, mitigations, compliance refs); M1 owns the export
wiring. When M3 hands over a real template, replace `REPORT_INTRO` and the section copy
below — the layout, pagination and download plumbing stay as they are.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from html import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.db.base import Scan

INK = colors.HexColor("#141210")
MUTED = colors.HexColor("#6B655D")
ACCENT = colors.HexColor("#B4361E")
RULE = colors.HexColor("#DAD5CB")
PAPER = colors.HexColor("#FAFAF8")

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}

REPORT_INTRO = (
    "This report summarises an automated adversarial robustness assessment. The target model was "
    "executed inside an isolated sandbox against the attack suite listed below; each finding is "
    "mapped to a MITRE ATLAS tactic and technique, with an OWASP ML Top 10 and NIST AI RMF "
    "reference for compliance traceability."
)


def _report_data(scan: Scan) -> dict[str, Any]:
    findings = sorted(
        scan.findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 0), reverse=True
    )
    raw = scan.raw_result.json_blob if scan.raw_result else {}
    asr_rows: list[tuple[str, float]] = []
    for block in ("evasion", "black_box"):
        for attack, payload in (raw.get(block) or {}).items():
            asr_rows.append((attack, float(payload.get("asr", 0.0))))
    for level, payload in (raw.get("poisoning") or {}).items():
        asr_rows.append((f"poisoning {level}", float(payload.get("accuracy_drop", 0.0))))

    return {
        "scan": scan,
        "model": scan.model,
        "score": scan.score,
        "findings": findings,
        "raw": raw,
        "asr_rows": asr_rows,
        "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
        "attacks": scan.attack_config.get("attacks", []),
    }


# --------------------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------------------

def render_html(scan: Scan) -> str:
    d = _report_data(scan)
    score = d["score"]
    grade = score.grade if score else "—"
    final = f"{score.final_score:.1f}" if score else "—"

    findings_html = "\n".join(
        f"""
        <article class="finding">
          <div class="finding-index">{i:02d}</div>
          <div class="finding-body">
            <h3>{escape(f.attack.upper())} <span class="sev sev-{escape(f.severity)}">{escape(f.severity)}</span></h3>
            <dl>
              <div><dt>ATLAS tactic</dt><dd>{escape(f.atlas_tactic)}</dd></div>
              <div><dt>ATLAS technique</dt><dd>{escape(f.atlas_technique)}</dd></div>
              <div><dt>OWASP ML Top 10</dt><dd>{escape(f.owasp_ref or "—")}</dd></div>
              <div><dt>NIST AI RMF</dt><dd>{escape(f.nist_ref or "—")}</dd></div>
              <div><dt>Evidence</dt><dd>{escape(", ".join(f"{k}={v}" for k, v in (f.evidence or {}).items()) or "—")}</dd></div>
            </dl>
            <p class="mitigation">{escape(f.mitigation)}</p>
          </div>
        </article>"""
        for i, f in enumerate(d["findings"], start=1)
    )

    component_html = "".join(
        f"<tr><td>{escape(k)}</td><td>{v:.3f}</td><td>{score.weights.get(k, 0):.2f}</td></tr>"
        for k, v in (score.component_scores.items() if score else [])
    )
    asr_html = "".join(
        f"<tr><td>{escape(name)}</td><td>{value:.2f}</td></tr>" for name, value in d["asr_rows"]
    )

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Robustness report — {escape(d["model"].name)}</title>
<link rel="preconnect" href="https://api.fontshare.com">
<link href="https://api.fontshare.com/v2/css?f[]=general-sans@600,700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{ --paper:#FAFAF8; --ink:#141210; --muted:#6B655D; --rule:#DAD5CB; --accent:#B4361E; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
         font-family:"Inter Tight",-apple-system,Segoe UI,sans-serif; line-height:1.55; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:64px 32px 96px; }}
  .eyebrow {{ font-size:11px; letter-spacing:.18em; text-transform:uppercase; color:var(--muted); }}
  h1 {{ font-family:"General Sans","Inter Tight",sans-serif; font-weight:700; font-size:clamp(40px,7vw,76px);
        line-height:.95; letter-spacing:-.03em; margin:12px 0 24px; text-transform:uppercase; }}
  h2 {{ font-family:"General Sans","Inter Tight",sans-serif; font-weight:600; font-size:clamp(24px,3vw,34px);
        letter-spacing:-.02em; margin:0 0 20px; text-transform:uppercase; }}
  .section {{ border-top:1px solid var(--rule); padding-top:28px; margin-top:56px;
              display:grid; grid-template-columns:120px 1fr; gap:24px; }}
  .section > .num {{ font-size:11px; letter-spacing:.18em; color:var(--muted); padding-top:6px; }}
  .grade {{ display:flex; align-items:flex-end; gap:32px; flex-wrap:wrap; }}
  .grade .letter {{ font-family:"General Sans",sans-serif; font-size:132px; line-height:.8; font-weight:700; color:var(--accent); }}
  .grade .num-score {{ font-size:44px; font-weight:600; letter-spacing:-.02em; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; margin-top:8px; }}
  th, td {{ text-align:left; padding:10px 8px; border-bottom:1px solid var(--rule); }}
  th {{ font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); font-weight:500; }}
  .finding {{ display:grid; grid-template-columns:56px 1fr; gap:20px; padding:26px 0; border-bottom:1px solid var(--rule); }}
  .finding-index {{ font-size:12px; color:var(--muted); padding-top:6px; }}
  .finding h3 {{ font-family:"General Sans",sans-serif; margin:0 0 12px; font-size:22px; letter-spacing:-.01em; }}
  .sev {{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; border:1px solid var(--rule);
          padding:3px 8px; margin-left:10px; vertical-align:middle; }}
  .sev-high, .sev-critical {{ color:var(--accent); border-color:var(--accent); }}
  dl {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:10px 24px; margin:0 0 14px; }}
  dt {{ font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }}
  dd {{ margin:2px 0 0; font-size:14px; }}
  .mitigation {{ margin:0; padding-left:14px; border-left:2px solid var(--accent); font-size:15px; }}
  footer {{ margin-top:72px; font-size:12px; color:var(--muted); border-top:1px solid var(--rule); padding-top:20px; }}
  @media print {{ .section {{ break-inside:avoid; }} .finding {{ break-inside:avoid; }} }}
</style></head>
<body><div class="wrap">
  <p class="eyebrow">Adversarial ML Red-Teaming Platform · Compliance report</p>
  <h1>Robustness<br>assessment</h1>
  <p style="max-width:62ch; font-size:16px; color:var(--muted);">{escape(REPORT_INTRO)}</p>

  <section class="section"><div class="num">01 / TARGET</div><div>
    <h2>Target</h2>
    <table>
      <tr><th>Model</th><td>{escape(d["model"].name)} (v{escape(d["model"].version)})</td></tr>
      <tr><th>Type</th><td>{escape(d["model"].model_type)}</td></tr>
      <tr><th>SHA-256</th><td style="font-family:monospace;font-size:12px">{escape(d["model"].checksum_sha256 or "—")}</td></tr>
      <tr><th>Scan ID</th><td style="font-family:monospace;font-size:12px">{scan.id}</td></tr>
      <tr><th>Threat model</th><td>{escape(scan.threat_model)}</td></tr>
      <tr><th>Attacks</th><td>{escape(", ".join(d["attacks"]) or "—")}</td></tr>
      <tr><th>Clean accuracy</th><td>{d["raw"].get("clean_accuracy", "—")}</td></tr>
    </table>
  </div></section>

  <section class="section"><div class="num">02 / SCORE</div><div>
    <h2>Robustness score</h2>
    <div class="grade">
      <div class="letter">{escape(grade)}</div>
      <div><div class="num-score">{final}<span style="font-size:18px;color:var(--muted)"> / 100</span></div>
      <div class="eyebrow">Weighted across components</div></div>
    </div>
    <table><thead><tr><th>Component</th><th>Badness (0–1)</th><th>Weight</th></tr></thead>
    <tbody>{component_html or '<tr><td colspan="3">No score recorded.</td></tr>'}</tbody></table>
  </div></section>

  <section class="section"><div class="num">03 / ATTACKS</div><div>
    <h2>Attack outcomes</h2>
    <table><thead><tr><th>Attack</th><th>ASR / accuracy drop</th></tr></thead>
    <tbody>{asr_html or '<tr><td colspan="2">No attack results recorded.</td></tr>'}</tbody></table>
  </div></section>

  <section class="section"><div class="num">04 / FINDINGS</div><div>
    <h2>Findings &amp; mitigations</h2>
    {findings_html or "<p>No findings recorded for this scan.</p>"}
  </div></section>

  <footer>Generated {escape(d["generated_at"])} · Scan {scan.id} ·
  Findings mapped to MITRE ATLAS, OWASP ML Top 10 and NIST AI RMF.</footer>
</div></body></html>"""


# --------------------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------------------

def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "eyebrow", parent=base["Normal"], fontName="Helvetica", fontSize=8,
            textColor=MUTED, leading=12, spaceAfter=6,
        ),
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=34,
            leading=34, textColor=INK, alignment=TA_LEFT, spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=15,
            leading=18, textColor=INK, spaceBefore=18, spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
            leading=14, textColor=INK,
        ),
        "muted": ParagraphStyle(
            "muted", parent=base["Normal"], fontName="Helvetica", fontSize=9,
            leading=13, textColor=MUTED,
        ),
        "grade": ParagraphStyle(
            "grade", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=56,
            leading=56, textColor=ACCENT,
        ),
    }


def _kv_table(rows: list[tuple[str, str]], width: float) -> Table:
    table = Table([[k, v] for k, v in rows], colWidths=[width * 0.3, width * 0.7])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("TEXTCOLOR", (1, 0), (1, -1), INK),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _page_furniture(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], stroke=0, fill=1)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(20 * mm, 12 * mm, "ADVERSARIAL ML RED-TEAMING PLATFORM — COMPLIANCE REPORT")
    canvas.drawRightString(doc.pagesize[0] - 20 * mm, 12 * mm, f"PAGE {doc.page:02d}")
    canvas.setStrokeColor(RULE)
    canvas.line(20 * mm, 16 * mm, doc.pagesize[0] - 20 * mm, 16 * mm)
    canvas.restoreState()


def render_pdf(scan: Scan) -> bytes:
    d = _report_data(scan)
    st = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=24 * mm,
        title=f"Robustness report — {d['model'].name}", author="Adversarial ML Red-Teaming Platform",
    )
    width = doc.width
    score = d["score"]
    story: list[Any] = [
        Paragraph("COMPLIANCE REPORT", st["eyebrow"]),
        Paragraph("ROBUSTNESS<br/>ASSESSMENT", st["title"]),
        Paragraph(REPORT_INTRO, st["muted"]),
        Spacer(1, 14),
        Paragraph("01 / TARGET", st["eyebrow"]),
        Paragraph("Target", st["h2"]),
        _kv_table(
            [
                ("Model", f"{d['model'].name} (v{d['model'].version})"),
                ("Type", d["model"].model_type),
                ("SHA-256", (d["model"].checksum_sha256 or "—")[:32] + "…"),
                ("Scan ID", str(scan.id)),
                ("Threat model", scan.threat_model),
                ("Attacks", ", ".join(d["attacks"]) or "—"),
                ("Clean accuracy", str(d["raw"].get("clean_accuracy", "—"))),
                ("Generated", d["generated_at"]),
            ],
            width,
        ),
        Spacer(1, 10),
        Paragraph("02 / SCORE", st["eyebrow"]),
        Paragraph("Robustness score", st["h2"]),
    ]

    if score is not None:
        grade_table = Table(
            [[Paragraph(score.grade, st["grade"]),
              Paragraph(f"<b>{score.final_score:.1f}</b> / 100 weighted robustness score",
                        st["body"])]],
            colWidths=[width * 0.25, width * 0.75],
        )
        grade_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(grade_table)
        comp_rows = [["COMPONENT", "BADNESS (0–1)", "WEIGHT"]] + [
            [k, f"{v:.3f}", f"{score.weights.get(k, 0):.2f}"]
            for k, v in score.component_scores.items()
        ]
        comp = Table(comp_rows, colWidths=[width * 0.4, width * 0.3, width * 0.3])
        comp.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story += [Spacer(1, 8), comp]
    else:
        story.append(Paragraph("No score recorded for this scan.", st["body"]))

    story += [
        Spacer(1, 12),
        Paragraph("03 / ATTACKS", st["eyebrow"]),
        Paragraph("Attack outcomes", st["h2"]),
    ]
    attack_rows = [["ATTACK", "ASR / ACCURACY DROP"]] + [
        [name, f"{value:.2f}"] for name, value in d["asr_rows"]
    ]
    if len(attack_rows) == 1:
        attack_rows.append(["—", "—"])
    attacks = Table(attack_rows, colWidths=[width * 0.6, width * 0.4])
    attacks.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story += [attacks, PageBreak(), Paragraph("04 / FINDINGS", st["eyebrow"]),
              Paragraph("Findings & mitigations", st["h2"])]

    if not d["findings"]:
        story.append(Paragraph("No findings recorded for this scan.", st["body"]))
    for i, f in enumerate(d["findings"], start=1):
        evidence = ", ".join(f"{k}={v}" for k, v in (f.evidence or {}).items()) or "—"
        block = [
            Paragraph(f"{i:02d} — {f.attack.upper()} · {f.severity.upper()}", st["h2"]),
            _kv_table(
                [
                    ("ATLAS tactic", f.atlas_tactic),
                    ("ATLAS technique", f.atlas_technique),
                    ("OWASP ML Top 10", f.owasp_ref or "—"),
                    ("NIST AI RMF", f.nist_ref or "—"),
                    ("Evidence", evidence),
                ],
                width,
            ),
            Spacer(1, 6),
            Paragraph(f"<b>Mitigation.</b> {f.mitigation}", st["body"]),
            Spacer(1, 14),
        ]
        story.append(KeepTogether(block))

    doc.build(story, onFirstPage=_page_furniture, onLaterPages=_page_furniture)
    return buffer.getvalue()
