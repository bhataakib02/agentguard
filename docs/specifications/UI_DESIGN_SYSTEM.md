# AGENTGUARD UI Design System Specification

**Classification:** Official Frontend Design Tokens & Visual Guidelines  
**Target:** AGENTGUARD Enterprise Dashboard (`frontend/src`)  

---

## 1. Visual Philosophy & Design Direction

AGENTGUARD employs an enterprise-grade visual aesthetic characterized by clarity, trustworthiness, and executive polish:

1. **Clean Minimalist Foundations:** Off-white backgrounds (`#FAF9F5`), crisp white cards (`#FFFFFF`), and soft borders (`#EAEAE5`).
2. **Authoritative Editorial Typography:** Consistent usage of `Times New Roman` serif typography across headers, KPI figures, and navigation titles, imparting legal and institutional gravity.
3. **Intentional Semantic Color Hierarchy:** Deep green as the primary color of affirmative governance (`ALLOW`), amber for escalated human review (`REVIEW`), and red strictly reserved for policy refusal (`REFUSE`) or critical threats.
4. **Subtle Micro-Interactions:** Soft shadows, 12px/16px rounded borders, and smooth transitions without overwhelming animations or dark dashboard clutter.

---

## 2. Typography System

### 2.1 Primary Font Family
```css
font-family: "Times New Roman", Times, serif;
```

This font family is applied consistently across:
- Application layout titles and headers (`h1`, `h2`, `h3`, `h4`)
- Navigation brand marks and sidebar labels
- KPI summary numbers and metrics
- Decision outcome badges (`ALLOW`, `REVIEW`, `REFUSE`)
- Table headers and modal titles

### 2.2 Monospace Font Family
For code snippets, capability tokens, hashes, and raw tool payloads:
```css
font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
```

---

## 3. Color Palette & Token Hierarchy

### 3.1 Background & Neutral Tokens
- **Canvas Background:** `#FAF9F5` (Off-white / Warm Canvas)
- **Card Background:** `#FFFFFF` (Pure White)
- **Subtle Surface:** `#F5F5F0` (Muted panel fill)
- **Border Default:** `#EAEAE5` (Light border)
- **Border Focus / Hover:** `#D5D5CE`

### 3.2 Typography Tokens
- **Text Primary:** `#1A1A18` (High-contrast charcoal)
- **Text Secondary:** `#5A5A52` (Muted metadata and helper text)
- **Text Tertiary:** `#8C8C82` (Timestamps and disabled states)

### 3.3 Semantic Governance Colors
- **Affirmative / Primary Action (ALLOW):**
  - Dark Forest Green: `#1B4332`
  - Emerald Action Green: `#2D6A4F`
  - Mint Accent / Badge Fill: `#D8F3DC`
- **Escalation / Attention (REVIEW):**
  - Amber / Warning: `#D97706`
  - Warm Yellow Tint: `#FEF3C7`
- **Critical Interception / Threat (REFUSE):**
  - Crimson Red: `#DC2626`
  - Rose Tint: `#FEE2E2`
- **AI Intelligence & Copilot:**
  - Indigo / Violet: `#6366F1`
  - Lavender Tint: `#EEF2FF`

---

## 4. Component Standards

### 4.1 Governance Status Badges
Every decision and status indicator uses a standardized badge:
- `ALLOW`: Green border, `#D8F3DC` background, `#1B4332` text.
- `REVIEW`: Amber border, `#FEF3C7` background, `#92400E` text.
- `REFUSE`: Red border, `#FEE2E2` background, `#991B1B` text.

### 4.2 Cards and Containers
```css
border: 1px solid #EAEAE5;
border-radius: 12px;
background-color: #FFFFFF;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
```
