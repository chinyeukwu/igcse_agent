<!-- SEED: re-run /impeccable document once there's code to capture the actual tokens and components. -->

---
name: Agentic AI Tutor Design System
description: Inviting, energetic learning workspace with rich green, burnt gold, and black palette
colors:
  primary-green: "oklch(0.48 0.16 140)"
  accent-gold: "oklch(0.56 0.13 60)"
  neutral-black: "oklch(0.08 0.0 0)"
  surface-light: "oklch(0.97 0.0 0)"
  surface-dark: "oklch(0.15 0.0 0)"
  text-muted: "oklch(0.55 0.0 0)"
  border: "oklch(0.88 0.0 0)"
typography:
  display:
    fontFamily: "[Modern sans-serif to be chosen at implementation]"
    fontWeight: 700
    fontSize: "clamp(2rem, 5vw, 3.5rem)"
    lineHeight: 1.1
  headline:
    fontFamily: "[Modern sans-serif, same family]"
    fontWeight: 600
    fontSize: "clamp(1.5rem, 4vw, 2.25rem)"
    lineHeight: 1.2
  body:
    fontFamily: "[Modern sans-serif, same family]"
    fontWeight: 400
    fontSize: "16px"
    lineHeight: 1.6
  label:
    fontFamily: "[Modern sans-serif, same family]"
    fontWeight: 500
    fontSize: "14px"
    letterSpacing: "0.02em"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
---

# Design System: Agentic AI Tutor

## 1. Overview

**Creative North Star: "The Learning Workshop"**

A warm, confident space where students feel supported but never patronized. The rich green grounds the space in growth and calm; burnt gold brings warmth and sophistication. Together they signal "thoughtful education," not corporate or clinical. Motion is responsive and immediate—students feel heard when they type. The interface stays out of the way: clean, focused, one task per screen. Typography is modern, generous, and dyslexia-friendly. Accessibility is woven in from the start: high contrast, large touch targets, mobile-first, no decoration that gets in the way.

This system explicitly rejects gamified cartoonery (no badges, no stars), corporate sterility (no cold blues, no jargon), cluttered dashboards (one question at a time), and outdated web design (no bevels, no tiny fonts).

**Key Characteristics:**
- Warm and inviting without being precious
- Focused and distraction-free
- Responsive, immediate feedback
- Mobile-first and accessible by default
- Energetic but not frenetic

---

## 2. Colors: The Inviting Palette

Three named colors carry the entire system. Their restraint is the point: color is used intentionally, never decoratively.

### Primary
- **Rich Learning Green** ([oklch to be resolved]): The foundation. Used on primary actions (quiz start, submit answer), section headings, and the chat interface highlight. Signals growth, calm, safety. Never more than 20% of any screen.

### Secondary
- **Burnt Gold Accent** ([oklch to be resolved]): Warmth and sophistication. Used on secondary actions, loading states, success messages, and callouts. Creates visual rhythm with the green. Never competes for primary attention.

### Neutral
- **Charcoal Ink** ([oklch to be resolved]): Body text, structural elements, borders. High contrast for readability (4.5:1+). The backbone of the system.
- **Surface Light** ([oklch to be resolved]): Card backgrounds, input fields, subtle dividers. Cream/off-white, not warm-tinted. Dyslexia-friendly: clean background, not colored paper effect.
- **Border Muted** ([oklch to be resolved]): Dividers between sections, input borders at rest. Restrained; never stronger than 1px.

### Named Rules

**The Restraint Rule.** Primary green appears on ≤20% of any screen. Its rarity makes it powerful. If the page looks "green," the color strategy has failed.

**The One Accent Rule.** Burnt gold is used for secondary actions and highlights, never as a background wash. Never pair green and gold on the same element without clear hierarchy.

**The Contrast Rule.** All body text and interactive elements hit ≥4.5:1 contrast against their background. Placeholder text uses the same threshold, not gray. No "elegant" pale text; readability wins.

---

## 3. Typography: Modern, Readable, Accessible

**Display Font:** [Modern sans-serif, generous letterforms, high legibility—to be chosen at implementation. Examples: Inter, Outfit, DM Sans]  
**Body Font:** Same family as display, multiple weights for hierarchy  
**Mono Font:** [System monospace or Courier, for code/data snippets if needed]

**Character:** Single modern sans throughout. Warm and human, not sterile or techie. Generous spacing and weight variation create hierarchy without size alone. Dyslexia-friendly: no serifs, open letterforms, tall x-height, clear lowercase/uppercase distinction.

### Hierarchy
- **Display** (700, clamp(2rem, 5vw, 3.5rem), 1.1): Hero sections, page headers. Only on the most important screens (quiz start, dashboard hero).
- **Headline** (600, clamp(1.5rem, 4vw, 2.25rem), 1.2): Section headers, question prompt in quiz, card titles. Grouped with the action they describe.
- **Title** (600, 18px, 1.3): Smaller section headers, input labels, sidebar nav items.
- **Body** (400, 16px, 1.6, max 65–75ch): Main reading text. Questions, explanations, feedback. Generous line-height supports dyslexia and mobile reading. Line-length capped at 65–75 characters for comfort.
- **Label** (500, 14px, 0.02em): Button text, field labels, breadcrumbs, helper text. Uppercase only when it's truly a label (input description); never uppercase for body text.

### Named Rules

**The Generosity Rule.** Line-height is never below 1.5 for body text; 1.6+ is default. Letter-spacing in display is ≥-0.02em (no cramped headlines). Margins between sections are ≥2.25rem. Dyslexia support and mobile reading win over compact layouts.

**The Weight Rule.** Weight variation carries hierarchy, not size alone. Display uses 700; headline uses 600; body is 400. No font weights between these steps; the scale is intentional.

---

## 4. Elevation

This system is **flat by default with tonal layering for depth**. No drop shadows. Depth is conveyed via:
- Background color shifts (cards use surface-light, containers use white)
- Subtle border (1px, muted color) to separate layers
- Responsive motion: buttons scale on hover, cards lift slightly on interaction

**Why:** Shadow-based elevation feels heavy and corporate. Tonal layering feels modern, accessible, and keeps the interface light. Motion provides the feedback students expect when they interact.

### Named Rules

**The Flat-By-Default Rule.** Surfaces are flat at rest. Shadows never appear. Depth is tonal (color shift) or responsive (on interaction via motion).

**The Motion Rule.** Interactions get immediate response: button scale (2-4% grow), loading spinner, toast notification. Motion supports feeling heard, not decorative.

---

## 5. Components

### Buttons
- **Shape:** Rounded corners (8px). Min height 48px for mobile touch targets.
- **Primary:** Rich green background (oklch(0.48 0.16 140)), white text, 2% scale on hover, 3px focus ring in burnt gold.
- **Secondary:** Surface background with 1px border, dark text, similar hover/focus treatment.
- **Ghost:** Transparent background with border, primary green text.

### Cards & Progress
- **Progress Cards:** Surface background, 1px border, hover state raises card 4px. Contains subject name, progress bar (8px height), percentage label.
- **Progress Bar:** Fixed-height container with green fill. No animation (prevents layout thrash). Communicates mastery level visually.
- **Quiz List Items:** Flex layout with quiz title, metadata, score badge, and trend indicator (↑ success, ↓ decline).

### Score Badges
- **Style:** Rich green background, white text, 60px min-width, centered, 4px radius.
- **Trend Indicators:** Success (green, ↑), Decline (red, ↓). Semantic color use; no color-only meaning.

### Stat Cards
- **Style:** Centered text, large green value, small muted label in uppercase. Grid layout responsive to 1fr on mobile.

### Recommendations
- **Style:** Surface background with 2px top border in burnt gold (subtle accent, not side-stripe). Contains title, description, CTA button.

### Input Controls & Navigation
- **Theme Toggle:** 48px button, border style, icon toggle (🌙/☀️), hover green border.
- **Modal Dialog:** Fixed positioning, rgba backdrop, content centered, close button top-right, 500px max-width responsive to 90vw.

### Responsive Behavior
- **Mobile (<768px):** Header stacks vertically. Progress/stats grid collapses to 1fr. Quiz items flex vertically.

---

## 6. Do's and Don'ts

### Do:
- **Do** use rich green sparingly on primary actions (submit quiz, start lesson, ask AI). ≤20% of the screen.
- **Do** use burnt gold for secondary actions, progress indicators, and success messages.
- **Do** ensure all text hits ≥4.5:1 contrast. No pale gray on light backgrounds.
- **Do** set body text to 16px+, line-height 1.6+, max-width 65–75ch. Dyslexia-friendly defaults.
- **Do** make buttons large (≥48px tall) for mobile and fat-thumb use. Spacing around them is ≥8px.
- **Do** use responsive motion: button hover = 2% scale, loading spinner = smooth rotation, transitions ≤300ms. Always provide a `@media (prefers-reduced-motion: reduce)` alternative (instant state change, no animation).
- **Do** stack elements vertically on mobile (<640px). One task per screen. No sidebars.
- **Do** provide high-contrast focus rings on interactive elements (2px, primary green). Keyboard navigation must be visible.

### Don't:
- **Don't** use gamified elements: no badges, stars, level indicators, achievement popups. Learning is serious; avoid trivializing mechanics.
- **Don't** use corporate colors or jargon: avoid navy + gold combinations, avoid "enterprise" language, avoid SaaS clichés (gradient overlays, thin sans-serif hero text, stock photography).
- **Don't** clutter the screen. One question per screen. No competing calls-to-action. If the page feels crowded, simplify.
- **Don't** use dated design patterns: no 2000s bevels, no skeuomorphism, no outdated icon styles. The interface should feel current, not retro or nostalgic.
- **Don't** pair rich green and burnt gold on the same element without hierarchy (e.g., green button with gold text). One or the other; green is dominant.
- **Don't** use color alone to convey meaning. Pair green with a checkmark (success), gold with a warning icon, red with an X (error).
- **Don't** create text that overflows its container. Test headlines at every breakpoint. If text wraps awkwardly, rewrite or reduce size.
- **Don't** use rounded corners >12px; they feel childish. Keep corners subtle (4–8px).
- **Don't** use animations that distract from content. Motion is responsive feedback, not choreographed sequences. Entrance animations should be fast (<300ms) and only on user action.
- **Don't** forget reduced motion. Every animation must have a `@media (prefers-reduced-motion: reduce)` rule that removes it or replaces it with an instant state change.
