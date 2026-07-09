/** @odoo-module **/

/**
 * Public appointment booking page (/book-appointment).
 *
 * Defaults date/time to the nearest available slot. Includes lightweight
 * anti-bot fields (honeypot + submit timing) — no Cloudflare required.
 */

const ROUTES = Object.freeze({
    bootstrap: '/quote_manage_ui/appointment/bootstrap',
    slots: '/quote_manage_ui/appointment/slots',
    book: '/quote_manage_ui/appointment/book',
    cancel: '/quote_manage_ui/appointment/cancel',
});

function setStatus(container, state, message) {
    const statusEl = container.querySelector('.rw-appointment-status');
    if (!statusEl) return;
    statusEl.classList.remove(
        'rw-appointment-status--success',
        'rw-appointment-status--error',
    );
    if (!message) {
        statusEl.textContent = '';
        return;
    }
    if (state === 'success') {
        statusEl.classList.add('rw-appointment-status--success');
    } else if (state === 'error') {
        statusEl.classList.add('rw-appointment-status--error');
    }
    statusEl.textContent = message;
}

function setSubmitting(form, submitting) {
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;
    if (submitting) {
        if (!button.dataset.originalLabel) {
            button.dataset.originalLabel = button.textContent.trim();
        }
        button.textContent = form.dataset.submittingLabel || 'Please wait…';
        button.disabled = true;
        form.classList.add('is-submitting');
    } else {
        button.textContent =
            button.dataset.originalLabel || button.textContent;
        button.disabled = false;
        form.classList.remove('is-submitting');
    }
}

function ensureFormLoadedAt(form) {
    if (!form.dataset.loadedAt) {
        form.dataset.loadedAt = String(Date.now() / 1000);
    }
    return form.dataset.loadedAt;
}

function getAntiBotPayload(form) {
    const company = form.querySelector('[name="company"]');
    return {
        company: company ? company.value : '',
        form_loaded_at: ensureFormLoadedAt(form),
    };
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

function fillSelect(select, options, placeholder) {
    select.innerHTML = '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = placeholder;
    select.appendChild(empty);
    for (const option of options) {
        const node = document.createElement('option');
        node.value = option.value ?? option.id;
        node.textContent = option.label ?? option.name;
        select.appendChild(node);
    }
}

function setSelectValue(select, value) {
    if (!select || !value) return false;
    select.value = String(value);
    return select.value === String(value);
}

function getBookFormValues(form) {
    return {
        appointment_type_id: form.querySelector('[name="appointment_type_id"]').value,
        date: form.querySelector('[name="date"]').value,
        start: form.querySelector('[name="start"]').value,
        name: form.querySelector('[name="name"]').value.trim(),
        email: form.querySelector('[name="email"]').value.trim(),
        ...getAntiBotPayload(form),
    };
}

function getBookPanel(form) {
    return form.closest('.rw-appointment-panel');
}

function hideBookingSuccess(form) {
    const panel = getBookPanel(form);
    const successEl = panel && panel.querySelector('.rw-appointment-success');
    if (successEl) {
        successEl.classList.add('d-none');
    }
    form.classList.remove('d-none');
}

function showBookingSuccess(form, result) {
    const panel = getBookPanel(form);
    if (!panel) return;

    const successEl = panel.querySelector('.rw-appointment-success');
    if (!successEl) return;

    const reference = result.booking_reference || result.event_id || '';
    const setText = (selector, value) => {
        const node = successEl.querySelector(selector);
        if (node) {
            node.textContent = value || '';
        }
    };

    setText('[data-role="reference"]', reference);
    setText('[data-role="type"]', result.appointment_type || '');
    setText('[data-role="date"]', result.date_label || '');
    setText('[data-role="time"]', result.time_label || '');
    setText('[data-role="guest"]', result.guest_name || '');
    setText('[data-role="email"]', result.guest_email || '');

    const cancelEmail = document.querySelector('#rw_cancel_email');
    if (cancelEmail && result.guest_email) {
        cancelEmail.value = result.guest_email;
    }
    const cancelReference = document.querySelector('#rw_cancel_reference');
    if (cancelReference && reference) {
        cancelReference.value = String(reference);
    }

    form.classList.add('d-none');
    successEl.classList.remove('d-none');
    successEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    const cancelPanel = document.querySelector('#rw_appointment_cancel_panel');
    if (cancelPanel) {
        cancelPanel.classList.remove('d-none');
    }
}

async function loadSlots(form, preferredSlot) {
    const slotSelect = form.querySelector('[name="start"]');
    const values = getBookFormValues(form);
    slotSelect.disabled = true;
    fillSelect(slotSelect, [], 'Select time…');

    if (!values.appointment_type_id || !values.date) {
        return null;
    }

    const result = await postJsonRpc(ROUTES.slots, {
        appointment_type_id: values.appointment_type_id,
        date: values.date,
    });

    if (!result || !result.success) {
        setStatus(
            form,
            'error',
            (result && result.message) || 'Could not load time slots.',
        );
        return null;
    }

    fillSelect(slotSelect, result.slots || [], 'Select time…');
    slotSelect.disabled = !(result.slots && result.slots.length);
    if (!result.slots || !result.slots.length) {
        setStatus(form, 'error', result.message || 'No available times on this day.');
        return null;
    }

    const defaultSlot = preferredSlot || result.default_slot || result.slots[0].value;
    setSelectValue(slotSelect, defaultSlot);
    setStatus(form, null, '');
    return result;
}

async function applyBookingDefaults(form, bootstrapResult) {
    const typeSelect = form.querySelector('[name="appointment_type_id"]');
    const dateSelect = form.querySelector('[name="date"]');

    if (bootstrapResult.default_type_id) {
        setSelectValue(typeSelect, bootstrapResult.default_type_id);
    }
    if (bootstrapResult.default_date) {
        setSelectValue(dateSelect, bootstrapResult.default_date);
    }

    await loadSlots(form);
}

async function bootstrapBookForm(form) {
    ensureFormLoadedAt(form);
    const result = await postJsonRpc(ROUTES.bootstrap, {});
    if (!result || !result.success) {
        setStatus(
            form,
            'error',
            (result && result.message) || 'Could not load booking options.',
        );
        return;
    }

    fillSelect(
        form.querySelector('[name="appointment_type_id"]'),
        result.types,
        'Select type…',
    );
    fillSelect(
        form.querySelector('[name="date"]'),
        result.dates,
        'Select date…',
    );
    await applyBookingDefaults(form, result);
}

async function resetBookForm(form) {
    hideBookingSuccess(form);
    form.reset();
    const company = form.querySelector('[name="company"]');
    if (company) company.value = '';
    form.querySelector('[name="start"]').disabled = true;
    delete form.dataset.loadedAt;
    setStatus(form, null, '');
    await bootstrapBookForm(form);
}

async function handleBookSubmit(event) {
    const form = event.currentTarget;
    event.preventDefault();
    if (form.classList.contains('is-submitting')) return;

    setSubmitting(form, true);
    setStatus(form, null, '');

    try {
        const values = getBookFormValues(form);
        const result = await postJsonRpc(ROUTES.book, values);
        if (!result || !result.success) {
            setStatus(
                form,
                'error',
                (result && result.message) || 'Booking failed.',
            );
            return;
        }

        showBookingSuccess(form, result);
    } catch (error) {
        setStatus(form, 'error', error.message || 'Booking failed.');
    } finally {
        setSubmitting(form, false);
    }
}

async function handleCancelSubmit(event) {
    const form = event.currentTarget;
    event.preventDefault();
    if (form.classList.contains('is-submitting')) return;

    setSubmitting(form, true);
    setStatus(form, null, '');

    try {
        const result = await postJsonRpc(ROUTES.cancel, {
            email: form.querySelector('[name="email"]').value.trim(),
            booking_reference: form
                .querySelector('[name="booking_reference"]')
                .value.trim(),
            ...getAntiBotPayload(form),
        });
        if (!result || !result.success) {
            setStatus(
                form,
                'error',
                (result && result.message) || 'Cancellation failed.',
            );
            return;
        }
        setStatus(form, 'success', result.message);
        form.reset();
        const company = form.querySelector('[name="company"]');
        if (company) company.value = '';
        delete form.dataset.loadedAt;
        ensureFormLoadedAt(form);
    } catch (error) {
        setStatus(form, 'error', error.message || 'Cancellation failed.');
    } finally {
        setSubmitting(form, false);
    }
}

function bindBookForm(form) {
    if (form.dataset.bound === '1') return;
    form.dataset.bound = '1';

    form.addEventListener('submit', handleBookSubmit);
    for (const selector of [
        '[name="appointment_type_id"]',
        '[name="date"]',
    ]) {
        form.querySelector(selector).addEventListener('change', () => {
            loadSlots(form).catch((error) => {
                setStatus(form, 'error', error.message || 'Could not load slots.');
            });
        });
    }

    const panel = getBookPanel(form);
    const bookAnother = panel && panel.querySelector('.js_rw_appointment_book_another');
    if (bookAnother) {
        bookAnother.addEventListener('click', () => {
            resetBookForm(form).catch((error) => {
                setStatus(form, 'error', error.message || 'Could not reset form.');
            });
        });
    }

    bootstrapBookForm(form).catch((error) => {
        setStatus(
            form,
            'error',
            error.message || 'Could not load booking options.',
        );
    });
}

function bindCancelForm(form) {
    if (form.dataset.bound === '1') return;
    form.dataset.bound = '1';
    ensureFormLoadedAt(form);
    form.addEventListener('submit', handleCancelSubmit);
}

function bindForms() {
    for (const form of document.querySelectorAll('.js_rw_appointment_book_form')) {
        bindBookForm(form);
    }
    for (const form of document.querySelectorAll('.js_rw_appointment_cancel_form')) {
        bindCancelForm(form);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => bindForms());
} else {
    bindForms();
}

document.addEventListener('content_changed', () => bindForms());
