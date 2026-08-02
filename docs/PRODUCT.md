# Product

## Register

product

## Users

**Primary:** IGCSE students (ages 15–18) studying independently or supplementing classroom learning. They access the app on phones and desktop, often during study breaks or revision sessions. They want clear, quick answers without cognitive overhead—they're already focused on learning, not navigating a UI.

**Secondary:** Teachers and admins managing student progress, tracking quiz results, and curating quiz content. They need dashboards that surface insights at a glance.

## Product Purpose

Agentic AI Tutor is an intelligent tutoring system that helps IGCSE students master curriculum content through conversational AI and adaptive quizzes. Students ask questions in natural language; the AI responds with clear, subject-specific explanations. Teachers assess understanding via auto-generated quizzes that adapt to student performance. The system works online and offline, persisting progress across sessions.

**Success looks like:**
- Students feel supported and confident asking follow-up questions
- Revision is efficient: targeted quizzes catch knowledge gaps
- Teachers can spend time on pedagogy, not content creation
- The app feels like an expert tutor in their pocket, not a textbook

## Brand Personality

**Three words:** Smart, Supportive, Accessible

**Tone and voice:**
- Expert but not intimidating; confident without arrogance
- Encouraging; celebrates progress and reframes mistakes as learning
- Clear and direct; explains without over-simplifying
- Energetic and engaging; learning feels interactive, not dull

**Emotional goals:**
- **For students:** I feel capable. This tutor believes I can learn this.
- **For teachers:** I trust the insights. This app saves me time.

## Anti-references

**Explicitly NOT:**
- Gamified or cartoon-heavy (no stars, badges, game mechanics that trivialize learning)
- Corporate or sterile (not enterprise SaaS; not cold or transactional)
- Cluttered with competing information (not information-dense dashboards; clear focus per screen)
- Outdated or broken (not 2000s web design; not janky interactions)

## Design Principles

1. **Clarity over decoration.** Every pixel serves the student's learning goal. Visual hierarchy makes the question-answer flow obvious. Information is discoverable, not hidden.

2. **Inviting, not clinical.** Rich green, burnt gold, and black create warmth and sophistication. The palette signals "thoughtful learning space," not "corporate tool."

3. **Mobile is primary.** Most students study on phones. Responsive design is not an afterthought; it's the default. Fat thumbs, bad light, one-handed use—all assumed.

4. **Accessibility is built in.** WCAG 2.1 AA minimum. Dyslexia-friendly typography (generous line-height, clear letterforms, sans-serif). High contrast. No information conveyed by color alone.

5. **One job per screen.** Each page answers one question or accomplishes one task. No sidebar clutter. No decision paralysis.

6. **Energetic without frenetic.** Motion is purposeful (smooth transitions, micro-interactions that feel responsive). Reduced motion respected always.

## Accessibility & Inclusion

- **WCAG 2.1 AA** compliance required (keyboard navigation, screen reader support, color contrast ≥4.5:1 for body text)
- **Mobile-first design** for students learning on phones (responsive to 320px+)
- **Dyslexia support:** 
  - Body text: 16px+, sans-serif, line-height ≥1.5
  - Generous spacing; no justified text
  - Option to increase font size
- **Color blindness:** Never rely on color alone to convey meaning; pair with icons or labels
- **Reduced motion:** All animations have a `@media (prefers-reduced-motion: reduce)` alternative
- **Dark mode optional** but with the same rich color palette applied thoughtfully

## Visual Direction

**Color palette** (OKLCH):
- **Primary (Rich Green):** Deep, inviting green for key actions and headings. Signals growth, learning, growth. NOT a flat or neon green.
- **Accent (Burnt Gold):** Warm, earthy gold for highlights, secondary actions, and visual interest. Creates contrast with the green; signals warmth and sophistication.
- **Neutral (Black/Charcoal):** Dark ink for body text and structural elements. Ensures readability and hierarchy.
- **Surface & backgrounds:** Cream/off-white (high contrast, not warm-tinted by default).

**Typography:**
- Headings: Modern sans-serif with generous tracking. Confident, not cramped.
- Body: Generous line-height (≥1.5), wide margins for reading. Dyslexia-friendly.
- Monospace for code snippets, code blocks, or technical content (when applicable).

**Components and patterns:**
- Clear question/answer layout (student's question prominent, AI response well-spaced)
- Quiz interface: progress indicator, clear question, large tap targets, readable answer options
- Dashboard: cards or list patterns, not data tables (for mobile). Scannable; high contrast headers.
- Loading states and error recovery: explicit messages, retry buttons, no silent failures.

---

## Current State & Next Steps

The app currently uses Streamlit with basic styling. **Phase 1** of the redesign is to:
1. Migrate core pages (chatbot, student dashboard, quiz) to a custom HTML/CSS/JS frontend (or replace Streamlit with a modern web framework like SvelteKit or Next.js)
2. Implement the rich green / burnt gold / black palette
3. Audit for accessibility and dyslexia support
4. Optimize for mobile

**Design system generation:** Run `/impeccable document` once the first pages are built to extract and codify the visual system (tokens, components, spacing scale) for consistency.
