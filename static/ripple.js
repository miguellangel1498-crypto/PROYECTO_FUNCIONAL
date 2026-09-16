/**
 * Ripple Effect - Growth Horizon
 * Genera una onda expansiva en el punto exacto del clic.
 * Delegación de eventos global, sin dependencias.
 */
(function () {
    'use strict';

    document.addEventListener('pointerdown', function (e) {
        var target = e.target.closest(
            'button, a, input[type="submit"], input[type="button"], [role="button"], .interactive-click, aside nav a'
        );

        if (!target) return;
        if (target.disabled || target.dataset.noRipple !== undefined) return;

        var rect = target.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        target.classList.add('gh-ripple-host');

        var diameter = Math.max(rect.width, rect.height) * 1.5;
        var radius = diameter / 2;
        var x = e.clientX - rect.left - radius;
        var y = e.clientY - rect.top - radius;

        var wave = document.createElement('span');
        wave.classList.add('gh-ripple-wave');

        // Si el fondo del elemento es claro, usar variante dark (verde esmeralda)
        try {
            var bg = window.getComputedStyle(target).backgroundColor;
            var rgb = bg.match(/\d+/g);
            if (rgb && rgb.length >= 3) {
                var brightness = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
                if (brightness > 180) {
                    wave.classList.add('gh-ripple-dark');
                }
            }
        } catch (err) {}

        wave.style.width = diameter + 'px';
        wave.style.height = diameter + 'px';
        wave.style.left = x + 'px';
        wave.style.top = y + 'px';

        target.appendChild(wave);

        setTimeout(function () {
            if (wave.parentNode) wave.parentNode.removeChild(wave);
        }, 600);
    }, { passive: true });
})();
