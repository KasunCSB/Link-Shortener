// API Configuration
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://lnk-api.kasunc.live';

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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setupDateInput();
    checkForRedirectError();
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

function setupDateInput() {
    const today = new Date();
    const maxDate = new Date();
    maxDate.setFullYear(maxDate.getFullYear() + 1);
    
    elements.expiryDate.min = today.toISOString().split('T')[0];
    elements.expiryDate.max = maxDate.toISOString().split('T')[0];
}

function checkForRedirectError() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('error') === 'notfound') {
        // Redirect to 404 page
        window.location.href = '/404.html';
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
        const payload = { url };
        
        if (customSuffix) {
            payload.custom_suffix = customSuffix;
        }
        
        if (elements.expiryDate.value) {
            payload.expires_at = elements.expiryDate.value;
        }
        
        const response = await fetch(`${API_BASE}/api/shorten`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to shorten URL');
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
    
    // Generate QR Code
    elements.qrCode.innerHTML = '';
    QRCode.toCanvas(shortUrl, {
        width: 140,
        margin: 2,
        color: { dark: '#1d4ed8', light: '#ffffff' }
    }, (error, canvas) => {
        if (!error) elements.qrCode.appendChild(canvas);
    });
    
    // Expiry info
    if (data.expires_at) {
        const expiryDate = new Date(data.expires_at);
        elements.expiresInfo.textContent = `Expires on ${expiryDate.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        })}`;
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
