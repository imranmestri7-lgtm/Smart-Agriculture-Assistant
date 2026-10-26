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

    const getVal = (id) => document.getElementById(id).value;

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Prevent duplicate submissions
        if (submitBtn.disabled) return;

        // Prepare result area
        resultDiv.replaceChildren();
        resultDiv.style.display = 'block';
        resultDiv.textContent = 'Loading...';

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

        try {
            const resp = await fetch('/api/crop/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            // Attempt to parse JSON response safely
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

            // Clear loading message
            resultDiv.textContent = '';

            if (parseError) {
                const errMsg = document.createElement('p');
                errMsg.textContent = 'Unexpected response from server. Please try again later.';
                resultDiv.appendChild(errMsg);
            } else if (resp.ok && result.status === 'success') {
                const title = document.createElement('h3');
                title.textContent = 'Recommended Crop';
                const crop = document.createElement('p');
                crop.textContent = result.recommendation || 'No recommendation returned';
                resultDiv.appendChild(title);
                resultDiv.appendChild(crop);

                if (result.details) {
                    const details = document.createElement('pre');
                    details.textContent = JSON.stringify(result.details, null, 2);
                    resultDiv.appendChild(details);
                }
            } else {
                const errMsg = document.createElement('p');
                errMsg.textContent = (result && result.message) || 'Failed to get recommendation';
                resultDiv.appendChild(errMsg);
            }

        } catch (err) {
            console.error('Crop recommendation error:', err);
            resultDiv.textContent = 'Network error while requesting recommendation.';
        } finally {
            // Re‑enable button
            submitBtn.disabled = false;
            submitBtn.removeAttribute('aria-disabled');
        }
    });
});