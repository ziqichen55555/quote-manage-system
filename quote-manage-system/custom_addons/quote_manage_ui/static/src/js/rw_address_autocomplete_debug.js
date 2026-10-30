/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";
import { renderToElement } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";

const LOG = "[Re-Ware address autocomplete]";
const RW_STREET_MIN_LEN = 3;

function rwLogPageCheck() {
    if (!window.location.pathname.includes("/shop/address")) {
        return;
    }
    const street = document.querySelector('input[name="street"]');
    console.info(`${LOG} page check`, {
        streetInput: Boolean(street),
        dataAutocompleteEnabled: street?.getAttribute("data-autocomplete-enabled"),
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", rwLogPageCheck);
} else {
    rwLogPageCheck();
}

import "@website_sale_autocomplete/js/address_form";

const AddressForm = publicWidget.registry.AddressForm;

if (!AddressForm) {
    console.warn(`${LOG} AddressForm widget not registered`);
} else {
    patch(AddressForm.prototype, {
        init() {
            const result = super.init(...arguments);
            this.street2Input = document.querySelector('input[name="street2"]');

            const self = this;
            this._onChangeStreet = debounce(function (ev) {
                const inputContainer = ev.currentTarget.parentNode;
                const partial = ev.currentTarget.value;
                self._hideAutocomplete(inputContainer);
                if (!partial.length) {
                    self.sessionId = self._generateUUID();
                    return;
                }
                if (partial.length < RW_STREET_MIN_LEN) {
                    return;
                }
                self.keepLast
                    .add(
                        self.rpc("/autocomplete/address", {
                            partial_address: partial,
                            session_id: self.sessionId || null,
                        })
                    )
                    .then((response) => {
                        self._hideAutocomplete(inputContainer);
                        inputContainer.appendChild(
                            renderToElement("website_sale_autocomplete.AutocompleteDropDown", {
                                results: response.results,
                            })
                        );
                        if (response.session_id) {
                            self.sessionId = response.session_id;
                        }
                    });
            }, 200);

            const rpc = this.rpc.bind(this);
            this.rpc = (route, params) => {
                if (route === "/autocomplete/address" || route === "/autocomplete/address_full") {
                    console.info(`${LOG} RPC →`, route, params);
                    return rpc(route, params)
                        .then((data) => {
                            console.info(`${LOG} RPC ←`, route, data);
                            if (data?.rw_debug) {
                                console.info(`${LOG} Google / Odoo debug`, data.rw_debug);
                            }
                            return data;
                        })
                        .catch((err) => {
                            console.error(`${LOG} RPC failed`, route, err);
                            throw err;
                        });
                }
                return rpc(route, params);
            };
            return result;
        },

        async _onClickAutocompleteResult(ev) {
            const dropDown = ev.currentTarget.parentNode;

            const spinner = document.createElement("div");
            dropDown.innerText = "";
            dropDown.classList.add("d-flex", "justify-content-center", "align-items-center");
            spinner.classList.add("spinner-border", "text-warning", "text-center", "m-auto");
            dropDown.appendChild(spinner);

            const address = await this.rpc("/autocomplete/address_full", {
                address: ev.currentTarget.innerText,
                google_place_id: ev.currentTarget.dataset.googlePlaceId,
                session_id: this.sessionId || null,
            });

            if (address.formatted_street_number) {
                this.streetAndNumberInput.value = address.formatted_street_number;
            }
            this.zipInput.value = address.zip || "";
            this.cityInput.value = address.city || "";

            const street2Input =
                this.street2Input || document.querySelector('input[name="street2"]');
            if (street2Input) {
                street2Input.value = address.street2 || "";
            }

            if (address.country) {
                this.countrySelect.value = address.country;
                this.countrySelect.dispatchEvent(new Event("change", { bubbles: true }));
            }
            if (address.state) {
                new MutationObserver((entries, observer) => {
                    this.stateSelect.value = address.state;
                    observer.disconnect();
                }).observe(this.stateSelect, {
                    childList: true,
                });
            }
            dropDown.remove();
            this.sessionId = this._generateUUID();
        },
    });
}
