/* Toast notification system – window.showToast(message, type, duration) */
(function () {
    'use strict';

    var container = null;

    var icons = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    function ensureContainer() {
        if (container && document.body.contains(container)) return;
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    function dismiss(el) {
        el.classList.add('toast-dismissing');
        setTimeout(function () {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 300);
    }

    window.showToast = function (message, type, duration) {
        type = type || 'info';
        duration = duration || 4500;
        ensureContainer();

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;

        var iconHtml = icons[type] || icons.info;
        toast.innerHTML =
            '<span class="toast-icon">' + iconHtml + '</span>' +
            '<span class="toast-message"></span>' +
            '<button type="button" class="toast-close" aria-label="Dismiss">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
            '</button>';

        toast.querySelector('.toast-message').textContent = message;
        toast.querySelector('.toast-close').addEventListener('click', function () { dismiss(toast); });

        container.prepend(toast);

        var timer = setTimeout(function () { dismiss(toast); }, duration);
        toast.addEventListener('mouseenter', function () { clearTimeout(timer); });
        toast.addEventListener('mouseleave', function () {
            timer = setTimeout(function () { dismiss(toast); }, 2000);
        });
    };
})();
