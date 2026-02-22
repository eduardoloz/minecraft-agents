/**
 * Minecraft Heart Sprites - JavaScript Module
 * Easy integration for displaying health hearts
 */

/**
 * Render hearts based on health value
 * @param {HTMLElement} container - Container element to render hearts into
 * @param {number} health - Current health (0-20 default, or custom max)
 * @param {number} maxHealth - Maximum health (default: 20)
 * @param {Object} options - Configuration options
 * @param {string} options.method - 'individual' or 'sprite' (default: 'sprite')
 * @param {number} options.scale - Scale multiplier (default: 2, makes 9px hearts 18px)
 * @param {boolean} options.animateLowHealth - Blink hearts when health is low (default: true)
 * @param {number} options.lowHealthThreshold - Health threshold for low health warning (default: 6)
 */
export function renderHearts(container, health, maxHealth = 20, options = {}) {
    const {
        method = 'sprite',
        scale = 2,
        animateLowHealth = true,
        lowHealthThreshold = 6
    } = options;
    
    container.innerHTML = '';
    
    const totalHearts = maxHealth / 2; // Each heart = 2 health
    const fullHearts = Math.floor(health / 2);
    const halfHeart = health % 2 === 1;
    const emptyHearts = totalHearts - fullHearts - (halfHeart ? 1 : 0);
    
    const isLowHealth = health <= lowHealthThreshold;
    const baseClass = method === 'sprite' ? 'heart-sprite' : 'heart';
    const size = 9 * scale;
    
    // Full hearts
    for (let i = 0; i < fullHearts; i++) {
        const heart = document.createElement('div');
        heart.className = `${baseClass} full`;
        if (isLowHealth && animateLowHealth) {
            heart.classList.add('blinking');
        }
        heart.style.width = `${size}px`;
        heart.style.height = `${size}px`;
        container.appendChild(heart);
    }
    
    // Half heart
    if (halfHeart) {
        const heart = document.createElement('div');
        heart.className = `${baseClass} half`;
        if (isLowHealth && animateLowHealth) {
            heart.classList.add('blinking');
        }
        heart.style.width = `${size}px`;
        heart.style.height = `${size}px`;
        container.appendChild(heart);
    }
    
    // Empty hearts
    for (let i = 0; i < emptyHearts; i++) {
        const heart = document.createElement('div');
        heart.className = `${baseClass} empty`;
        heart.style.width = `${size}px`;
        heart.style.height = `${size}px`;
        container.appendChild(heart);
    }
}

/**
 * Animate damage on hearts
 * @param {HTMLElement} container - Container with hearts
 * @param {number} damageAmount - Amount of damage taken
 */
export function animateDamage(container, damageAmount) {
    const hearts = container.querySelectorAll('.heart.full, .heart-sprite.full');
    const heartsToAnimate = Math.min(Math.ceil(damageAmount / 2), hearts.length);
    
    for (let i = 0; i < heartsToAnimate; i++) {
        const heart = hearts[hearts.length - 1 - i];
        if (heart) {
            heart.classList.add('damaged');
            setTimeout(() => {
                heart.classList.remove('damaged');
            }, 400);
        }
    }
}

/**
 * Animate health regeneration
 * @param {HTMLElement} container - Container with hearts
 */
export function animateRegeneration(container) {
    const emptyHearts = container.querySelectorAll('.heart.empty, .heart-sprite.empty');
    if (emptyHearts.length > 0) {
        emptyHearts[0].classList.add('pulsing');
        setTimeout(() => {
            emptyHearts[0].classList.remove('pulsing');
        }, 1000);
    }
}

/**
 * Update health display with animation
 * @param {HTMLElement} container - Container element
 * @param {number} oldHealth - Previous health value
 * @param {number} newHealth - New health value
 * @param {number} maxHealth - Maximum health
 * @param {Object} options - Configuration options
 */
export function updateHealth(container, oldHealth, newHealth, maxHealth = 20, options = {}) {
    const damage = oldHealth - newHealth;
    
    if (damage > 0) {
        // Health decreased - animate damage
        animateDamage(container, damage);
        setTimeout(() => {
            renderHearts(container, newHealth, maxHealth, options);
        }, 200);
    } else if (damage < 0) {
        // Health increased - animate regeneration
        renderHearts(container, newHealth, maxHealth, options);
        animateRegeneration(container);
    } else {
        // No change
        renderHearts(container, newHealth, maxHealth, options);
    }
}

// Default export
export default {
    renderHearts,
    animateDamage,
    animateRegeneration,
    updateHealth
};
