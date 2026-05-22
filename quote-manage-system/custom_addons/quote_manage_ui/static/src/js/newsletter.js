/** @odoo-module **/

/**
 * Re-Ware "Follow our journey" newsletter — submit handler.
 *
 * Wires every <form class="js_rw_newsletter_form"> on the page so that:
 *   - submit is intercepted and posted as JSON-RPC to
 *     /quote_manage_ui/newsletter/subscribe;
 *   - while in flight the button reads "Submitting…" and is disabled;
 *   - on success / error a status message is rendered into
 *     .rw-newsletter-status, replacing any previous message.
 *
 * No Odoo widget framework is needed — plain DOM + fetch keep the snippet
 * usable inside the Website Builder preview as well.
 */

const STATE = Object.freeze({
    IDLE: 'idle',
    SUBMITTING: 'submitting',
    SUCCESS: 'success',
    ERROR: 'error',
});

function setStatus(form, state, message) {
    const statusEl = form.querySelector('.rw-newsletter-status');
    if (!statusEl) return;
    statusEl.classList.remove(
        'rw-newsletter-status--success',
        'rw-newsletter-status--error',
    );
    if (!message) {
        statusEl.textContent = '';
        return;
    }
    if (state === STATE.SUCCESS) {
        statusEl.classList.add('rw-newsletter-status--success');
    } else if (state === STATE.ERROR) {
        statusEl.classList.add('rw-newsletter-status--error');
    }
    statusEl.textContent = message;
}

function setSubmittingState(form, submitting) {
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;
    if (submitting) {
        if (!button.dataset.originalLabel) {
            button.dataset.originalLabel = button.textContent.trim();
        }
        const submittingLabel =
            form.dataset.submittingLabel || 'Submitting…';
        button.textContent = submittingLabel;
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        form.classList.add('is-submitting');
    } else {
        const originalLabel =
            button.dataset.originalLabel ||
            form.dataset.submitLabel ||
            'Join us!';
        button.textContent = originalLabel;
        button.disabled = false;
        button.removeAttribute('aria-busy');
        form.classList.remove('is-submitting');
    }
}

async function postJsonRpc(url, params) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: params || {},
        }),
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    if (data && data.error) {
        throw new Error(
            (data.error.data && data.error.data.message) ||
                data.error.message ||
                'Request failed',
        );
    }
    return data && data.result;
}

async function handleSubmit(event) {
    const form = event.currentTarget;
    event.preventDefault();
    if (form.classList.contains('is-submitting')) return;

    const firstName = (form.querySelector('[name="first_name"]') || {}).value || '';
    const lastName = (form.querySelector('[name="last_name"]') || {}).value || '';
    const email = (form.querySelector('[name="email"]') || {}).value || '';

    if (!email.trim() || !firstName.trim() || !lastName.trim()) {
        setStatus(form, STATE.ERROR, 'Please fill in every field.');
        return;
    }

    setStatus(form, STATE.IDLE, '');
    setSubmittingState(form, true);

    try {
        const result = await postJsonRpc(form.action, {
            first_name: firstName.trim(),
            last_name: lastName.trim(),
            email: email.trim(),
        });
        if (result && result.success) {
            setStatus(
                form,
                STATE.SUCCESS,
                result.message || "Thanks! You're on the list.",
            );
            form.reset();
        } else {
            setStatus(
                form,
                STATE.ERROR,
                (result && result.message) ||
                    'We could not subscribe you — please try again.',
            );
        }
    } catch (err) {
        setStatus(
            form,
            STATE.ERROR,
            'Network error — please check your connection and try again.',
        );
    } finally {
        setSubmittingState(form, false);
    }
}

function bindForms(root) {
    const scope = root || document;
    const forms = scope.querySelectorAll('form.js_rw_newsletter_form');
    forms.forEach((form) => {
        if (form.dataset.rwNewsletterBound === '1') return;
        form.dataset.rwNewsletterBound = '1';
        form.addEventListener('submit', handleSubmit);
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => bindForms());
} else {
    bindForms();
}

// Re-bind after Odoo Website Builder swaps DOM (snippet drop / save).
document.addEventListener('content_changed', () => bindForms());
