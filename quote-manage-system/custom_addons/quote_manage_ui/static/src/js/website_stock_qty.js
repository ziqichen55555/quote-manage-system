/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_sale/js/website_sale";

publicWidget.registry.WebsiteSale.include({
    /**
     * Keep "Stock on hand" in sync with the selected configuration.
     * @override
     */
    _onChangeCombination(ev, $parent, combination) {
        this._super(...arguments);
        const qtyEl = document.querySelector(".rw-stock-on-hand-qty");
        if (!qtyEl || combination.product_type !== "product") {
            return;
        }
        if (combination.free_qty === undefined) {
            return;
        }
        const qty = Math.max(0, combination.free_qty);
        qtyEl.textContent = Number.isInteger(qty) ? String(qty) : String(Math.floor(qty));
    },
});
