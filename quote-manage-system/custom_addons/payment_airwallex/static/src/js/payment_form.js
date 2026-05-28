/** @odoo-module **/
/* eslint-disable no-restricted-globals */
/*
 * Airwallex payment_form integration.
 *
 * Wires the generic payment.form widget to Airwallex's Hosted Payment Page
 * via @airwallex/components-sdk. We intentionally do NOT bundle the SDK --
 * it is loaded at runtime from Airwallex's CDN so updates land without us
 * having to redeploy the module.
 *
 * Lifecycle:
 *   1. Customer clicks "Pay Now" on /shop/payment.
 *   2. PaymentForm.start() resolves -> _processRedirectFlow -> we get
 *      processing_values back from Odoo (created in
 *      payment_transaction._get_specific_rendering_values).
 *   3. We swap the standard redirect for a SDK-driven
 *      payments.redirectToCheckout() call, which sends the customer to the
 *      HPP. The HPP's successUrl/cancelUrl point back at our controllers.
 */

import paymentForm from '@payment/js/payment_form';
import { _t } from '@web/core/l10n/translation';
import { loadJS } from '@web/core/assets';

const AIRWALLEX_SDK_URL = 'https://static.airwallex.com/components/sdk/v1/index.js';

paymentForm.include({
    /**
     * Override the generic redirect handler for the Airwallex provider.
     */
    async _processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'airwallex') {
            return this._super(...arguments);
        }
        try {
            await loadJS(AIRWALLEX_SDK_URL);
        } catch (err) {
            this._displayErrorDialog(
                _t('Cannot load Airwallex'),
                _t('The Airwallex payment SDK could not be reached. Please retry.'),
            );
            throw err;
        }

        const sdk = window.AirwallexComponentsSDK || window.Airwallex;
        if (!sdk || typeof sdk.init !== 'function') {
            this._displayErrorDialog(
                _t('Airwallex unavailable'),
                _t('The Airwallex SDK loaded but did not initialise correctly.'),
            );
            return;
        }
        const { payments } = await sdk.init({
            env: processingValues.airwallex_env || 'demo',
            enabledElements: ['payments'],
        });

        await payments.redirectToCheckout({
            mode: 'payment',
            intent_id: processingValues.airwallex_intent_id,
            client_secret: processingValues.airwallex_client_secret,
            currency: processingValues.airwallex_currency,
            country_code: processingValues.airwallex_country_code,
            successUrl: processingValues.airwallex_success_url,
            cancelUrl: processingValues.airwallex_cancel_url,
            failUrl: processingValues.airwallex_cancel_url,
            // Match the Re-Ware brand. Customise via the provider form
            // later if marketing wants tweaks.
            appearance: {
                mode: 'light',
                variables: { colorBrand: '#612FFF' },
            },
        });
    },
});
