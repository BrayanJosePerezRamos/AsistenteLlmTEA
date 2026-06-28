/* ====================================================
   AsistenteTEA — Comportamientos cliente (JS puro)
   Pasado a gr.Blocks(js=...) — debe ser UNA función que
   Gradio ejecuta una vez al cargar la página.
   ==================================================== */

() => {
    'use strict';

    // ----------------------------------------------------------------
    // Indicador "JS✓" temporal arriba derecha — confirma que el script
    // se cargó. Se desvanece tras unos segundos.
    // ----------------------------------------------------------------
    function showLoadedBadge() {
        const badge = document.createElement('div');
        badge.textContent = 'JS✓';
        badge.style.cssText = [
            'position: fixed', 'top: 6px', 'right: 6px',
            'background: #10b981', 'color: white',
            'padding: 2px 8px', 'border-radius: 6px',
            'font-size: 11px', 'font-weight: 600',
            'z-index: 99999', 'opacity: 0.7',
            'pointer-events: none', 'font-family: monospace'
        ].join(';');
        document.body.appendChild(badge);
        setTimeout(() => { badge.style.opacity = '0.3'; }, 3000);
    }

    // ----------------------------------------------------------------
    // 1) Botón "1x ⇄ 1.5x" junto a cada <audio>.
    //    Cambia playbackRate HTML5 — no regenera WAV, no afecta pitch.
    // ----------------------------------------------------------------
    function attachSpeedControl(audioEl) {
        if (audioEl.dataset.speedAttached) return;
        audioEl.dataset.speedAttached = '1';

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = '»  1.5x';
        btn.style.cssText = [
            'margin: 6px 0 0 8px',
            'padding: 4px 10px',
            'font-size: 13px',
            'font-weight: 600',
            'border: 1px solid #3b82f6',
            'border-radius: 6px',
            'background: #fff',
            'color: #1e3a8a',
            'cursor: pointer'
        ].join(';');

        btn.addEventListener('click', () => {
            const next = audioEl.playbackRate >= 1.5 ? 1.0 : 1.5;
            audioEl.playbackRate = next;
            btn.textContent = next === 1.5 ? '«  1x' : '»  1.5x';
            btn.style.background = next === 1.5 ? '#dbeafe' : '#fff';
        });

        const container = audioEl.closest('.audio-container, .gradio-audio') || audioEl.parentElement;
        if (container) container.appendChild(btn);
    }

    // ----------------------------------------------------------------
    // 2) Auto-scroll del chatbot.
    //    El scroller real de gr.Chatbot es .bubble-wrap. Polling inicial
    //    hasta encontrarlo y luego MutationObserver para cada cambio.
    // ----------------------------------------------------------------
    function findChatScroller() {
        const cb = document.getElementById('main-chatbot');
        if (!cb) return null;
        return cb.querySelector('.bubble-wrap') || cb.querySelector('[class*="bubble"]') || cb;
    }

    function forceChatScroll() {
        const s = findChatScroller();
        if (!s) return;
        s.scrollTop = s.scrollHeight;
        requestAnimationFrame(() => { s.scrollTop = s.scrollHeight; });
        setTimeout(() => { s.scrollTop = s.scrollHeight; }, 100);
        setTimeout(() => { s.scrollTop = s.scrollHeight; }, 400);
    }

    let chatObs = null;
    function attachChatObserver() {
        if (chatObs) return true;
        const cb = document.getElementById('main-chatbot');
        if (!cb) return false;
        chatObs = new MutationObserver(forceChatScroll);
        chatObs.observe(cb, { childList: true, subtree: true, characterData: true });
        forceChatScroll();
        return true;
    }

    let attempts = 0;
    const pollInterval = setInterval(() => {
        attempts++;
        if (attachChatObserver() || attempts > 50) clearInterval(pollInterval);
    }, 200);

    // ----------------------------------------------------------------
    // 3) Enter envía / Ctrl+Enter inserta salto de línea manualmente.
    // ----------------------------------------------------------------
    function clickSendButton() {
        const el = document.getElementById('chat-send-btn');
        if (!el) return;
        const btn = el.tagName === 'BUTTON' ? el : el.querySelector('button');
        if (btn && !btn.disabled) btn.click();
    }

    function insertNewlineAtCursor(textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const v = textarea.value;
        textarea.value = v.slice(0, start) + '\n' + v.slice(end);
        textarea.selectionStart = textarea.selectionEnd = start + 1;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }

    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Enter') return;
        const t = e.target;
        if (!(t instanceof HTMLTextAreaElement)) return;
        if (!t.closest('#chat-text-input')) return;

        if (e.ctrlKey || e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            insertNewlineAtCursor(t);
            return;
        }

        e.preventDefault();
        e.stopPropagation();
        clickSendButton();
    }, true);

    // ----------------------------------------------------------------
    // 4) Toggles de accesibilidad: texto grande / alto contraste.
    //    Sin callback Python — aplicamos clases CSS al <body> y
    //    persistimos en localStorage entre recargas.
    // ----------------------------------------------------------------
    const STORAGE_KEY_LARGE   = 'tea.largeText';
    const STORAGE_KEY_CONTRAST = 'tea.highContrast';

    function applyA11yClasses() {
        const large = localStorage.getItem(STORAGE_KEY_LARGE) === '1';
        const contrast = localStorage.getItem(STORAGE_KEY_CONTRAST) === '1';
        document.body.classList.toggle('large-text', large);
        document.body.classList.toggle('high-contrast', contrast);
    }

    function findCheckboxInput(id) {
        // gr.Checkbox(elem_id=X) crea <div id="X"> con un <input type="checkbox"> dentro.
        const wrapper = document.getElementById(id);
        if (!wrapper) return null;
        if (wrapper.tagName === 'INPUT') return wrapper;
        return wrapper.querySelector('input[type="checkbox"]');
    }

    function setupA11yToggles() {
        // Sincronizar UI checkbox con localStorage al cargar
        const largeInput = findCheckboxInput('cfg-large-text');
        const contrastInput = findCheckboxInput('cfg-high-contrast');

        if (largeInput) {
            largeInput.checked = localStorage.getItem(STORAGE_KEY_LARGE) === '1';
            largeInput.addEventListener('change', () => {
                localStorage.setItem(STORAGE_KEY_LARGE, largeInput.checked ? '1' : '0');
                applyA11yClasses();
            });
        }
        if (contrastInput) {
            contrastInput.checked = localStorage.getItem(STORAGE_KEY_CONTRAST) === '1';
            contrastInput.addEventListener('change', () => {
                localStorage.setItem(STORAGE_KEY_CONTRAST, contrastInput.checked ? '1' : '0');
                applyA11yClasses();
            });
        }
        return !!(largeInput && contrastInput);
    }

    applyA11yClasses();
    let a11yAttempts = 0;
    const a11yPoll = setInterval(() => {
        a11yAttempts++;
        if (setupA11yToggles() || a11yAttempts > 50) clearInterval(a11yPoll);
    }, 200);

    // ----------------------------------------------------------------
    // 4b) Confirmación al pulsar "Reiniciar".
    //     Solo pide confirmación si hay mensajes en el chat (evita
    //     molestar cuando el botón se pulsa sin conversación activa).
    //     stopImmediatePropagation cancela el callback de Gradio si
    //     el usuario rechaza.
    // ----------------------------------------------------------------
    document.addEventListener('click', function (e) {
        const resetEl = e.target.closest('#chat-reset-btn');
        if (!resetEl) return;
        // Si no hay burbujas en el chat, no preguntar — reset es no-op
        const cb = document.getElementById('main-chatbot');
        const hasMessages = cb && cb.querySelectorAll('.message, .bubble-wrap').length > 0;
        if (!hasMessages) return;

        const ok = confirm('¿Reiniciar la conversación? Se perderán los mensajes actuales.');
        if (!ok) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
        }
    }, true);

    // ----------------------------------------------------------------
    // 5) Badge "●" en la pestaña Historia Social cuando termina la
    //    sesión. Detectamos la aparición del banner .session-ended-banner
    //    y añadimos un span dentro del segundo botón de .tab-nav.
    //    Click en la pestaña → quita el badge.
    // ----------------------------------------------------------------
    function getHistoriaTabButton() {
        // Las pestañas Gradio están en .tab-nav. La 2ª es Historia Social.
        const navs = document.querySelectorAll('.tab-nav button');
        return navs[1] || null;  // 0: Chat, 1: Historia
    }

    function addHistoriaBadge() {
        const btn = getHistoriaTabButton();
        if (!btn || btn.querySelector('.new-badge')) return;
        const dot = document.createElement('span');
        dot.className = 'new-badge';
        dot.textContent = '●';
        dot.setAttribute('aria-label', 'Nueva Historia Social disponible');
        btn.appendChild(dot);
        // Click en la pestaña → quitar badge
        const handler = () => {
            const d = btn.querySelector('.new-badge');
            if (d) d.remove();
            btn.removeEventListener('click', handler);
        };
        btn.addEventListener('click', handler);
    }

    // Observador: cuando aparece el banner de fin de sesión, ponemos el badge
    const sessionEndObs = new MutationObserver(() => {
        if (document.querySelector('.session-ended-banner')) {
            addHistoriaBadge();
        }
    });
    sessionEndObs.observe(document.body, { childList: true, subtree: true });

    // ----------------------------------------------------------------
    // Observador global — engancha audios nuevos al volar.
    // ----------------------------------------------------------------
    new MutationObserver(() => {
        document.querySelectorAll('audio').forEach(attachSpeedControl);
    }).observe(document.body, { childList: true, subtree: true });

    document.querySelectorAll('audio').forEach(attachSpeedControl);
    showLoadedBadge();
}
