---
name: beautiful-powerpoint
description: Design and create polished, presentation-ready PPTX decks with strong visual hierarchy, consistent layout systems, and mandatory visual QA.
trigger:
  - User asks to create, improve, beautify, polish, redesign, or send a PPT/PPTX/deck/slides/presentation
  - User asks for a business report, proposal, pitch deck, training deck, meeting slides, or WeChat-shareable PPT
  - User says the slides should look beautiful, professional, premium, modern, executive, or client-ready
---

# Beautiful PowerPoint Skill

Use this skill together with the built-in `productivity/powerpoint` skill whenever a presentation is created or edited.

## Goal

Deliver a PPTX that looks intentionally designed, not like default office output. The deck should have:

- A clear visual system: palette, typography, spacing, motif, slide rhythm.
- Strong hierarchy: title, key message, supporting detail, visual proof.
- At least one visual element per slide: chart, icon, diagram, image, table, timeline, process, callout, or branded shape.
- Consistent margins, spacing, footer/page numbers, and section treatment.
- A rendered visual QA pass before final delivery.

## Workflow

1. Clarify the audience and purpose if missing.
2. Draft a slide outline with one message per slide.
3. Pick a visual direction before writing code:
   - Executive: restrained, high-contrast, dense but readable.
   - Sales/pitch: energetic, benefit-forward, bold numbers and screenshots.
   - Training: calm, modular, clear examples and step flows.
   - Research/report: structured, evidence-heavy, charts and citations.
4. Build with the built-in PowerPoint tooling, preferably `pptxgenjs` or the existing PowerPoint skill scripts.
5. Render to PDF/images and inspect every slide.
6. Fix layout issues, then re-render changed slides.
7. Only finish after at least one visual QA pass.

## Design Rules

- Use 16:9 widescreen unless the user asks otherwise.
- Use 0.45-0.65 inch page margins.
- Do not put long paragraphs on slides. Convert prose into callouts, diagrams, timelines, or grouped cards.
- Prefer 3-5 bullets maximum per slide, 6-10 words each.
- Use one dominant color, one neutral background, and one accent. Avoid rainbow palettes.
- Use font size ranges:
  - Title: 34-44 pt
  - Section header: 22-28 pt
  - Body: 14-18 pt
  - Caption/source: 9-11 pt
- Keep title positions consistent across content slides.
- Avoid generic title + bullet layouts when a diagram, metric card, or comparison layout would work better.
- Do not use low-contrast gray text on light backgrounds.
- Do not place text over busy images without a solid overlay.
- Do not use decorative lines under every title. Use whitespace, blocks, or section markers instead.

## Slide Patterns

Choose patterns that match the content:

- Title slide: strong title, short subtitle, date/owner, subtle motif.
- Executive summary: 3-4 key takeaways as cards.
- Data slide: one chart plus one headline insight.
- Comparison: two or three columns with clear labels.
- Process: numbered horizontal or vertical flow.
- Roadmap: timeline with phases and milestones.
- Strategy: pyramid, flywheel, matrix, or decision tree.
- Case/example: screenshot or image with annotated callouts.
- Closing: recommendation, next steps, or decision request.

## Chinese Deck Defaults

For Chinese PPTs:

- Prefer Microsoft YaHei / SimHei / DengXian for Chinese text if available.
- Keep Chinese slide titles short and punchy.
- Avoid mixing too many Chinese font families.
- Use full-width punctuation consistently.

## QA Checklist

Before final delivery, check:

- No text overflow, clipping, or overlap.
- All slides have sufficient edge margins.
- Similar elements align across slides.
- Font sizes are readable on a projector.
- Colors are consistent and contrast is strong.
- Charts have labels and a clear takeaway.
- No placeholder text remains.
- File opens successfully in PowerPoint or LibreOffice.
- If sending through WeChat, keep the filename simple and include a short message explaining the attachment.

## Output Behavior

When finished, report:

- The created `.pptx` path.
- Whether visual QA/rendering was completed.
- Any known limitations, such as missing brand assets or unresolved source data.

