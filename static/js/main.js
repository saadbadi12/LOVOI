// LOVOI_2 - JavaScript utilities

// Price calculator for reservation form
document.addEventListener('DOMContentLoaded', function() {
    const dateDebut = document.querySelector('input[name="date_debut"]');
    const dateFin = document.querySelector('input[name="date_fin"]');
    const priceDisplay = document.getElementById('price-calculator');

    if (dateDebut && dateFin && priceDisplay) {
        function calculatePrice() {
            const debut = new Date(dateDebut.value);
            const fin = new Date(dateFin.value);
            const dailyPrice = parseFloat(priceDisplay.dataset.dailyPrice || 0);
            const caution = parseFloat(priceDisplay.dataset.caution || 0);

            if (deebut && fin && fin >= debut) {
                const days = Math.ceil((fin - debut) / (1000 * 60 * 60 * 24));
                const total = days * dailyPrice;
                const ttc = total * 1.2; // with 20% VAT

                priceDisplay.innerHTML = `
                    <div class="alert alert-info">
                        <h5>Détails du prix</h5>
                        <p>Durée: <strong>${days} jour(s)</strong></p>
                        <p>Prix jour: <strong>${dailyPrice} MAD</strong></p>
                        <p>Total HT: <strong>${total.toFixed(2)} MAD</strong></p>
                        <p>TVA (20%): <strong>${(total * 0.2).toFixed(2)} MAD</strong></p>
                        <p class="fw-bold fs-5">Total TTC: ${ttc.toFixed(2)} MAD</p>
                        <p>Caution: ${caution} MAD (à verser à la récupération)</p>
                    </div>
                `;
            }
        }

        dateDebut.addEventListener('change', calculatePrice);
        dateFin.addEventListener('change', calculatePrice);
    }

    // Check for notification badge updates
    const notifCount = document.querySelector('.notification-count');
    if (notifCount) {
        fetch('/api/notifications/?format=json')
            .then(res => res.json())
            .then(data => {
                const unread = data.filter(n => !n.lue).length;
                if (unread > 0) {
                    notifCount.textContent = unread;
                    notifCount.style.display = 'inline-block';
                }
            })
            .catch(() => {});
    }
});

// Mark notifications as read
function markNotificationsRead() {
    fetch('/api/notifications/mark_all_read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        }
    }).then(() => {
        document.querySelectorAll('.notification-item.unread').forEach(el => {
            el.classList.remove('unread');
            el.classList.add('read');
        });
    });
}

// Helper to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
