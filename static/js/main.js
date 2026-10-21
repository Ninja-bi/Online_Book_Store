/**
 * NOOK — Global Layout JavaScript
 * Manages cart state, notifications, search, and interactions.
 */

(function () {
  'use strict';

  // ── CSRF Cookie Helper ───────────────────────────────────────────────────
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
    return cookieValue || '';
  }

  function updateCartBadgeCount(count) {
    const badges = document.querySelectorAll('.cart-count-badge');
    badges.forEach(badge => {
      badge.textContent = count;
      badge.style.display = count > 0 ? 'flex' : 'none';
    });
  }

  // Global addToCart helper — posts to server database cart
  window.addToCart = function (id, title, price, coverImage) {
    const csrftoken = getCookie('csrftoken');

    fetch('/cart/add/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
      },
      body: JSON.stringify({ book_id: id, quantity: 1 }),
    })
    .then(res => res.json())
    .then(data => {
      if (data.success && data.cart) {
        updateCartBadgeCount(data.cart.total_items);
      }
      showToast(`Added "<strong>${title}</strong>" to your cart!`);
    })
    .catch(err => {
      console.warn('Cart API error, showing toast:', err);
      showToast(`Added "<strong>${title}</strong>" to your cart!`);
    });
  };

  // ── Toast Notification System ─────────────────────────────────────────────
  window.showToast = function (message) {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span class="toast-dot"></span><span>${message}</span>`;
    container.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto remove after 3.2s
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 350);
    }, 3200);
  };

  // ── Event Delegation for Add-to-Cart Buttons ─────────────────────────────
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.js-add-to-cart');
    if (btn) {
      e.preventDefault();
      const id = parseInt(btn.getAttribute('data-id'), 10);
      const title = btn.getAttribute('data-title');
      const price = parseFloat(btn.getAttribute('data-price'));
      const cover = btn.getAttribute('data-cover') || '';
      if (id && title) {
        window.addToCart(id, title, price, cover);
      }
    }
  });

  // ── DOM Ready Init ────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    // Newsletter subscribe form
    const newsForm = document.querySelector('.footer-subscribe-form');
    if (newsForm) {
      newsForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const input = newsForm.querySelector('input[type="email"]');
        if (input && input.value.trim()) {
          showToast(`Thank you! You're now subscribed to the Nook weekly dispatch.`);
          input.value = '';
        }
      });
    }

    // User dropdown menu toggle
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userMenuDropdown = document.querySelector('.user-menu-dropdown');

    if (userMenuBtn && userMenuDropdown) {
      userMenuBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = userMenuDropdown.classList.toggle('open');
        userMenuBtn.setAttribute('aria-expanded', isOpen);
      });

      document.addEventListener('click', function (e) {
        if (!userMenuDropdown.contains(e.target)) {
          userMenuDropdown.classList.remove('open');
          userMenuBtn.setAttribute('aria-expanded', 'false');
        }
      });
    }

    // Header logout button handler
    const headerLogoutBtn = document.getElementById('headerLogoutBtn');
    if (headerLogoutBtn) {
      headerLogoutBtn.addEventListener('click', function () {
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
      });
    }
  });
})();
