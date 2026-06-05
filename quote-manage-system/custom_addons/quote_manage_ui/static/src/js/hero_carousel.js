/** @odoo-module **/

/**
 * Re-Ware hero carousel — bypass Bootstrap auto-ride on the public site.
 *
 * Bootstrap's ``_setActiveIndicatorElement`` crashes when indicator ``.active``
 * is missing (common after Odoo editor saves or when slide/indicator counts
 * diverge). Odoo's stock ``.carousel`` public widget also initialises every
 * carousel and can fight with a second Bootstrap instance.
 *
 * This module:
 *   1. Skips the stock Odoo slider widget on ``#rwHeroCarousel``.
 *   2. Rebuilds indicators to match slide count, then autoplay via a simple
 *      active-class rotation (Bootstrap fade CSS still applies).
 *   3. Never uses ``data-bs-ride`` or ``ride: 'carousel'`` (those call
 *      ``nextWhenVisible`` and trigger the crash).
 */

import publicWidget from "@web/legacy/js/public/public_widget";

function isRwHeroCarousel(el) {
    return el && (el.id === "rwHeroCarousel" || !!el.closest(".s_rw_hero"));
}

function normaliseCarousel(carousel) {
    const items = Array.from(carousel.querySelectorAll(".carousel-item"));
    if (!items.length) {
        return 0;
    }

    let activeItems = items.filter((el) => el.classList.contains("active"));
    if (activeItems.length === 0) {
        items[0].classList.add("active");
    } else if (activeItems.length > 1) {
        activeItems.slice(1).forEach((el) => el.classList.remove("active"));
    }
    const activeIndex = Math.max(
        0,
        items.findIndex((el) => el.classList.contains("active"))
    );

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

function disposeBootstrapCarousel(carousel) {
    const jq = window.jQuery || window.$;
    if (!jq || typeof jq.fn.carousel !== "function") {
        return;
    }
    try {
        jq(carousel).carousel("pause");
    } catch (_e) {
        /* not initialised */
    }
    try {
        jq(carousel).carousel("dispose");
    } catch (_e) {
        /* BS5 dispose may be unavailable */
    }
    carousel.removeAttribute("data-bs-ride");
}

function advanceSlide(carousel) {
    const items = Array.from(carousel.querySelectorAll(".carousel-item"));
    const dots = Array.from(
        carousel.querySelectorAll(".carousel-indicators > li")
    );
    if (items.length < 2) {
        return;
    }
    let idx = items.findIndex((el) => el.classList.contains("active"));
    if (idx < 0) {
        idx = 0;
    }
    items[idx].classList.remove("active");
    if (dots[idx]) {
        dots[idx].classList.remove("active");
        dots[idx].removeAttribute("aria-current");
    }
    idx = (idx + 1) % items.length;
    items[idx].classList.add("active");
    if (dots[idx]) {
        dots[idx].classList.add("active");
        dots[idx].setAttribute("aria-current", "true");
    }
}

// Do not let Odoo's stock slider widget touch the hero (it starts Bootstrap
// cycle and breaks indicators in edit mode).
const StockSlider = publicWidget.registry.slider;

publicWidget.registry.slider = StockSlider.extend({
    start() {
        if (isRwHeroCarousel(this.el)) {
            return Promise.resolve();
        }
        return this._super(...arguments);
    },
});

publicWidget.registry.RwHeroCarousel = publicWidget.Widget.extend({
    selector: "#rwHeroCarousel, .s_rw_hero .carousel",

    start() {
        disposeBootstrapCarousel(this.el);
        normaliseCarousel(this.el);

        if (!this.editableMode) {
            const ms = parseInt(this.el.getAttribute("data-bs-interval"), 10);
            const interval = Number.isFinite(ms) && ms > 0 ? ms : 4000;
            this._rwTimer = setInterval(() => advanceSlide(this.el), interval);
        }
        return this._super(...arguments);
    },

    destroy() {
        if (this._rwTimer) {
            clearInterval(this._rwTimer);
            this._rwTimer = null;
        }
        return this._super(...arguments);
    },
});
