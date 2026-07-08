/** @odoo-module **/

/**
 * Public appointment booking page (/book-appointment).
 *
 * All fields are <select> or text inputs. Creates / cancels calendar.event
 * records through JSON-RPC endpoints on quote_manage_ui.
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

function getBookFormValues(form) {
    return {
        appointment_type_id: form.querySelector('[name="appointment_type_id"]').value,
        user_id: form.querySelector('[name="user_id"]').value,
        date: form.querySelector('[name="date"]').value,
        start: form.querySelector('[name="start"]').value,
        name: form.querySelector('[name="name"]').value.trim(),
        email: form.querySelector('[name="email"]').value.trim(),
        phone: form.querySelector('[name="phone"]').value.trim(),
    };
}

async function loadSlots(form) {
    const slotSelect = form.querySelector('[name="start"]');
    const values = getBookFormValues(form);
    slotSelect.disabled = true;
    fillSelect(slotSelect, [], 'Select time…');

    if (!values.appointment_type_id || !values.user_id || !values.date) {
        return;
    }

    const result = await postJsonRpc(ROUTES.slots, {
        appointment_type_id: values.appointment_type_id,
        user_id: values.user_id,
        date: values.date,
    });

    if (!result || !result.success) {
        setStatus(
            form,
            'error',
            (result && result.message) || 'Could not load time slots.',
        );
        return;
    }

    fillSelect(slotSelect, result.slots || [], 'Select time…');
    slotSelect.disabled = !(result.slots && result.slots.length);
    if (!result.slots || !result.slots.length) {
        setStatus(form, 'error', result.message || 'No available times on this day.');
    } else {
        setStatus(form, null, '');
    }
}

async function bootstrapBookForm(form) {
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
        form.querySelector('[name="user_id"]'),
        result.staff,
        'Select staff…',
    );
    fillSelect(
        form.querySelector('[name="date"]'),
        result.dates,
        'Select date…',
    );
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

        const reference = result.booking_reference || result.event_id;
        setStatus(
            form,
            'success',
            `${result.message} Reference: ${reference}`,
        );
        form.reset();
        form.querySelector('[name="start"]').disabled = true;
        await bootstrapBookForm(form);
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
        '[name="user_id"]',
        '[name="date"]',
    ]) {
        form.querySelector(selector).addEventListener('change', () => {
            loadSlots(form).catch((error) => {
                setStatus(form, 'error', error.message || 'Could not load slots.');
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
