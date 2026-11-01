// Crop recommendation client-side script
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('cropForm');
    if (!form) return;

    const submitBtn = form.querySelector('button.recommend-button');
    const resultDiv = document.getElementById('cropResult');
    if (!submitBtn || !resultDiv) {
        console.warn('Crop form UI elements missing');
        return;
    }

    let lastResult = null;

    function t(key, fallback) {
        if (window.i18n && typeof window.i18n.t === 'function') {
            const val = window.i18n.t(key);
            if (val && val !== key) return val;
        }
        return fallback || key;
    }

    function renderCropResult(result) {
        resultDiv.replaceChildren();
        if (!result) return;

        if (result.isError) {
            const errMsg = document.createElement('p');
            errMsg.textContent = result.message;
            resultDiv.appendChild(errMsg);
            return;
        }

        const title = document.createElement('h3');
        title.setAttribute('data-i18n', 'recommended_crop_title');
        title.textContent = t('recommended_crop_title', 'Recommended Crop');

        const crop = document.createElement('p');
        crop.textContent = result.recommendation || t('no_crop_rec_returned', 'No recommendation returned');

        resultDiv.appendChild(title);
        resultDiv.appendChild(crop);

        if (result.details) {
            const details = document.createElement('pre');
            details.textContent = typeof result.details === 'string'
                ? result.details
                : JSON.stringify(result.details, null, 2);
            resultDiv.appendChild(details);
        }
    }

    const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value : '';
    };

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Prevent duplicate submissions
        if (submitBtn.disabled) return;

        // Prepare result area
        resultDiv.replaceChildren();
        resultDiv.style.display = 'block';
        resultDiv.textContent = t('loading_crop_rec', 'Loading recommendation...');

        // Disable button during request
        submitBtn.disabled = true;
        submitBtn.setAttribute('aria-disabled', 'true');

        const data = {
            nitrogen: getVal('nitrogen'),
            phosphorus: getVal('phosphorus'),
            potassium: getVal('potassium'),
            ph: getVal('ph'),
            temperature: getVal('temperature'),
            humidity: getVal('humidity'),
            rainfall: getVal('rainfall'),
            location: getVal('location')
        };

        const activeLang = (window.i18n && window.i18n.currentLang) || localStorage.getItem('lang') || 'en';

        try {
            const resp = await fetch('/api/crop/recommend', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-Language': activeLang
                },
                body: JSON.stringify(data)
            });

            let result = null;
            let parseError = false;
            const contentType = resp.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                try {
                    result = await resp.json();
                } catch (e) {
                    parseError = true;
                }
            } else {
                parseError = true;
            }

            resultDiv.textContent = '';

            if (parseError) {
                lastResult = {
                    isError: true,
                    message: t('err_unexpected_response', 'Unexpected response from server. Please try again later.')
                };
            } else if (resp.ok && result.status === 'success') {
                lastResult = result;
            } else {
                lastResult = {
                    isError: true,
                    message: (result && result.message) || t('err_crop_rec_failed', 'Failed to get crop recommendation')
                };
            }

            renderCropResult(lastResult);

        } catch (err) {
            console.error('Crop recommendation error:', err);
            lastResult = {
                isError: true,
                message: t('err_network', 'Network error while requesting recommendation.')
            };
            renderCropResult(lastResult);
        } finally {
            submitBtn.disabled = false;
            submitBtn.removeAttribute('aria-disabled');
        }
    });

    window.addEventListener('languageChanged', function () {
        if (lastResult) {
            renderCropResult(lastResult);
        }
    });
});
