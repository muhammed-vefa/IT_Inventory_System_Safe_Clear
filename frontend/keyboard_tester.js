// =============================================================================
// KEYBOARD TESTER MODULE (Klavye Test Aracı)
// KeyData KSH IT Inventory System
// =============================================================================

(function() {
    const KEY_LAYOUTS = {
        'TR-Q': {
            main: [
                // Row 0: Esc + Function keys
                [
                    { code: 'Escape', label: 'Esc', width: 'w-1' },
                    { spacer: 'w-1' },
                    { code: 'F1', label: 'F1', width: 'w-1' },
                    { code: 'F2', label: 'F2', width: 'w-1' },
                    { code: 'F3', label: 'F3', width: 'w-1' },
                    { code: 'F4', label: 'F4', width: 'w-1' },
                    { spacer: 'w-0-5' },
                    { code: 'F5', label: 'F5', width: 'w-1' },
                    { code: 'F6', label: 'F6', width: 'w-1' },
                    { code: 'F7', label: 'F7', width: 'w-1' },
                    { code: 'F8', label: 'F8', width: 'w-1' },
                    { spacer: 'w-0-5' },
                    { code: 'F9', label: 'F9', width: 'w-1' },
                    { code: 'F10', label: 'F10', width: 'w-1' },
                    { code: 'F11', label: 'F11', width: 'w-1' },
                    { code: 'F12', label: 'F12', width: 'w-1' }
                ],
                // Row 1: Numbers
                [
                    { code: 'Backquote', main: '"', sub: 'é', width: 'w-1' },
                    { code: 'Digit1', main: '1', sub: '!', width: 'w-1' },
                    { code: 'Digit2', main: '2', sub: '\'', width: 'w-1' },
                    { code: 'Digit3', main: '3', sub: '^', width: 'w-1' },
                    { code: 'Digit4', main: '4', sub: '+', width: 'w-1' },
                    { code: 'Digit5', main: '5', sub: '%', width: 'w-1' },
                    { code: 'Digit6', main: '6', sub: '&', width: 'w-1' },
                    { code: 'Digit7', main: '7', sub: '/', width: 'w-1' },
                    { code: 'Digit8', main: '8', sub: '(', width: 'w-1' },
                    { code: 'Digit9', main: '9', sub: ')', width: 'w-1' },
                    { code: 'Digit0', main: '0', sub: '=', width: 'w-1' },
                    { code: 'Minus', main: '*', sub: '?', width: 'w-1' },
                    { code: 'Equal', main: '-', sub: '_', width: 'w-1' },
                    { code: 'Backspace', label: 'Backspace', width: 'w-2' }
                ],
                // Row 2: Tab + QWERTY
                [
                    { code: 'Tab', label: 'Tab ⇥', width: 'w-1-5' },
                    { code: 'KeyQ', label: 'Q', width: 'w-1' },
                    { code: 'KeyW', label: 'W', width: 'w-1' },
                    { code: 'KeyE', main: 'E', sub: '€', width: 'w-1' },
                    { code: 'KeyR', label: 'R', width: 'w-1' },
                    { code: 'KeyT', label: 'T', width: 'w-1' },
                    { code: 'KeyY', label: 'Y', width: 'w-1' },
                    { code: 'KeyU', label: 'U', width: 'w-1' },
                    { code: 'KeyI', label: 'I', width: 'w-1' },
                    { code: 'KeyO', label: 'O', width: 'w-1' },
                    { code: 'KeyP', label: 'P', width: 'w-1' },
                    { code: 'BracketLeft', main: 'Ğ', sub: '¨', width: 'w-1' },
                    { code: 'BracketRight', main: 'Ü', sub: '~', width: 'w-1' },
                    { code: 'Backslash', main: ',', sub: ';', width: 'w-1-5' }
                ],
                // Row 3: Caps + ASDF
                [
                    { code: 'CapsLock', label: 'Caps Lock', width: 'w-1-75' },
                    { code: 'KeyA', label: 'A', width: 'w-1' },
                    { code: 'KeyS', label: 'S', width: 'w-1' },
                    { code: 'KeyD', label: 'D', width: 'w-1' },
                    { code: 'KeyF', label: 'F', width: 'w-1' },
                    { code: 'KeyG', label: 'G', width: 'w-1' },
                    { code: 'KeyH', label: 'H', width: 'w-1' },
                    { code: 'KeyJ', label: 'J', width: 'w-1' },
                    { code: 'KeyK', label: 'K', width: 'w-1' },
                    { code: 'KeyL', label: 'L', width: 'w-1' },
                    { code: 'Semicolon', main: 'Ş', sub: '´', width: 'w-1' },
                    { code: 'Quote', main: 'İ', sub: '`', width: 'w-1' },
                    { code: 'Enter', label: 'Enter ↵', width: 'w-2-25' }
                ],
                // Row 4: Shift + ZXCV
                [
                    { code: 'ShiftLeft', label: 'Shift ⇧', width: 'w-1-25' },
                    { code: 'IntlBackslash', main: '<', sub: '>', width: 'w-1' },
                    { code: 'KeyZ', label: 'Z', width: 'w-1' },
                    { code: 'KeyX', label: 'X', width: 'w-1' },
                    { code: 'KeyC', label: 'C', width: 'w-1' },
                    { code: 'KeyV', label: 'V', width: 'w-1' },
                    { code: 'KeyB', label: 'B', width: 'w-1' },
                    { code: 'KeyN', label: 'N', width: 'w-1' },
                    { code: 'KeyM', label: 'M', width: 'w-1' },
                    { code: 'Comma', label: 'Ö', width: 'w-1' },
                    { code: 'Period', label: 'Ç', width: 'w-1' },
                    { code: 'Slash', main: '.', sub: ':', width: 'w-1' },
                    { code: 'ShiftRight', label: 'Shift ⇧', width: 'w-2-75' }
                ],
                // Row 5: Modifiers + Space
                [
                    { code: 'ControlLeft', label: 'Ctrl', width: 'w-1-25' },
                    { code: 'MetaLeft', label: 'Win ⊞', width: 'w-1-25' },
                    { code: 'AltLeft', label: 'Alt', width: 'w-1-25' },
                    { code: 'Space', label: 'Space', width: 'w-space' },
                    { code: 'AltRight', label: 'Alt Gr', width: 'w-1-25' },
                    { code: 'MetaRight', label: 'Win ⊞', width: 'w-1-25' },
                    { code: 'ContextMenu', label: 'Menu ≣', width: 'w-1-25' },
                    { code: 'ControlRight', label: 'Ctrl', width: 'w-1-25' }
                ]
            ],
            nav: [
                [
                    { code: 'PrintScreen', label: 'PrtSc', width: 'w-1' },
                    { code: 'ScrollLock', label: 'ScrLk', width: 'w-1' },
                    { code: 'Pause', label: 'Pause', width: 'w-1' }
                ],
                [
                    { code: 'Insert', label: 'Ins', width: 'w-1' },
                    { code: 'Home', label: 'Home', width: 'w-1' },
                    { code: 'PageUp', label: 'PgUp', width: 'w-1' }
                ],
                [
                    { code: 'Delete', label: 'Del', width: 'w-1' },
                    { code: 'End', label: 'End', width: 'w-1' },
                    { code: 'PageDown', label: 'PgDn', width: 'w-1' }
                ],
                [
                    { spacer: 'w-nav-row-gap' }
                ],
                [
                    { spacer: 'w-1' },
                    { code: 'ArrowUp', label: '▲', width: 'w-1' },
                    { spacer: 'w-1' }
                ],
                [
                    { code: 'ArrowLeft', label: '◀', width: 'w-1' },
                    { code: 'ArrowDown', label: '▼', width: 'w-1' },
                    { code: 'ArrowRight', label: '▶', width: 'w-1' }
                ]
            ],
            numpad: [
                { code: 'NumLock', label: 'Num' },
                { code: 'NumpadDivide', label: '/' },
                { code: 'NumpadMultiply', label: '*' },
                { code: 'NumpadSubtract', label: '-' },
                { code: 'Numpad7', label: '7' },
                { code: 'Numpad8', label: '8' },
                { code: 'Numpad9', label: '9' },
                { code: 'NumpadAdd', label: '+', gridClass: 'np-add' },
                { code: 'Numpad4', label: '4' },
                { code: 'Numpad5', label: '5' },
                { code: 'Numpad6', label: '6' },
                { code: 'Numpad1', label: '1' },
                { code: 'Numpad2', label: '2' },
                { code: 'Numpad3', label: '3' },
                { code: 'NumpadEnter', label: 'Enter', gridClass: 'np-enter' },
                { code: 'Numpad0', label: '0', gridClass: 'np-zero' },
                { code: 'NumpadDecimal', label: '.' }
            ]
        },
        'US': {
            main: [
                [
                    { code: 'Escape', label: 'Esc', width: 'w-1' },
                    { spacer: 'w-1' },
                    { code: 'F1', label: 'F1', width: 'w-1' },
                    { code: 'F2', label: 'F2', width: 'w-1' },
                    { code: 'F3', label: 'F3', width: 'w-1' },
                    { code: 'F4', label: 'F4', width: 'w-1' },
                    { spacer: 'w-0-5' },
                    { code: 'F5', label: 'F5', width: 'w-1' },
                    { code: 'F6', label: 'F6', width: 'w-1' },
                    { code: 'F7', label: 'F7', width: 'w-1' },
                    { code: 'F8', label: 'F8', width: 'w-1' },
                    { spacer: 'w-0-5' },
                    { code: 'F9', label: 'F9', width: 'w-1' },
                    { code: 'F10', label: 'F10', width: 'w-1' },
                    { code: 'F11', label: 'F11', width: 'w-1' },
                    { code: 'F12', label: 'F12', width: 'w-1' }
                ],
                [
                    { code: 'Backquote', main: '`', sub: '~', width: 'w-1' },
                    { code: 'Digit1', main: '1', sub: '!', width: 'w-1' },
                    { code: 'Digit2', main: '2', sub: '@', width: 'w-1' },
                    { code: 'Digit3', main: '3', sub: '#', width: 'w-1' },
                    { code: 'Digit4', main: '4', sub: '$', width: 'w-1' },
                    { code: 'Digit5', main: '5', sub: '%', width: 'w-1' },
                    { code: 'Digit6', main: '6', sub: '^', width: 'w-1' },
                    { code: 'Digit7', main: '7', sub: '&', width: 'w-1' },
                    { code: 'Digit8', main: '8', sub: '*', width: 'w-1' },
                    { code: 'Digit9', main: '9', sub: '(', width: 'w-1' },
                    { code: 'Digit0', main: '0', sub: ')', width: 'w-1' },
                    { code: 'Minus', main: '-', sub: '_', width: 'w-1' },
                    { code: 'Equal', main: '=', sub: '+', width: 'w-1' },
                    { code: 'Backspace', label: 'Backspace', width: 'w-2' }
                ],
                [
                    { code: 'Tab', label: 'Tab ⇥', width: 'w-1-5' },
                    { code: 'KeyQ', label: 'Q', width: 'w-1' },
                    { code: 'KeyW', label: 'W', width: 'w-1' },
                    { code: 'KeyE', label: 'E', width: 'w-1' },
                    { code: 'KeyR', label: 'R', width: 'w-1' },
                    { code: 'KeyT', label: 'T', width: 'w-1' },
                    { code: 'KeyY', label: 'Y', width: 'w-1' },
                    { code: 'KeyU', label: 'U', width: 'w-1' },
                    { code: 'KeyI', label: 'I', width: 'w-1' },
                    { code: 'KeyO', label: 'O', width: 'w-1' },
                    { code: 'KeyP', label: 'P', width: 'w-1' },
                    { code: 'BracketLeft', main: '[', sub: '{', width: 'w-1' },
                    { code: 'BracketRight', main: ']', sub: '}', width: 'w-1' },
                    { code: 'Backslash', main: '\\', sub: '|', width: 'w-1-5' }
                ],
                [
                    { code: 'CapsLock', label: 'Caps Lock', width: 'w-1-75' },
                    { code: 'KeyA', label: 'A', width: 'w-1' },
                    { code: 'KeyS', label: 'S', width: 'w-1' },
                    { code: 'KeyD', label: 'D', width: 'w-1' },
                    { code: 'KeyF', label: 'F', width: 'w-1' },
                    { code: 'KeyG', label: 'G', width: 'w-1' },
                    { code: 'KeyH', label: 'H', width: 'w-1' },
                    { code: 'KeyJ', label: 'J', width: 'w-1' },
                    { code: 'KeyK', label: 'K', width: 'w-1' },
                    { code: 'KeyL', label: 'L', width: 'w-1' },
                    { code: 'Semicolon', main: ';', sub: ':', width: 'w-1' },
                    { code: 'Quote', main: '\'', sub: '"', width: 'w-1' },
                    { code: 'Enter', label: 'Enter ↵', width: 'w-2-25' }
                ],
                [
                    { code: 'ShiftLeft', label: 'Shift ⇧', width: 'w-2-25' },
                    { code: 'KeyZ', label: 'Z', width: 'w-1' },
                    { code: 'KeyX', label: 'X', width: 'w-1' },
                    { code: 'KeyC', label: 'C', width: 'w-1' },
                    { code: 'KeyV', label: 'V', width: 'w-1' },
                    { code: 'KeyB', label: 'B', width: 'w-1' },
                    { code: 'KeyN', label: 'N', width: 'w-1' },
                    { code: 'KeyM', label: 'M', width: 'w-1' },
                    { code: 'Comma', main: ',', sub: '<', width: 'w-1' },
                    { code: 'Period', main: '.', sub: '>', width: 'w-1' },
                    { code: 'Slash', main: '/', sub: '?', width: 'w-1' },
                    { code: 'ShiftRight', label: 'Shift ⇧', width: 'w-2-75' }
                ],
                [
                    { code: 'ControlLeft', label: 'Ctrl', width: 'w-1-25' },
                    { code: 'MetaLeft', label: 'Win ⊞', width: 'w-1-25' },
                    { code: 'AltLeft', label: 'Alt', width: 'w-1-25' },
                    { code: 'Space', label: 'Space', width: 'w-space' },
                    { code: 'AltRight', label: 'Alt', width: 'w-1-25' },
                    { code: 'MetaRight', label: 'Win ⊞', width: 'w-1-25' },
                    { code: 'ContextMenu', label: 'Menu ≣', width: 'w-1-25' },
                    { code: 'ControlRight', label: 'Ctrl', width: 'w-1-25' }
                ]
            ],
            nav: [
                [
                    { code: 'PrintScreen', label: 'PrtSc', width: 'w-1' },
                    { code: 'ScrollLock', label: 'ScrLk', width: 'w-1' },
                    { code: 'Pause', label: 'Pause', width: 'w-1' }
                ],
                [
                    { code: 'Insert', label: 'Ins', width: 'w-1' },
                    { code: 'Home', label: 'Home', width: 'w-1' },
                    { code: 'PageUp', label: 'PgUp', width: 'w-1' }
                ],
                [
                    { code: 'Delete', label: 'Del', width: 'w-1' },
                    { code: 'End', label: 'End', width: 'w-1' },
                    { code: 'PageDown', label: 'PgDn', width: 'w-1' }
                ],
                [
                    { spacer: 'w-nav-row-gap' }
                ],
                [
                    { spacer: 'w-1' },
                    { code: 'ArrowUp', label: '▲', width: 'w-1' },
                    { spacer: 'w-1' }
                ],
                [
                    { code: 'ArrowLeft', label: '◀', width: 'w-1' },
                    { code: 'ArrowDown', label: '▼', width: 'w-1' },
                    { code: 'ArrowRight', label: '▶', width: 'w-1' }
                ]
            ],
            numpad: [
                { code: 'NumLock', label: 'Num' },
                { code: 'NumpadDivide', label: '/' },
                { code: 'NumpadMultiply', label: '*' },
                { code: 'NumpadSubtract', label: '-' },
                { code: 'Numpad7', label: '7' },
                { code: 'Numpad8', label: '8' },
                { code: 'Numpad9', label: '9' },
                { code: 'NumpadAdd', label: '+', gridClass: 'np-add' },
                { code: 'Numpad4', label: '4' },
                { code: 'Numpad5', label: '5' },
                { code: 'Numpad6', label: '6' },
                { code: 'Numpad1', label: '1' },
                { code: 'Numpad2', label: '2' },
                { code: 'Numpad3', label: '3' },
                { code: 'NumpadEnter', label: 'Enter', gridClass: 'np-enter' },
                { code: 'Numpad0', label: '0', gridClass: 'np-zero' },
                { code: 'NumpadDecimal', label: '.' }
            ]
        }
    };

    const KeyboardTester = {
        keyboardLayout: localStorage.getItem('kb_layout') || 'TR-Q',
        keyboardNumpadVisible: localStorage.getItem('kb_numpad_visible') !== 'false',
        keyboardSoundEnabled: localStorage.getItem('kb_sound_enabled') !== 'false',
        testedKeyCodes: new Set(),
        keyHistory: [],
        audioCtx: null,
        _listenersAttached: false,

        initKeyboardTest: function() {
            this.renderKeyboard();
            this.setupKeyboardListeners();
            this.updateKeyboardStats();
            this.updateLayoutToggleUI();
            this.updateNumpadToggleUI();
            this.updateSoundToggleUI();
        },

        setupKeyboardListeners: function() {
            if (this._listenersAttached) return;
            this._listenersAttached = true;

            // Capture phase (true) intercepts F5, F11, F12 before browser default actions
            window.addEventListener('keydown', (e) => {
                if (this.state && this.state.view !== 'keyboard-test') return;
                this.handleKeyDown(e);
            }, true);

            window.addEventListener('keyup', (e) => {
                if (this.state && this.state.view !== 'keyboard-test') return;
                this.handleKeyUp(e);
            }, true);
        },

        handleKeyDown: function(e) {
            let code = e.code || '';
            const key = e.key || '';
            const keyCode = e.keyCode || e.which || 0;

            // Map F1-F12 keys reliably by keyCode (112-123) or name
            const fKeyCodeMap = {
                112: 'F1', 113: 'F2', 114: 'F3', 115: 'F4',
                116: 'F5', 117: 'F6', 118: 'F7', 119: 'F8',
                120: 'F9', 121: 'F10', 122: 'F11', 123: 'F12'
            };

            const isFKey = /^F([1-9]|1[0-2])$/i.test(code) || 
                          /^F([1-9]|1[0-2])$/i.test(key) || 
                          (keyCode >= 112 && keyCode <= 123);

            if (isFKey) {
                if (fKeyCodeMap[keyCode]) {
                    code = fKeyCodeMap[keyCode];
                } else if (!code && key) {
                    code = key.toUpperCase();
                }
            }

            // Prevent all browser actions that interfere with keyboard testing
            // F5 (reload), F11 (fullscreen), F12 (devtools), Tab, Space, Backspace, etc.
            const preventCodes = [
                'Tab', 'Space', 'Backspace', 'ContextMenu',
                'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
                'PageUp', 'PageDown', 'Home', 'End', 'Insert',
                'Escape'
            ];

            if (isFKey || preventCodes.includes(code) || (e.altKey && ['ArrowLeft', 'ArrowRight'].includes(code))) {
                if (typeof e.preventDefault === 'function') e.preventDefault();
                if (typeof e.stopPropagation === 'function') e.stopPropagation();
            }

            if (!code) code = key || `Key_${keyCode}`;

            this.testedKeyCodes.add(code);
            this.playMechanicalSound();

            // Find key DOM element by data-code or fallback by key
            let keyEl = document.querySelector(`.kb-key[data-code="${code}"]`);
            if (!keyEl && key) {
                keyEl = document.querySelector(`.kb-key[data-code="${key}"]`);
            }
            if (keyEl) {
                keyEl.classList.add('active');
                keyEl.classList.add('tested');
            }

            // Update Lock LEDs
            this.updateLockLEDs(e);

            // Update stats & history
            const readableName = this.formatKeyName(e, code);
            this.updateLastKey(readableName, code, keyCode);
            this.pushHistory(readableName, code);
            this.updateKeyboardStats();
        },

        handleKeyUp: function(e) {
            let code = e.code || '';
            const key = e.key || '';
            const keyCode = e.keyCode || e.which || 0;

            const isFKey = /^F([1-9]|1[0-2])$/i.test(code) || 
                          /^F([1-9]|1[0-2])$/i.test(key) || 
                          (keyCode >= 112 && keyCode <= 123);

            if (isFKey) {
                if (typeof e.preventDefault === 'function') e.preventDefault();
                if (typeof e.stopPropagation === 'function') e.stopPropagation();
                if (keyCode >= 112 && keyCode <= 123) {
                    code = `F${keyCode - 111}`;
                }
            }

            let keyEl = document.querySelector(`.kb-key[data-code="${code}"]`);
            if (!keyEl && key) {
                keyEl = document.querySelector(`.kb-key[data-code="${key}"]`);
            }
            if (keyEl) {
                keyEl.classList.remove('active');
            }
            this.updateLockLEDs(e);
        },

        updateLockLEDs: function(e) {
            if (!e || typeof e.getModifierState !== 'function') return;
            const capsOn = e.getModifierState('CapsLock');
            const numOn = e.getModifierState('NumLock');
            const scrollOn = e.getModifierState('ScrollLock');

            const ledCaps = document.getElementById('kb-led-caps');
            const ledNum = document.getElementById('kb-led-num');
            const ledScroll = document.getElementById('kb-led-scroll');

            if (ledCaps) ledCaps.classList.toggle('active', capsOn);
            if (ledNum) ledNum.classList.toggle('active', numOn);
            if (ledScroll) ledScroll.classList.toggle('active', scrollOn);
        },

        formatKeyName: function(e, resolvedCode) {
            if (!e) return '-';
            const code = resolvedCode || e.code || '';
            const key = e.key || '';

            // Laptop Multimedia Keys Notice
            if (code.includes('AudioVolume') || code.includes('Brightness') || code.includes('Media')) {
                return `${key || code} (Laptop Fn aktif: F-tuşu için Fn tuşuna basılı tutun)`;
            }

            if (code === 'Space') return 'Space (Boşluk)';
            if (code === 'Enter') return 'Enter ↵';
            if (code === 'NumpadEnter') return 'Num Enter ↵';
            if (code === 'Backspace') return 'Backspace ⌫';
            if (code === 'Tab') return 'Tab ⇥';
            if (code === 'CapsLock') return 'Caps Lock';
            if (code === 'ShiftLeft') return 'Sol Shift ⇧';
            if (code === 'ShiftRight') return 'Sağ Shift ⇧';
            if (code === 'ControlLeft') return 'Sol Ctrl';
            if (code === 'ControlRight') return 'Sağ Ctrl';
            if (code === 'AltLeft') return 'Alt';
            if (code === 'AltRight') return 'Alt Gr';
            if (code === 'MetaLeft' || code === 'MetaRight') return 'Windows ⊞';
            if (code === 'ContextMenu') return 'Menu / Sağ Tık ≣';
            if (code.startsWith('Arrow')) {
                const dir = code.replace('Arrow', '');
                const map = { 'Up': 'Yukarı Ok ↑', 'Down': 'Aşağı Ok ↓', 'Left': 'Sol Ok ←', 'Right': 'Sağ Ok →' };
                return map[dir] || code;
            }
            if (code.startsWith('Key')) {
                return `${code.replace('Key', '')} (${key.toUpperCase()})`;
            }
            if (code.startsWith('Digit')) {
                return `${code.replace('Digit', '')} (${key})`;
            }
            if (code.startsWith('Numpad')) {
                return `Num ${code.replace('Numpad', '')} (${key})`;
            }
            return key ? `${key} (${code})` : code;
        },

        updateLastKey: function(name, code, keyCode) {
            const nameEl = document.getElementById('kb-last-key-display');
            const badgeEl = document.getElementById('kb-last-code-badge');
            if (nameEl) nameEl.textContent = name;
            if (badgeEl) badgeEl.textContent = `${code} [${keyCode || '-'}]`;
        },

        pushHistory: function(name, code) {
            this.keyHistory.unshift({ name, code });
            if (this.keyHistory.length > 12) this.keyHistory.pop();

            const stream = document.getElementById('kb-history-stream');
            if (!stream) return;

            stream.innerHTML = this.keyHistory.map((item, idx) => {
                const opacity = Math.max(0.35, 1 - (idx * 0.06));
                return `<span class="badge" style="background: rgba(0, 210, 255, 0.1); border: 1px solid rgba(0, 210, 255, 0.25); color: #00d2ff; font-size: 0.72rem; padding: 2px 7px; border-radius: 4px; opacity: ${opacity};" title="${item.code}">${this.escapeHtml(item.name)}</span>`;
            }).join('');
        },

        updateKeyboardStats: function() {
            const totalKeys = this.getTotalKeyCount();
            const testedCount = this.getTestedMatchingCount();
            const percent = totalKeys > 0 ? Math.round((testedCount / totalKeys) * 100) : 0;

            const countEl = document.getElementById('kb-tested-count');
            const totalEl = document.getElementById('kb-total-count');
            const percentEl = document.getElementById('kb-tested-percent');

            if (countEl) countEl.textContent = testedCount;
            if (totalEl) totalEl.textContent = totalKeys;
            if (percentEl) percentEl.textContent = `${percent}%`;
        },

        getTotalKeyCount: function() {
            const layout = KEY_LAYOUTS[this.keyboardLayout] || KEY_LAYOUTS['TR-Q'];
            let count = 0;
            const countSection = (sec) => {
                sec.forEach(row => {
                    row.forEach(k => {
                        if (k.code) count++;
                    });
                });
            };
            if (layout.main) countSection(layout.main);
            if (layout.nav) countSection(layout.nav);
            if (this.keyboardNumpadVisible && layout.numpad) {
                count += layout.numpad.length;
            }
            return count;
        },

        getTestedMatchingCount: function() {
            const layout = KEY_LAYOUTS[this.keyboardLayout] || KEY_LAYOUTS['TR-Q'];
            const allCodes = new Set();
            const collectSection = (sec) => {
                sec.forEach(row => {
                    row.forEach(k => {
                        if (k.code) allCodes.add(k.code);
                    });
                });
            };
            if (layout.main) collectSection(layout.main);
            if (layout.nav) collectSection(layout.nav);
            if (this.keyboardNumpadVisible && layout.numpad) {
                layout.numpad.forEach(k => allCodes.add(k.code));
            }

            let matched = 0;
            this.testedKeyCodes.forEach(code => {
                if (allCodes.has(code)) matched++;
            });
            return matched;
        },

        resetKeyboardTest: function() {
            this.testedKeyCodes.clear();
            this.keyHistory = [];

            document.querySelectorAll('.kb-key').forEach(el => {
                el.classList.remove('active', 'tested');
            });

            const stream = document.getElementById('kb-history-stream');
            if (stream) stream.innerHTML = '<span style="font-size: 0.8rem; color: rgba(255,255,255,0.3); font-style: italic;">Test sıfırlandı. Yeni tuşa basınız.</span>';

            const nameEl = document.getElementById('kb-last-key-display');
            const badgeEl = document.getElementById('kb-last-code-badge');
            if (nameEl) nameEl.textContent = '-';
            if (badgeEl) badgeEl.textContent = '-';

            this.updateKeyboardStats();
            this.showToast('Klavye testi sıfırlandı.', 'info');
        },

        toggleKeyboardLayout: function() {
            this.keyboardLayout = (this.keyboardLayout === 'TR-Q') ? 'US' : 'TR-Q';
            localStorage.setItem('kb_layout', this.keyboardLayout);
            this.updateLayoutToggleUI();
            this.renderKeyboard();
            this.updateKeyboardStats();
            this.showToast(`Klavye düzeni: ${this.keyboardLayout === 'TR-Q' ? 'Türkçe Q' : 'English US'}`, 'info');
        },

        updateLayoutToggleUI: function() {
            const nameEl = document.getElementById('kb-layout-name');
            if (nameEl) nameEl.textContent = (this.keyboardLayout === 'TR-Q') ? 'Türkçe Q' : 'English US';
        },

        toggleKeyboardNumpad: function() {
            this.keyboardNumpadVisible = !this.keyboardNumpadVisible;
            localStorage.setItem('kb_numpad_visible', String(this.keyboardNumpadVisible));
            this.updateNumpadToggleUI();
            this.renderKeyboard();
            this.updateKeyboardStats();
        },

        updateNumpadToggleUI: function() {
            const statusEl = document.getElementById('kb-numpad-status');
            if (statusEl) statusEl.textContent = this.keyboardNumpadVisible ? 'Numpad: Açık' : 'Numpad: Gizli (TKL)';
        },

        toggleKeyboardSound: function() {
            this.keyboardSoundEnabled = !this.keyboardSoundEnabled;
            localStorage.setItem('kb_sound_enabled', String(this.keyboardSoundEnabled));
            this.updateSoundToggleUI();
            this.showToast(this.keyboardSoundEnabled ? 'Klavye tıklama sesi açıldı.' : 'Klavye sesi kapatıldı.', 'info');
        },

        updateSoundToggleUI: function() {
            const iconEl = document.getElementById('kb-sound-icon');
            const statusEl = document.getElementById('kb-sound-status');
            if (iconEl) {
                iconEl.className = this.keyboardSoundEnabled ? 'fas fa-volume-high' : 'fas fa-volume-xmark';
                iconEl.style.color = this.keyboardSoundEnabled ? 'var(--accent)' : '#ef4444';
            }
            if (statusEl) statusEl.textContent = this.keyboardSoundEnabled ? 'Ses: Açık' : 'Ses: Kapalı';
        },

        playMechanicalSound: function() {
            if (!this.keyboardSoundEnabled) return;
            try {
                if (!this.audioCtx) {
                    const AudioCtx = window.AudioContext || window.webkitAudioContext;
                    if (AudioCtx) this.audioCtx = new AudioCtx();
                }
                if (this.audioCtx && this.audioCtx.state === 'suspended') {
                    this.audioCtx.resume();
                }
                if (!this.audioCtx) return;

                const now = this.audioCtx.currentTime;
                const osc = this.audioCtx.createOscillator();
                const gain = this.audioCtx.createGain();

                osc.type = 'triangle';
                osc.frequency.setValueAtTime(440, now);
                osc.frequency.exponentialRampToValueAtTime(110, now + 0.035);

                gain.gain.setValueAtTime(0.12, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);

                osc.connect(gain);
                gain.connect(this.audioCtx.destination);

                osc.start(now);
                osc.stop(now + 0.035);
            } catch (err) {}
        },

        renderKeyboard: function() {
            const container = document.getElementById('keyboard-wrapper');
            if (!container) return;

            const layout = KEY_LAYOUTS[this.keyboardLayout] || KEY_LAYOUTS['TR-Q'];

            const renderRow = (row) => {
                let html = '<div class="kb-row">';
                row.forEach(item => {
                    if (item.spacer) {
                        html += `<div class="kb-spacer ${item.spacer}"></div>`;
                    } else {
                        const code = item.code || '';
                        const isTested = this.testedKeyCodes.has(code);
                        const testedClass = isTested ? ' tested' : '';
                        const wClass = item.width || 'w-1';
                        const hClass = item.height || '';
                        
                        let labelHtml = '';
                        if (item.main && item.sub) {
                            labelHtml = `
                                <span class="kb-sub">${this.escapeHtml(item.sub)}</span>
                                <span class="kb-main">${this.escapeHtml(item.main)}</span>
                            `;
                        } else {
                            labelHtml = `<span class="kb-single">${this.escapeHtml(item.label || item.main || '')}</span>`;
                        }

                        html += `
                            <div class="kb-key ${wClass} ${hClass}${testedClass}" data-code="${code}" onclick="app.simulateKeyClick('${code}')" title="${code}">
                                ${labelHtml}
                            </div>
                        `;
                    }
                });
                html += '</div>';
                return html;
            };

            let mainHtml = `<div class="kb-section kb-main-section">${layout.main.map(renderRow).join('')}</div>`;
            let navHtml = `<div class="kb-section kb-nav-section">${layout.nav.map(renderRow).join('')}</div>`;
            
            let numpadHtml = '';
            if (this.keyboardNumpadVisible && layout.numpad) {
                let keysHtml = layout.numpad.map(item => {
                    const code = item.code || '';
                    const isTested = this.testedKeyCodes.has(code);
                    const testedClass = isTested ? ' tested' : '';
                    const gClass = item.gridClass ? ` ${item.gridClass}` : '';
                    return `
                        <div class="kb-key${gClass}${testedClass}" data-code="${code}" onclick="app.simulateKeyClick('${code}')" title="${code}">
                            <span class="kb-single">${this.escapeHtml(item.label || '')}</span>
                        </div>
                    `;
                }).join('');

                numpadHtml = `
                    <div class="kb-section kb-numpad-section" id="kb-numpad-section">
                        <div class="kb-leds-bar">
                            <div class="kb-led-item"><span class="kb-led-bulb" id="kb-led-num"></span> NUM</div>
                            <div class="kb-led-item"><span class="kb-led-bulb" id="kb-led-caps"></span> CAPS</div>
                            <div class="kb-led-item"><span class="kb-led-bulb" id="kb-led-scroll"></span> SCRL</div>
                        </div>
                        <div class="kb-numpad-grid">
                            ${keysHtml}
                        </div>
                    </div>
                `;
            }

            container.innerHTML = mainHtml + navHtml + numpadHtml;
        },

        simulateKeyClick: function(code) {
            this.handleKeyDown({
                code: code,
                key: code,
                keyCode: 0,
                preventDefault: () => {},
                stopPropagation: () => {}
            });
            setTimeout(() => {
                this.handleKeyUp({
                    code: code,
                    key: code,
                    keyCode: 0,
                    preventDefault: () => {},
                    stopPropagation: () => {}
                });
            }, 120);
        }
    };

    // Attach to app
    if (window.app) {
        Object.assign(window.app, KeyboardTester);
    } else {
        window.KeyboardTester = KeyboardTester;
    }
})();
