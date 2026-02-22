# Minecraft Heart Sprites & Animations

This directory contains Minecraft-style heart sprites and animations for displaying health in your Minecraft Agents Dashboard.

## Files

- **`full.png`** - Full heart sprite (9x9 pixels)
- **`half.png`** - Half heart sprite (9x9 pixels)
- **`empty.png`** - Empty/container heart sprite (9x9 pixels)
- **`hearts_sprite_sheet.png`** - All three variants in one sprite sheet (27x9 pixels)
- **`heart_example.html`** - Example HTML file showing all features
- **`hearts.js`** - JavaScript module for easy integration

## Quick Start

### Method 1: Individual Images

```html
<div class="heart full"></div>
<div class="heart half"></div>
<div class="heart empty"></div>
```

```css
.heart {
    width: 18px;
    height: 18px;
    image-rendering: pixelated;
    display: inline-block;
}

.heart.full { background-image: url('full.png'); background-size: contain; }
.heart.half { background-image: url('half.png'); background-size: contain; }
.heart.empty { background-image: url('empty.png'); background-size: contain; }
```

### Method 2: Sprite Sheet (More Efficient)

```html
<div class="heart-sprite full"></div>
<div class="heart-sprite half"></div>
<div class="heart-sprite empty"></div>
```

```css
.heart-sprite {
    width: 18px;
    height: 18px;
    background-image: url('hearts_sprite_sheet.png');
    background-size: 54px 18px;
    image-rendering: pixelated;
    display: inline-block;
}

.heart-sprite.full { background-position: 0 0; }
.heart-sprite.half { background-position: -18px 0; }
.heart-sprite.empty { background-position: -36px 0; }
```

### Method 3: JavaScript Module

```javascript
import { renderHearts } from './hearts.js';

const container = document.getElementById('health-bar');
renderHearts(container, 15, 20); // 15/20 health = 7.5 hearts
```

## Animations

### Blinking (Low Health Warning)
```css
@keyframes heartBlink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

.heart.blinking {
    animation: heartBlink 0.5s ease-in-out infinite;
}
```

### Pulsing (Health Regeneration)
```css
@keyframes heartPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.2); }
}

.heart.pulsing {
    animation: heartPulse 1s ease-in-out infinite;
}
```

### Damage Animation
```css
@keyframes heartDamage {
    0% { transform: scale(1); opacity: 1; }
    25% { transform: scale(1.3) rotate(-5deg); opacity: 0.8; }
    50% { transform: scale(0.9) rotate(5deg); opacity: 0.6; }
    75% { transform: scale(1.1) rotate(-3deg); opacity: 0.7; }
    100% { transform: scale(1); opacity: 1; }
}

.heart.damaged {
    animation: heartDamage 0.4s ease-in-out;
}
```

## Integration Example

See `heart_example.html` for a complete working example with all features.

## Notes

- Hearts are 9x9 pixels (scaled to 18x18px for better visibility)
- Use `image-rendering: pixelated` to maintain crisp pixel art
- Default Minecraft health is 20 (10 hearts)
- Each heart represents 2 health points
