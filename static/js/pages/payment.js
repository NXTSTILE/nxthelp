const config = window.PaymentConfig || {};

function showError(msg) {
    const el = document.getElementById('error-msg');
    if (!el) {
        return;
    }
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => {
        el.style.display = 'none';
    }, 6000);
}

async function initiatePayment() {
    const amountInput = document.getElementById('amount-input');
    const noteInput = document.getElementById('payment-note');
    const payBtn = document.getElementById('pay-btn');
    if (!amountInput || !payBtn) {
        return;
    }

    const amount = parseFloat(amountInput.value);
    if (!amount || amount <= 0) {
        showError('Please enter a valid amount.');
        amountInput.focus();
        return;
    }

    payBtn.disabled = true;
    payBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating order...';

    try {
        const response = await fetch(config.createOrderUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken,
            },
            body: JSON.stringify({
                amount: amount,
                note: (noteInput?.value || '').trim(),
            }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to create order');
        }

        const options = {
            key: config.razorpayKey,
            amount: data.amount,
            currency: data.currency,
            name: 'UniConnect',
            description: `Payment for: ${config.helpTitle}`,
            order_id: data.order_id,
            prefill: {
                name: config.payerName,
                email: config.payerEmail,
            },
            theme: {
                color: '#7c3aed',
            },
            handler: function (responseData) {
                document.getElementById('rz-payment-id').value = responseData.razorpay_payment_id;
                document.getElementById('rz-order-id').value = responseData.razorpay_order_id;
                document.getElementById('rz-signature').value = responseData.razorpay_signature;
                document.getElementById('payment-confirm-form').submit();
            },
            modal: {
                ondismiss: function () {
                    payBtn.disabled = false;
                    payBtn.innerHTML = '<i class="fas fa-lock"></i> Pay with Razorpay';
                },
            },
        };

        const rzp = new Razorpay(options);
        rzp.on('payment.failed', function (responseData) {
            showError(`Payment failed: ${responseData.error.description}`);
            payBtn.disabled = false;
            payBtn.innerHTML = '<i class="fas fa-lock"></i> Pay with Razorpay';
        });
        rzp.open();
    } catch (err) {
        showError(err.message || 'Something went wrong. Please try again.');
        payBtn.disabled = false;
        payBtn.innerHTML = '<i class="fas fa-lock"></i> Pay with Razorpay';
    }
}

window.initiatePayment = initiatePayment;
