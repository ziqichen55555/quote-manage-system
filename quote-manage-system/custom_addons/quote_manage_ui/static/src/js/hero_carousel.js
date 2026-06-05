/** @odoo-module **/

/**
 * Re-Ware hero carousel — defensive active-state guard.
 *
 * Bootstrap's Carousel._setActiveIndicatorElement() throws
 *   "Cannot read properties of null (reading 'classList')"
 * when, at slide time, the .carousel-indicators block has no `.active`
 * child (or there is no active .carousel-item). This can happen if the
 * Website Builder saves the carousel mid-rotation, leaving the active
 * classes out of sync between the slides and their indicators.
 *
 * This runs on the public site (not the editor) and normalises the hero
 * carousel BEFORE Bootstrap's auto-ride fires its first slide:
 *   - exactly one .carousel-item.active (defaults to the first item);
 *   - exactly one active indicator, matching the active item's index.
 *
 * Plain DOM, no widget framework, so it also survives Builder DOM swaps.
 */

function normaliseCarousel(carousel) {
    const items = Array.from(carousel.querySelectorAll('.carousel-item'));
    if (!items.length) return;

    // 1. Exactly one active item (keep the first active, else the first item).
    let activeItems = items.filter((el) => el.classList.contains('active'));
    if (activeItems.length === 0) {
        items[0].classList.add('active');
    } else if (activeItems.length > 1) {
        activeItems.slice(1).forEach((el) => el.classList.remove('active'));
    }
    const activeIndex = items.findIndex((el) => el.classList.contains('active'));

    // 2. Indicators must have exactly one active, matching the active item.
    const indicators = carousel.querySelector('.carousel-indicators');
    if (!indicators) return;
    const dots = Array.from(indicators.children);
    if (!dots.length) return;
    dots.forEach((dot, i) => {
        const isActive = i === activeIndex;
        dot.classList.toggle('active', isActive);
        if (isActive) {
            dot.setAttribute('aria-current', 'true');
        } else {
            dot.removeAttribute('aria-current');
        }
    });
}

function guardHeroCarousels(root) {
    const scope = root || document;
    scope
        .querySelectorAll('#rwHeroCarousel, .s_rw_hero .carousel')
        .forEach(normaliseCarousel);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => guardHeroCarousels());
} else {
    guardHeroCarousels();
}

// Re-normalise after Odoo Website Builder swaps DOM (snippet drop / save).
document.addEventListener('content_changed', () => guardHeroCarousels());
