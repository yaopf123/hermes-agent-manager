---
name: beautiful-word-docx
description: Create polished, professional Word documents with strong typography, spacing, section hierarchy, cover pages, tables, and mandatory DOCX QA.
trigger:
  - User asks to create, improve, beautify, polish, redesign, or send a Word/DOCX/document/report/proposal/plan
  - User asks for a business report, proposal, contract draft, meeting minutes, operation guide, training handout, or WeChat-shareable Word file
  - User says the document should look beautiful, professional, formal, premium, modern, executive, or client-ready
---

# Beautiful Word DOCX Skill

Use this skill together with the built-in `productivity/word-docx` skill whenever a Word document is created or edited.

## Goal

Deliver a `.docx` that looks like a finished business document, not plain exported text. The document should have:

- A clean title page or strong opening block when appropriate.
- Consistent heading hierarchy.
- Readable typography and spacing.
- Professional tables, callouts, and numbered sections.
- Headers/footers or page numbers for longer documents.
- A final open/render/structure QA pass before delivery.

## Workflow

1. Identify document type:
   - Proposal
   - Report
   - Operating guide
   - Meeting minutes
   - Training material
   - Contract or formal memo
2. Decide a visual system:
   - Font pairing
   - Heading colors
   - Table style
   - Callout style
   - Page margins
3. Create the `.docx` using available tooling:
   - Prefer `python-docx` when available.
   - Use manual OOXML only when necessary.
   - Use LibreOffice for conversion/checking if available.
4. Add content structure:
   - Cover/title block
   - Table of contents for long docs if practical
   - Section headings
   - Tables or bullet summaries where useful
   - Appendix/source notes if needed
5. Run QA:
   - Open or inspect the DOCX.
   - Convert to PDF when possible and visually inspect.
   - Fix layout issues.

## Design Defaults

- Page size: A4 unless the user asks otherwise.
- Margins: 0.7-1.0 inch.
- Body font:
  - Chinese: Microsoft YaHei, DengXian, SimSun fallback.
  - English: Calibri, Aptos, Arial, or Georgia for formal reports.
- Body text: 10.5-11.5 pt.
- H1: 20-24 pt bold.
- H2: 15-17 pt bold.
- H3: 12-13 pt bold.
- Line spacing: 1.15-1.35.
- Paragraph spacing after: 4-8 pt.

## Layout Rules

- Use numbered headings for formal documents.
- Avoid giant walls of text. Break content into short paragraphs, tables, lists, and callout boxes.
- Use tables for comparisons, schedules, responsibilities, budgets, risks, or timelines.
- Keep table headers shaded and bold.
- Keep table cell padding readable.
- Use one accent color consistently for headings, table headers, and callouts.
- Avoid excessive borders. Prefer light gray lines and subtle shading.
- Use page breaks before major sections in long documents.
- Keep filenames simple and descriptive.

## Common Document Patterns

- Proposal:
  - Cover
  - Background
  - Objectives
  - Solution
  - Timeline
  - Budget/resources
  - Risks
  - Next steps
- Report:
  - Executive summary
  - Findings
  - Evidence/data
  - Analysis
  - Recommendations
  - Appendix
- Operating guide:
  - Purpose
  - Scope
  - Roles
  - Step-by-step procedures
  - Troubleshooting
  - Change log

## QA Checklist

Before final delivery, check:

- The DOCX opens without repair warnings.
- Headings are consistent.
- Tables fit within page margins.
- No orphaned heading at the bottom of a page.
- No placeholder text remains.
- Page breaks are sensible.
- Headers/footers do not collide with body content.
- Chinese and English fonts render cleanly.
- The final file path is clear.

## Output Behavior

When finished, report:

- The created `.docx` path.
- Whether render/open QA was completed.
- Any limitations, such as missing logos, signatures, or exact brand fonts.

