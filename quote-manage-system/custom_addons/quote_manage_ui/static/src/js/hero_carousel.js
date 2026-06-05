/** @odoo-module **/

/**
 * Re-Ware hero carousel — public-site driver + crash guard.
 *
 * Two problems this solves:
 *
 * 1. Bootstrap's Carousel._setActiveIndicatorElement() throws
 *    "Cannot read properties of null (reading 'classList')" when, at slide
 *    time, the .carousel-indicators block has no `.active` child or the
 *    indicator count is out of sync with the slides. Odoo's editor also
 *    strips `data-bs-slide-to` from indicators in edit mode, which makes a
 *    natively auto-riding carousel crash. So the snippet no longer sets
 *    `data-bs-ride="carousel"`.
 *
 * 2. Without `data-bs-ride`, the carousel no longer autoplays. We start the
 *    cycle ourselves on the PUBLIC site only (never in the Website Builder,
 *    where Odoo pauses carousels and manages slides manually).
 *
 * Before starting, we rebuild the indicators to exactly match the slides and
 * guarantee a single active slide/indicator, so Bootstrap can never read a
 * null indicator.
 */

function isEditMode() {
    // Website Builder adds `editor_enable` to <body> (and the page runs inside
    // the editor iframe). Never drive autoplay there — let Odoo handle it.
    return !!(
        document.body &&
        (document.body.classList.contains("editor_enable") ||
            document.body.classList.contains("editor_has_snippets"))
    );
}

function normaliseCarousel(carousel) {
    const inner = carousel.querySelector(".carousel-inner");
    const items = Array.from(carousel.querySelectorAll(".carousel-item"));
    if (!inner || !items.length) {
        return -1;
    }

    // Exactly one active slide (keep the first active, else default to first).
    const activeItems = items.filter((el) => el.classList.contains("active"));
    if (activeItems.length === 0) {
        items[0].classList.add("active");
    } else if (activeItems.length > 1) {
        activeItems.slice(1).forEach((el) => el.classList.remove("active"));
    }
    const activeIndex = Math.max(
        0,
        items.findIndex((el) => el.classList.contains("active"))
    );

    // Rebuild indicators to match the slide count exactly.
    const indicators = carousel.querySelector(".carousel-indicators");
    if (indicators) {
        const carouselId = carousel.getAttribute("id");
        indicators.innerHTML = "";
        items.forEach((_item, i) => {
            const li = document.createElement("li");
            if (carouselId) {
                li.setAttribute("data-bs-target", "#" + carouselId);
            }
            li.setAttribute("data-bs-slide-to", String(i));
            if (i === activeIndex) {
                li.classList.add("active");
                li.setAttribute("aria-current", "true");
            }
            indicators.appendChild(li);
        });
    }
    return activeIndex;
}

function startAutoplay(carousel) {
    const jq = window.jQuery || window.$;
    if (!jq || typeof jq.fn.carousel !== "function") {
        return; // bootstrap jQuery bridge unavailable; carousel stays manual
    }
    const interval = parseInt(carousel.getAttribute("data-bs-interval"), 10);
    jq(carousel).carousel({
        interval: Number.isFinite(interval) && interval > 0 ? interval : 4000,
        ride: "carousel",
        pause: "hover",
    });
}

function initHeroCarousels(root) {
    if (isEditMode()) {
        return;
    }
    const scope = root || document;
    scope
        .querySelectorAll("#rwHeroCarousel, .s_rw_hero .carousel")
        .forEach((carousel) => {
            normaliseCarousel(carousel);
            startAutoplay(carousel);
        });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => initHeroCarousels());
} else {
    initHeroCarousels();
}
