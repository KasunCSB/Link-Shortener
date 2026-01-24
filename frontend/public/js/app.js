// API Configuration
// Load runtime config from /config.json
let API_BASE = 'https://lnk-api.kasunc.live';

async function loadRuntimeConfig() {
    try {
        const res = await fetch('/config.json', {cache: 'no-store'});
        if (!res.ok) throw new Error('no config');
        const cfg = await res.json();
        if (typeof cfg.API_BASE === 'string' && cfg.API_BASE.trim()) {
            API_BASE = cfg.API_BASE;
        } else if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            API_BASE = 'http://localhost:8000';
        }
    } catch (e) {
        // fallback: if hostname indicates local, default to localhost API
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            API_BASE = 'http://localhost:8000';
        }
    }
}

// DOM Elements
const elements = {
    form: document.getElementById('shorten-form'),
    urlInput: document.getElementById('url-input'),
    shortenBtn: document.getElementById('shorten-btn'),
    btnText: document.querySelector('.btn-text'),
    btnLoader: document.querySelector('.btn-loader'),
    advancedToggle: document.getElementById('advanced-toggle'),
    advancedOptions: document.getElementById('advanced-options'),
    customSuffix: document.getElementById('custom-suffix'),
    suffixStatus: document.getElementById('suffix-status'),
    expiryDate: document.getElementById('expiry-date'),
    errorMessage: document.getElementById('error-message'),
    successModal: document.getElementById('success-modal'),
    modalClose: document.getElementById('modal-close'),
    resultLink: document.getElementById('result-link'),
    copyBtn: document.getElementById('copy-btn'),
    copyIcon: document.getElementById('copy-icon'),
    checkIcon: document.getElementById('check-icon'),
    qrCode: document.getElementById('qr-code'),
    expiresInfo: document.getElementById('expires-info'),
    createAnother: document.getElementById('create-another'),
    successAnimation: document.getElementById('success-animation')
};

// State
let suffixCheckTimeout = null;
let isSubmitting = false;

function parseExpiryDate(value) {
    if (!value) return null;
    let v = String(value).trim();
    if (!v) return null;
    if (v.includes(' ') && !v.includes('T')) {
        v = v.replace(' ', 'T');
    }
    const hasTz = /([zZ]|[+-]\d{2}:?\d{2})$/.test(v);
    return new Date(hasTz ? v : v + 'Z');
}

// Initialize
// Initialize after runtime config is loaded so API_BASE is correct
loadRuntimeConfig().then(() => {
    const init = () => {
        try {
            setupEventListeners();
            setupDateInput();
            checkForRedirectError();
        } catch (e) {
            // if elements not present, fail gracefully
            console.error('Initialization error', e);
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
});

function setupEventListeners() {
    // Form submission
    elements.form.addEventListener('submit', handleSubmit);
    
    // Advanced toggle
    elements.advancedToggle.addEventListener('click', toggleAdvancedOptions);
    
    // Custom suffix validation
    elements.customSuffix.addEventListener('input', handleSuffixInput);
    
    // Modal close
    elements.modalClose.addEventListener('click', closeSuccessModal);
    elements.successModal.querySelector('.modal-backdrop').addEventListener('click', closeSuccessModal);
    
    // Copy button
    elements.copyBtn.addEventListener('click', copyToClipboard);
    
    // Create another
    elements.createAnother.addEventListener('click', createAnotherLink);


    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeSuccessModal();
        }
    });
}

// Render a styled QR code using qr-code-styling when available, otherwise fall back to API image
let currentStyledQr = null;
function renderStyledQRCode(data) {
    // Clear previous
    elements.qrCode.innerHTML = '';

    // Fixed style: modules = dots, finder = rounded squares
    const dotsType = 'dots';

    if (window.QRCodeStyling) {
        try {
            currentStyledQr = new QRCodeStyling({
                width: 140,
                height: 140,
                data,
                dotsOptions: {
                    color: '#000000',
                    type: dotsType
                },
                cornersSquareOptions: {
                    color: '#000000',
                    type: 'rounded'
                },
                cornersDotOptions: {
                    color: '#000000',
                    type: 'rounded'
                },
                backgroundOptions: {
                    color: '#ffffff'
                },
                imageOptions: {
                    crossOrigin: 'anonymous',
                    margin: 0
                }
            });

            // Append to container
            currentStyledQr.append(elements.qrCode);
            return;
        } catch (e) {
            // fallthrough to image fallback
            console.warn('Styled QR render failed, falling back to static image', e);
        }
    }

    // Fallback: use external API image
    try {
        const img = document.createElement('img');
        img.alt = 'QR code';
        img.width = 140;
        img.height = 140;
        img.className = 'qr-img';
        img.src = `https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(data)}`;
        elements.qrCode.appendChild(img);
    } catch (e) {
        const p = document.createElement('p');
        p.textContent = data;
        p.className = 'qr-fallback';
        elements.qrCode.appendChild(p);
    }
}

function setupDateInput() {
    const today = new Date();
    const maxDate = new Date();
    maxDate.setFullYear(maxDate.getFullYear() + 1);
    
    elements.expiryDate.min = today.toISOString().split('T')[0];
    elements.expiryDate.max = maxDate.toISOString().split('T')[0];
}

function checkForRedirectError() {
    const urlParams = new URLSearchParams(window.location.search);
    const err = urlParams.get('error');
    if (err === 'notfound') {
        window.location.href = '/404.html';
    } else if (err === 'expired') {
        window.location.href = '/expired.html';
    }
} 

// Toggle Advanced Options
function toggleAdvancedOptions() {
    elements.advancedToggle.classList.toggle('active');
    elements.advancedOptions.classList.toggle('hidden');
}

// Suffix Validation
function handleSuffixInput(e) {
    const value = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
    e.target.value = value;
    
    if (suffixCheckTimeout) clearTimeout(suffixCheckTimeout);
    
    if (!value) {
        elements.suffixStatus.textContent = '';
        elements.suffixStatus.className = 'suffix-status';
        return;
    }
    
    if (value.length < 3) {
        elements.suffixStatus.textContent = 'Minimum 3 characters';
        elements.suffixStatus.className = 'suffix-status taken';
        return;
    }
    
    elements.suffixStatus.textContent = 'Checking...';
    elements.suffixStatus.className = 'suffix-status checking';
    
    suffixCheckTimeout = setTimeout(() => checkSuffixAvailability(value), 400);
}

async function checkSuffixAvailability(suffix) {
    try {
        const response = await fetch(`${API_BASE}/api/check/${suffix}`);
        const data = await response.json();
        
        if (data.available) {
            elements.suffixStatus.textContent = '✓ Available';
            elements.suffixStatus.className = 'suffix-status available';
        } else {
            elements.suffixStatus.textContent = '✗ Already taken';
            elements.suffixStatus.className = 'suffix-status taken';
        }
    } catch (error) {
        elements.suffixStatus.textContent = 'Could not verify';
        elements.suffixStatus.className = 'suffix-status';
    }
}

// Form Submission
async function handleSubmit(e) {
    e.preventDefault();
    
    if (isSubmitting) return;
    
    const url = elements.urlInput.value.trim();
    if (!url) return;
    
    // Validate URL
    if (!isValidUrl(url)) {
        showError('Please enter a valid URL including http:// or https://');
        return;
    }
    
    // Check custom suffix
    const customSuffix = elements.customSuffix.value.trim();
    if (customSuffix && customSuffix.length < 3) {
        showError('Custom suffix must be at least 3 characters');
        return;
    }
    
    isSubmitting = true;
    setLoadingState(true);
    hideError();
    
    try {
        // Map frontend fields to backend schema:
        // backend expects `custom_code` and `expires_in_days` (not `custom_suffix`/`expires_at`).
        const payload = { url };

        if (customSuffix) {
            payload.custom_code = customSuffix; // map to backend `custom_code`
        }

        if (elements.expiryDate.value) {
            // Convert selected expiry date to number of days from today as backend expects `expires_in_days`.
            const today = new Date();
            const selected = new Date(elements.expiryDate.value + 'T00:00:00');
            const msPerDay = 1000 * 60 * 60 * 24;
            const diffMs = selected - today;
            const diffDays = Math.ceil(diffMs / msPerDay);
            if (diffDays > 0) {
                // Cap to 365 days to match backend validation
                payload.expires_in_days = Math.min(diffDays, 365);
            }
        }
        
        const response = await fetch(`${API_BASE}/api/shorten`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            // Rate limit handling
            if (response.status === 429) {
                const retryAfter = response.headers.get('Retry-After');
                let msg = data.detail || data.error || 'Rate limit exceeded. Please try again later.';
                if (retryAfter) msg += ` Retry after ${retryAfter} seconds.`;
                throw new Error(msg);
            }

            throw new Error(data.detail || data.error || 'Failed to shorten URL');
        }

        showSuccessModal(data);
        
    } catch (error) {
        showError(error.message || 'Something went wrong. Please try again.');
    } finally {
        isSubmitting = false;
        setLoadingState(false);
    }
}

function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
        return false;
    }
}

function setLoadingState(loading) {
    elements.shortenBtn.disabled = loading;
    elements.btnText.classList.toggle('hidden', loading);
    elements.btnLoader.classList.toggle('hidden', !loading);
}

// Error Handling
function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorMessage.classList.remove('hidden');
}

function hideError() {
    elements.errorMessage.classList.add('hidden');
}

// Success Modal
function showSuccessModal(data) {
    const shortUrl = data.short_url;
    elements.resultLink.value = shortUrl;
    
    // Generate QR Code using styled renderer when available (fallback to image service)
    elements.qrCode.innerHTML = '';
    renderStyledQRCode(shortUrl);
    
    // Expiry info
    if (data.expires_at) {
        const expiryDate = parseExpiryDate(data.expires_at);
        if (!expiryDate || isNaN(expiryDate.getTime())) {
            elements.expiresInfo.textContent = `Expires at ${data.expires_at}`;
        } else {
            elements.expiresInfo.textContent = `Expires on ${expiryDate.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            })}`;
        }
    } else {
        elements.expiresInfo.textContent = 'This link never expires';
    }
    
    elements.successModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Play animation
    if (elements.successAnimation) {
        elements.successAnimation.stop();
        elements.successAnimation.play();
    }
}

function closeSuccessModal() {
    elements.successModal.classList.add('hidden');
    document.body.style.overflow = '';
    resetCopyButton();
}

function createAnotherLink() {
    closeSuccessModal();
    elements.form.reset();
    elements.customSuffix.value = '';
    elements.suffixStatus.textContent = '';
    elements.suffixStatus.className = 'suffix-status';
    elements.urlInput.focus();
    
    if (!elements.advancedOptions.classList.contains('hidden')) {
        toggleAdvancedOptions();
    }
}

// Copy to Clipboard
async function copyToClipboard() {
    try {
        await navigator.clipboard.writeText(elements.resultLink.value);
        
        elements.copyBtn.classList.add('copied');
        elements.copyIcon.classList.add('hidden');
        elements.checkIcon.classList.remove('hidden');
        
        setTimeout(resetCopyButton, 2000);
    } catch (error) {
        // Fallback
        elements.resultLink.select();
        document.execCommand('copy');
    }
}

function resetCopyButton() {
    elements.copyBtn.classList.remove('copied');
    elements.copyIcon.classList.remove('hidden');
    elements.checkIcon.classList.add('hidden');
}
