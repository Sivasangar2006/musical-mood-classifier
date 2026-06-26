# MoodWave — Design System

A flat, editorial, light interface. Solid surfaces, hairline borders, one warm
signature accent, and mood colours used strictly as data. No gradients, no
glassmorphism, no decorative background. Motion is purposeful (framer-motion),
not decorative.

## Direction
- **Purpose:** a tool people return to — read a song's emotion, then explore.
- **Tone:** quiet, scannable, hand-made. Reads as a considered product, not a
  templated generator.
- **Memorable detail:** the valence/arousal circumplex — the song's point springs
  out from the centre into place, with nearby recommendations fading in around it.

## Typography
- **Display / headings:** `Space Grotesk` (500–700)
- **Body / UI:** `Inter` (400–700)
- Import: `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap`

## Color tokens
| Role | Hex |
|------|-----|
| Paper (bg) | `#F6F4EF` |
| Card | `#FFFFFF` |
| Ink (text) | `#1A1A1A` |
| Ink-soft | `#6B6B6B` |
| Ink-faint | `#9A9A95` |
| Line | `#E5E3DD` |
| Line-strong | `#D6D3CB` |
| Accent (clay) | `#C2553A` |
| Accent dark | `#A8442C` |
| Accent wash | `#F7E9E3` |

## Mood colours (data only, tuned for contrast on white)
Happy `#C98A12` · Energetic `#D6294B` · Angry `#7E3CC0` · Sad `#2563EB` · Relaxed `#0E8C63`

## Elevation
Neutral, subtle shadows only — `shadow-card` / `shadow-lift` / `shadow-pop`. No
coloured glows, no blur/glass.

## Motion (framer-motion)
- Section reveals on scroll (`whileInView`, subtle y + opacity).
- Search/popover and history slide-over via `AnimatePresence`.
- Result card spring entrance; circumplex point spring-to-position; confidence bar fill.
- Hover micro-interactions on rows and the search arrow.
- `prefers-reduced-motion` honoured globally (index.css).

## Guardrails
- [x] No gradients, no glassmorphism, no background blobs.
- [x] No library / tech-stack names surfaced in the UI.
- [x] SVG icons (Lucide), never emoji-as-icon.
- [x] `cursor-pointer` on all clickable elements; visible focus ring (clay).
- [x] Text contrast ≥ 4.5:1 on paper/card.
- [x] Responsive at 375 / 768 / 1024 / 1440 px.
