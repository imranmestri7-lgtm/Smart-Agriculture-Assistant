
 // =====================================================
 // AGRISMART - PLANT DISEASE DETECTION
 // Flask API + TensorFlow model + farmer follow-up
 // =====================================================

const API_URL = "/api/disease/predict";
const RECOMMEND_API_URL = "/api/disease/recommend";
const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const LOW_CONFIDENCE_LIMIT = 60;

// HTML elements
const leafImage = document.getElementById("leafImage");
const uploadArea = document.querySelector(".upload-area");
const imagePreview = document.getElementById("imagePreview");
const previewImage = document.getElementById("previewImage");
const cameraButton = document.getElementById("cameraButton");
const cameraContainer = document.getElementById("cameraContainer");
const camera = document.getElementById("camera");
const captureButton = document.getElementById("captureButton");
const closeCameraButton = document.getElementById("closeCameraButton");
const analyzeButton = document.getElementById("analyzeButton");
const cropSelect = document.getElementById("crop");
const scanAgainButton = document.getElementById("scanAgainButton");

// Application state
let selectedFile = null;
let cameraStream = null;
let previewObjectUrl = null;
let lastPredictionData = null;

// =====================================================
// CREATE RESULT SECTION
// =====================================================

const resultSection = document.createElement("section");
resultSection.id = "predictionResult";

resultSection.style.cssText = `
    display: none;
    max-width: 900px;
    margin: 30px auto;
    padding: 28px;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 5px 22px rgba(0, 0, 0, 0.10);
`;

resultSection.innerHTML = `
    <h2 style="margin-bottom: 20px; color: #245c32;">
        🌿 Disease Prediction Result
    </h2>

    <div style="
        display: flex;
        flex-wrap: wrap;
        gap: 24px;
        align-items: flex-start;
    ">
        <div style="flex: 1; min-width: 220px;">
            <img
                id="resultImage"
                alt="Analyzed plant image"
                style="
                    width: 100%;
                    max-width: 320px;
                    border-radius: 12px;
                    object-fit: contain;
                "
            >
        </div>

        <div style="flex: 2; min-width: 250px;">
            <p style="color: #666; margin-bottom: 8px;">
                Predicted class
            </p>

            <h3
                id="diseaseName"
                style="
                    color: #245c32;
                    font-size: 23px;
                    margin-bottom: 18px;
                    overflow-wrap: anywhere;
                "
            >--</h3>

            <p style="margin-bottom: 8px;">
                Model confidence:
                <strong id="confidence">--</strong>
            </p>

            <div style="
                height: 12px;
                background: #e5e7eb;
                border-radius: 10px;
                overflow: hidden;
                margin-bottom: 22px;
            ">
                <div
                    id="confidenceBar"
                    style="
                        width: 0%;
                        height: 100%;
                        background: #2e7d32;
                        transition: width 0.5s ease;
                    "
                ></div>
            </div>

            <h4 style="margin-bottom: 12px;">
                Other possible predictions
            </h4>

            <div id="topPredictions"></div>
        </div>
    </div>

    <div
        id="lowConfidenceWarning"
        role="status"
        style="
            display: none;
            margin-top: 22px;
            padding: 16px;
            background: #fff3cd;
            color: #664d03;
            border-radius: 10px;
            line-height: 1.6;
        "
    >
        <strong>⚠️ The prediction is uncertain.</strong>
        <p style="margin-top: 8px;">
            The model confidence is below 60%. Please answer the
            questions below to provide more information. Your answers
            do not confirm a disease, and the model prediction will
            not change based on these answers.
        </p>
    </div>

    <div
        id="farmerFollowUp"
        style="
            display: none;
            margin-top: 22px;
            padding: 20px;
            border: 1px solid #dce8dc;
            border-radius: 12px;
        "
    >
        <h3 style="color: #245c32; margin-bottom: 8px;">
            🌱 Tell us about your plant
        </h3>

        <p style="margin-bottom: 18px; line-height: 1.6;">
            Don't know the disease name? That's okay. Answer what you
            know, or select "Not sure".
        </p>

        <form id="farmerQuestionsForm">
            <label for="farmerPlant" style="display:block; margin-bottom:6px;">
                1. Which plant or fruit is affected?
            </label>
            <select
                id="farmerPlant"
                name="plant"
                style="width:100%; padding:11px; margin-bottom:16px;"
                required
            >
                <option value="">Choose or select not sure</option>
                <option>Tomato</option>
                <option>Potato</option>
                <option>Corn / Maize</option>
                <option>Apple</option>
                <option>Strawberry</option>
                <option>Other plant or fruit</option>
                <option>Not sure</option>
            </select>

            <label for="farmerSymptoms" style="display:block; margin-bottom:6px;">
                2. What do you see on the plant?
            </label>
            <select
                id="farmerSymptoms"
                name="symptoms"
                style="width:100%; padding:11px; margin-bottom:16px;"
                required
            >
                <option value="">Choose a symptom</option>
                <option>Brown or black spots</option>
                <option>Yellow leaves</option>
                <option>Curled or wilting leaves</option>
                <option>Rotting fruit or stem</option>
                <option>Insects or holes in leaves</option>
                <option>Other symptoms</option>
                <option>Not sure</option>
            </select>

            <label for="farmerDuration" style="display:block; margin-bottom:6px;">
                3. When did you first notice the problem?
            </label>
            <select
                id="farmerDuration"
                name="duration"
                style="width:100%; padding:11px; margin-bottom:16px;"
                required
            >
                <option value="">Choose a duration</option>
                <option>Within the last 1–3 days</option>
                <option>About one week ago</option>
                <option>More than one week ago</option>
                <option>Not sure</option>
            </select>

            <label for="farmerSpread" style="display:block; margin-bottom:6px;">
                4. How much of the plant is affected?
            </label>
            <select
                id="farmerSpread"
                name="spread"
                style="width:100%; padding:11px; margin-bottom:18px;"
                required
            >
                <option value="">Choose an answer</option>
                <option>Only one leaf or fruit</option>
                <option>Several leaves or fruits</option>
                <option>Most of the plant</option>
                <option>Many plants are affected</option>
                <option>Not sure</option>
            </select>

            <button
                type="submit"
                style="
                    padding: 12px 20px;
                    background: #2e7d32;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 15px;
                "
            >
                Submit Answers
            </button>
        </form>

        <div
            id="farmerAnswersResult"
            role="status"
            style="
                display: none;
                margin-top: 20px;
                padding: 16px;
                background: #e8f5e9;
                border-radius: 8px;
                line-height: 1.8;
            "
        ></div>

        <p style="margin-top:14px; color:#666; font-size:13px; line-height:1.5;">
            These answers are displayed on this page only. They are not
            saved to the database or used to change the model prediction.
        </p>
    </div>

    <p
        id="predictionDisclaimer"
        style="
            margin-top: 22px;
            padding: 14px;
            background: #fff8e1;
            border-radius: 8px;
            color: #66551a;
            line-height: 1.6;
        "
    ></p>
`;

const scannerSection = document.getElementById("scanner");

if (scannerSection) {
    scannerSection.insertAdjacentElement("afterend", resultSection);
}

// =====================================================
// MESSAGES
// =====================================================

function showMessage(message, type = "error") {
    let messageBox = document.getElementById("diseaseMessage");

    if (!messageBox) {
        messageBox = document.createElement("div");
        messageBox.id = "diseaseMessage";

        messageBox.style.cssText = `
            padding: 14px;
            margin: 16px 0;
            border-radius: 8px;
            line-height: 1.5;
            overflow-wrap: anywhere;
        `;

        if (analyzeButton) {
            analyzeButton.insertAdjacentElement("afterend", messageBox);
        } else if (scannerSection) {
            scannerSection.appendChild(messageBox);
        }
    }

    messageBox.textContent = message;
    messageBox.style.background =
        type === "success" ? "#e8f5e9" : "#ffebee";
    messageBox.style.color =
        type === "success" ? "#1b5e20" : "#b71c1c";
    messageBox.style.display = "block";
}

function clearMessage() {
    const messageBox = document.getElementById("diseaseMessage");

    if (messageBox) {
        messageBox.style.display = "none";
        messageBox.textContent = "";
    }
}

// =====================================================
// IMAGE PREVIEW
// =====================================================

function clearPreviewUrl() {
    if (previewObjectUrl) {
        URL.revokeObjectURL(previewObjectUrl);
        previewObjectUrl = null;
    }
}

function displaySelectedImage(file) {
    clearPreviewUrl();

    previewObjectUrl = URL.createObjectURL(file);

    if (previewImage) {
        previewImage.src = previewObjectUrl;
    }

    if (imagePreview) {
        imagePreview.style.display = "flex";
    }

    if (uploadArea) {
        uploadArea.style.display = "none";
    }

    resultSection.style.display = "none";
    clearMessage();
}

function handleImage(file) {
    clearMessage();

    if (!file.type.startsWith("image/")) {
        showMessage("Please select a valid image file.");
        return;
    }

    if (file.size > MAX_IMAGE_SIZE) {
        showMessage("Image size must be less than 5 MB.");
        return;
    }

    selectedFile = file;
    displaySelectedImage(file);

    // Keep the existing crop selection optional.
}

// =====================================================
// FILE INPUT
// =====================================================

if (leafImage) {
    leafImage.addEventListener("change", function () {
        const file = this.files[0];

        if (file) {
            handleImage(file);
        }
    });
}

// =====================================================
// DRAG AND DROP
// =====================================================

if (uploadArea) {
    uploadArea.addEventListener("dragover", function (event) {
        event.preventDefault();
        uploadArea.style.borderColor = "#2e7d32";
    });

    uploadArea.addEventListener("dragleave", function () {
        uploadArea.style.borderColor = "";
    });

    uploadArea.addEventListener("drop", function (event) {
        event.preventDefault();
        uploadArea.style.borderColor = "";

        const file = event.dataTransfer.files[0];

        if (file) {
            handleImage(file);
        }
    });
}

// =====================================================
// CAMERA
// =====================================================

if (cameraButton) {
    cameraButton.addEventListener("click", async function () {
        clearMessage();

        if (
            !navigator.mediaDevices ||
            !navigator.mediaDevices.getUserMedia
        ) {
            showMessage(
                "Camera access is unavailable. Open the website using localhost or HTTPS."
            );
            return;
        }

        if (!camera || !cameraContainer) {
            showMessage("The camera elements could not be found on this page.");
            return;
        }

        try {
            stopCamera();

            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" },
                audio: false
            });

            camera.srcObject = cameraStream;
            cameraContainer.style.display = "block";

            await camera.play();

            cameraContainer.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });
        } catch (error) {
            console.error("Camera error:", error);

            showMessage(
                "Unable to access the camera. Please allow camera permission or upload an image instead."
            );
        }
    });
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(function (track) {
            track.stop();
        });

        cameraStream = null;
    }

    if (camera) {
        camera.srcObject = null;
    }

    if (cameraContainer) {
        cameraContainer.style.display = "none";
    }
}

if (closeCameraButton) {
    closeCameraButton.addEventListener("click", stopCamera);
}

// =====================================================
// CAPTURE IMAGE FROM CAMERA
// =====================================================

if (captureButton) {
    captureButton.addEventListener("click", function () {
        if (!cameraStream || !camera || !camera.videoWidth) {
            showMessage("Please wait for the camera to start.");
            return;
        }

        const canvas = document.createElement("canvas");
        canvas.width = camera.videoWidth;
        canvas.height = camera.videoHeight;

        const context = canvas.getContext("2d");

        if (!context) {
            showMessage("Could not prepare the camera image. Please try again.");
            return;
        }

        context.drawImage(
            camera,
            0,
            0,
            canvas.width,
            canvas.height
        );

        canvas.toBlob(function (blob) {
            if (!blob) {
                showMessage("Could not capture the image. Please try again.");
                return;
            }

            const file = new File(
                [blob],
                "captured_leaf.jpg",
                { type: "image/jpeg" }
            );

            handleImage(file);
            stopCamera();
        }, "image/jpeg", 0.92);
    });
}

// =====================================================
// FORMAT MODEL CLASS NAME
// =====================================================

function formatClassName(className) {
    return String(className || "Unknown")
        .replace(/___/g, " — ")
        .replace(/_/g, " ");
}

// =====================================================
// DISPLAY TOP PREDICTIONS
// =====================================================

function displayTopPredictions(predictions) {
    const container = document.getElementById("topPredictions");

    if (!container) {
        return;
    }

    container.replaceChildren();

    if (!Array.isArray(predictions) || predictions.length === 0) {
        container.textContent = "No additional predictions available.";
        return;
    }

    predictions.forEach(function (item) {
        const row = document.createElement("div");

        row.style.cssText = `
            display: flex;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #eeeeee;
        `;

        const name = document.createElement("span");
        name.textContent = formatClassName(item.class_name);
        name.style.overflowWrap = "anywhere";

        const score = document.createElement("strong");
        const itemConfidence = Number(item.confidence);
        score.textContent = Number.isFinite(itemConfidence)
            ? `${itemConfidence.toFixed(2)}%`
            : "N/A";

        row.appendChild(name);
        row.appendChild(score);
        container.appendChild(row);
    });
}

// =====================================================
// SHOW PREDICTION AND LOW-CONFIDENCE QUESTIONS
// =====================================================

function showResult(data) {
    lastPredictionData = data;

    const prediction = data.prediction;
    const confidence = Number(prediction.confidence);

    if (!Number.isFinite(confidence)) {
        throw new Error("The model returned an invalid confidence value.");
    }

    document.getElementById("resultImage").src = previewImage.src;

    document.getElementById("diseaseName").textContent =
        formatClassName(prediction.class_name);

    document.getElementById("confidence").textContent =
        `${confidence.toFixed(2)}%`;

    document.getElementById("confidenceBar").style.width =
        `${Math.min(100, Math.max(0, confidence))}%`;

    const warning = document.getElementById("lowConfidenceWarning");
    const followUp = document.getElementById("farmerFollowUp");
    const answersResult = document.getElementById("farmerAnswersResult");
    const questionsForm = document.getElementById("farmerQuestionsForm");

    const isLowConfidence = confidence < LOW_CONFIDENCE_LIMIT;

warning.style.display = isLowConfidence ? "block" : "none";
followUp.style.display = "block";
    answersResult.style.display = "none";
    answersResult.replaceChildren();

    if (questionsForm) {
        questionsForm.reset();
    }

    document.getElementById("predictionDisclaimer").textContent =
        data.disclaimer ||
        "This is a model prediction, not a confirmed diagnosis. Verify the symptoms before choosing a treatment.";

    displayTopPredictions(data.top_predictions);

    resultSection.style.display = "block";

    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

// =====================================================
// FARMER FOLLOW-UP FORM
// Answers are displayed only; not saved or diagnosed.
// =====================================================


const farmerQuestionsForm = document.getElementById("farmerQuestionsForm");

if (farmerQuestionsForm) {
    farmerQuestionsForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        clearMessage();

        if (!lastPredictionData || !lastPredictionData.prediction) {
            showMessage("Please analyze a plant image first.");
            return;
        }

        const answers = {
            plant: document.getElementById("farmerPlant").value,
            symptoms: document.getElementById("farmerSymptoms").value,
            duration: document.getElementById("farmerDuration").value,
            spread: document.getElementById("farmerSpread").value
        };

        const resultBox = document.getElementById("farmerAnswersResult");
        const submitButton = farmerQuestionsForm.querySelector(
            'button[type="submit"]'
        );

        const originalButtonText = submitButton.textContent;

        submitButton.disabled = true;
        submitButton.textContent = "Generating recommendations...";

        resultBox.style.display = "block";
        resultBox.replaceChildren();

        const loading = document.createElement("p");
        loading.textContent = "Please wait while AgriSmart prepares suggestions...";
        resultBox.appendChild(loading);

        try {
            const response = await fetch(RECOMMEND_API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    prediction: lastPredictionData.prediction,
                    top_predictions: lastPredictionData.top_predictions || [],
                    answers: answers
                })
            });

            const result = await response.json();

            if (!response.ok || result.status !== "success") {
                throw new Error(
                    result.message || "Could not generate recommendations."
                );
            }

            resultBox.replaceChildren();

            function addHeading(text) {
                const heading = document.createElement("h4");
                heading.textContent = text;
                heading.style.margin = "16px 0 8px";
                resultBox.appendChild(heading);
            }

            function addParagraph(text) {
                const paragraph = document.createElement("p");
                paragraph.textContent = text || "";
                resultBox.appendChild(paragraph);
            }

            function addList(title, items) {
                if (!Array.isArray(items) || items.length === 0) {
                    return;
                }

                addHeading(title);

                const list = document.createElement("ul");
                list.style.paddingLeft = "22px";

                items.forEach(function (item) {
                    const listItem = document.createElement("li");
                    listItem.textContent = item;
                    listItem.style.marginBottom = "8px";
                    list.appendChild(listItem);
                });

                resultBox.appendChild(list);
            }

            addHeading("🌱 AgriSmart Recommendations");
            addParagraph(result.assessment);

            addList("What you can do now", result.recommendations);
            addList("What to avoid", result.actions_to_avoid);
            addList("Follow-up questions", result.follow_up_questions);

            addHeading("Next step");
            addParagraph(result.next_step);

            const disclaimer = document.createElement("p");
            disclaimer.textContent = result.disclaimer ||
                "These suggestions do not confirm a plant disease.";
            disclaimer.style.marginTop = "16px";
            disclaimer.style.fontSize = "13px";
            disclaimer.style.color = "#66551a";
            resultBox.appendChild(disclaimer);

            resultBox.scrollIntoView({
                behavior: "smooth",
                block: "nearest"
            });

        } catch (error) {
            console.error("Recommendation error:", error);

            resultBox.replaceChildren();

            const errorText = document.createElement("p");
            errorText.textContent = error.message.includes("Failed to fetch")
                ? "Cannot connect to the recommendation API. Please check that the AgriSmart backend is running."
                : error.message || "Unable to generate recommendations.";

            resultBox.appendChild(errorText);
            resultBox.style.background = "#ffebee";

        } finally {
            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;
        }
    });
}


// =====================================================
// CALL THE FLASK PREDICTION API
// =====================================================

if (analyzeButton) {
    analyzeButton.addEventListener("click", async function () {
        clearMessage();

        if (!selectedFile) {
            showMessage(
                "Please upload a plant image or capture one using the camera."
            );
            return;
        }

        const originalButtonText = analyzeButton.textContent;

        // Preserve original text and disable button
        analyzeButton.disabled = true;
        analyzeButton.dataset.originalText = analyzeButton.textContent;
        // Set visible analyzing label
        analyzeButton.textContent = "⏳ Analyzing image...";
        // Insert visible loading spinner for accessibility
        const spinner = document.createElement('span');
        spinner.className = 'loading-spinner';
        spinner.setAttribute('role', 'status');
        spinner.setAttribute('aria-live', 'polite');
        spinner.textContent = 'Analyzing...';
        analyzeButton.prepend(spinner);

        try {
            const formData = new FormData();
            formData.append("image", selectedFile);

            const token = localStorage.getItem("agriSmartToken");
            const headers = token
                ? { "Authorization": `Bearer ${token}` }
                : {};

            const response = await fetch(API_URL, {
                method: "POST",
                headers,
                body: formData
            });

            let data;

            try {
                data = await response.json();
            } catch {
                throw new Error("The backend returned an invalid response.");
            }

            if (!response.ok) {
                throw new Error(data.message || "Disease prediction failed.");
            }

            if (
                data.status !== "success" ||
                !data.prediction ||
                !data.prediction.class_name
            ) {
                throw new Error(
                    "The backend did not return a valid prediction."
                );
            }

            showResult(data);
            if (data.history_saved && typeof loadDiagnosisHistory === "function") {
                loadDiagnosisHistory();
            }
        } catch (error) {
            console.error("Disease prediction error:", error);

            const errorMessage = error.message || "An unexpected error occurred.";

            showMessage(
                errorMessage.includes("Failed to fetch")
                    ? `Cannot connect to the Flask backend at ${API_URL}.`
                    : errorMessage
            );
        } finally {
            // Remove spinner and restore button text
            const spinner = analyzeButton.querySelector('.loading-spinner');
            if (spinner) { spinner.remove(); }
            analyzeButton.disabled = false;
            analyzeButton.textContent = originalButtonText;
        }
    });
}

// =====================================================
// SCAN ANOTHER LEAF
// =====================================================

if (scanAgainButton) {
    scanAgainButton.addEventListener("click", function () {
        selectedFile = null;

        if (leafImage) {
            leafImage.value = "";
        }

        clearPreviewUrl();

        if (previewImage) {
            previewImage.src = "";
        }

        if (imagePreview) {
            imagePreview.style.display = "none";
        }

        if (uploadArea) {
            uploadArea.style.display = "";
        }

        resultSection.style.display = "none";

        const questionsForm = document.getElementById("farmerQuestionsForm");

        if (questionsForm) {
            questionsForm.reset();
        }

        const answersResult = document.getElementById("farmerAnswersResult");

        if (answersResult) {
            answersResult.replaceChildren();
            answersResult.style.display = "none";
        }

        stopCamera();
        clearMessage();

        if (cropSelect) {
            cropSelect.value = "";
        }

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    });
}


// =====================================================
// AUTHENTICATED DIAGNOSIS HISTORY
// =====================================================

const HISTORY_API_URL = "/api/disease/history";

function t(key, fallback) {
    if (window.i18n && typeof window.i18n.t === "function") {
        return window.i18n.t(key);
    }
    return fallback || key;
}

// Global modal close handler
function closeDiagnosisModal() {
    const modal = document.getElementById("diagnosisDetailModal");
    if (modal) {
        modal.style.display = "none";
    }
}

// Show full diagnosis detail modal
function openDiagnosisDetailModal(item) {
    const modal = document.getElementById("diagnosisDetailModal");
    const content = document.getElementById("diagnosisDetailContent");
    if (!modal || !content) return;

    const symptomsHtml = Array.isArray(item.symptoms) && item.symptoms.length > 0
        ? `<div style="margin-top:12px;"><strong style="color:#1e293b;">🔍 Symptoms:</strong><ul style="margin:4px 0 0 20px; font-size:14px; color:#475569;">${item.symptoms.map(s => `<li>${escapeHtml(s)}</li>`).join("")}</ul></div>`
        : "";

    const preventionHtml = Array.isArray(item.prevention) && item.prevention.length > 0
        ? `<div style="margin-top:12px;"><strong style="color:#1e293b;">🛡️ ${escapeHtml(t("prevention_summary", "Prevention Advice"))}:</strong><ul style="margin:4px 0 0 20px; font-size:14px; color:#475569;">${item.prevention.map(p => `<li>${escapeHtml(p)}</li>`).join("")}</ul></div>`
        : "";

    const treatmentHtml = Array.isArray(item.safe_treatment) && item.safe_treatment.length > 0
        ? `<div style="margin-top:12px;"><strong style="color:#1e293b;">💊 ${escapeHtml(t("treatment_summary", "Recommended Treatment"))}:</strong><ul style="margin:4px 0 0 20px; font-size:14px; color:#475569;">${item.safe_treatment.map(t => `<li>${escapeHtml(t)}</li>`).join("")}</ul></div>`
        : "";

    const token = localStorage.getItem("agriSmartToken") || localStorage.getItem("token") || "";
    const imageTag = item.image_url
        ? `<div style="margin-bottom:18px; text-align:center;"><img src="${escapeHtml(item.image_url)}${token ? `?token=${encodeURIComponent(token)}` : ''}" alt="${escapeHtml(item.display_name)}" style="max-height:220px; border-radius:12px; border:1px solid #e2e8f0; object-fit:cover;"></div>`
        : `<div style="width:100%; height:80px; background:#f0fdf4; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:36px; margin-bottom:16px;">🌱</div>`;

    const parsedDate = item.diagnosis_date ? new Date(item.diagnosis_date).toLocaleString() : "Date unavailable";

    content.innerHTML = `
        <button type="button" onclick="closeDiagnosisModal()" style="position:absolute; top:20px; right:20px; background:#f1f5f9; border:none; border-radius:50%; width:36px; height:36px; font-size:18px; font-weight:700; cursor:pointer; color:#64748b;">✕</button>
        ${imageTag}
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
            <span style="background:#dbeafe; color:#1d4ed8; font-weight:700; font-size:12px; padding:4px 12px; border-radius:12px;">
                ${escapeHtml(item.crop_name || "Plant Crop")}
            </span>
            <span style="background:#dcfce7; color:#15803d; font-weight:800; font-size:13px; padding:4px 12px; border-radius:12px;">
                ${item.confidence != null ? `${Number(item.confidence).toFixed(1)}% ${escapeHtml(t("confidence_label", "Confidence"))}` : ""}
            </span>
        </div>
        <h2 style="color:#15803d; margin:0 0 8px 0; font-size:22px;">
            ${escapeHtml(item.display_name || item.predicted_class || "Plant Condition")}
        </h2>
        <p style="color:#64748b; font-size:13px; margin:0 0 14px 0;">📅 ${escapeHtml(parsedDate)}</p>
        
        ${item.description ? `<p style="font-size:14px; line-height:1.6; color:#334155; background:#f8fafc; padding:12px 14px; border-radius:10px; border-left:4px solid #15803d;">${escapeHtml(item.description)}</p>` : ""}

        ${symptomsHtml}
        ${preventionHtml}
        ${treatmentHtml}

        ${item.disclaimer ? `<p style="margin-top:18px; font-size:12px; color:#94a3b8; font-style:italic; line-height:1.5;">⚠️ ${escapeHtml(item.disclaimer)}</p>` : ""}

        <div style="margin-top:24px; text-align:right;">
            <button type="button" onclick="closeDiagnosisModal()" style="padding:10px 22px; background:#15803d; color:white; border:none; border-radius:10px; font-weight:600; cursor:pointer;" data-i18n="history_close">
                ${escapeHtml(t("history_close", "Close"))}
            </button>
        </div>
    `;

    modal.style.display = "flex";
}

// Close on backdrop click
const detailModal = document.getElementById("diagnosisDetailModal");
if (detailModal) {
    detailModal.addEventListener("click", function (e) {
        if (e.target === detailModal) {
            closeDiagnosisModal();
        }
    });
}

async function loadDiagnosisHistory() {
    const message = document.getElementById("diagnosisHistoryMessage");
    const list = document.getElementById("diagnosisHistoryList");

    if (!message || !list) return;

    list.replaceChildren();

    const token = localStorage.getItem("agriSmartToken") || localStorage.getItem("token");

    if (!token) {
        message.innerHTML = `
            <div style="padding:16px 20px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; text-align:center;">
                <p style="margin:0 0 10px 0; color:#475569;" data-i18n="history_login_required">
                    ${t("history_login_required", "Please log in to view and save your diagnosis history.")}
                </p>
                <a href="login.html" class="primary-button" style="display:inline-block; padding:8px 18px; font-size:13px; text-decoration:none;">
                    ${t("login_button", "Login")}
                </a>
            </div>
        `;
        return;
    }

    message.textContent = t("history_loading", "Loading your saved diagnoses...");

    try {
        const response = await fetch(HISTORY_API_URL + "?limit=20", {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error("The server returned an invalid response.");
        }

        if (response.status === 401) {
            localStorage.removeItem("agriSmartToken");
            message.innerHTML = `
                <div style="color:#dc2626; padding:12px 16px; background:#fef2f2; border-radius:8px;">
                    Session expired. <a href="login.html" style="color:#b91c1c; font-weight:700;">Please log in again</a>.
                </div>
            `;
            return;
        }

        if (!response.ok || data.status !== "success") {
            throw new Error(data.message || "Could not load diagnosis history.");
        }

        if (!Array.isArray(data.history) || data.history.length === 0) {
            message.innerHTML = `
                <div style="text-align:center; padding:30px; background:#f8fafc; border-radius:12px; border:1px dashed #cbd5e1;">
                    <span style="font-size:32px;">🌿</span>
                    <p style="color:#64748b; margin:8px 0 0;" data-i18n="history_empty">
                        ${t("history_empty", "No saved diagnoses yet. Scan a plant leaf image while logged in to begin your history.")}
                    </p>
                </div>
            `;
            return;
        }

        message.textContent = `Showing ${data.history.length} saved diagnosis record(s).`;

        for (const item of data.history) {
            const card = document.createElement("article");
            card.style.cssText = [
                "display: flex",
                "align-items: center",
                "justify-content: space-between",
                "flex-wrap: wrap",
                "gap: 16px",
                "padding: 18px 22px",
                "background: #ffffff",
                "border: 1px solid #e2e8f0",
                "border-radius: 14px",
                "box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03)",
                "transition: transform 0.2s, box-shadow 0.2s"
            ].join(";");

            const parsedDate = item.diagnosis_date
                ? new Date(item.diagnosis_date).toLocaleDateString(undefined, {
                      year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                  })
                : "Date unavailable";

            const tokenParam = token ? `?token=${encodeURIComponent(token)}` : '';
            const thumbnailHtml = item.image_url
                ? `<img src="${escapeHtml(item.image_url)}${tokenParam}" alt="Leaf" style="width:64px; height:64px; border-radius:10px; object-fit:cover; border:1px solid #cbd5e1;">`
                : `<div style="width:64px; height:64px; border-radius:10px; background:#f0fdf4; border:1px solid #bbf7d0; display:flex; align-items:center; justify-content:center; font-size:28px;">🌱</div>`;

            const leftBlock = document.createElement("div");
            leftBlock.style.cssText = "display:flex; align-items:center; gap:16px; flex:1; min-width:260px;";
            leftBlock.innerHTML = `
                ${thumbnailHtml}
                <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <span style="background:#e0f2fe; color:#0369a1; font-weight:700; font-size:11px; padding:2px 8px; border-radius:10px;">
                            ${escapeHtml(item.crop_name || "Crop")}
                        </span>
                        <small style="color:#94a3b8; font-size:12px;">📅 ${escapeHtml(parsedDate)}</small>
                    </div>
                    <h3 style="color:#1e293b; margin:0 0 4px 0; font-size:17px; font-weight:700;">
                        ${escapeHtml(item.display_name || item.predicted_class || "Plant Disease")}
                    </h3>
                    <p style="margin:0; font-size:13px; color:#64748b;">
                        ${item.safe_treatment && item.safe_treatment.length > 0 ? `💊 ${escapeHtml(item.safe_treatment[0])}` : (item.notes || "Image-based prediction")}
                    </p>
                </div>
            `;

            const rightBlock = document.createElement("div");
            rightBlock.style.cssText = "display:flex; flex-direction:column; align-items:flex-end; gap:8px;";

            const confBadge = document.createElement("span");
            confBadge.style.cssText = "background:#dcfce7; color:#15803d; font-weight:800; font-size:13px; padding:5px 12px; border-radius:14px; border:1px solid #86efac;";
            confBadge.textContent = item.confidence != null ? `${Number(item.confidence).toFixed(1)}%` : "N/A";

            const viewBtn = document.createElement("button");
            viewBtn.type = "button";
            viewBtn.style.cssText = "padding:6px 14px; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; font-size:12px; font-weight:700; color:#334155; cursor:pointer;";
            viewBtn.textContent = t("history_view_details", "View Details");
            viewBtn.addEventListener("click", () => openDiagnosisDetailModal(item));

            rightBlock.append(confBadge, viewBtn);

            card.append(leftBlock, rightBlock);
            list.appendChild(card);
        }

        // Apply translations
        if (window.i18n && typeof window.i18n.applyTranslations === "function") {
            window.i18n.applyTranslations();
        }

    } catch (error) {
        console.error("Diagnosis history error:", error);
        message.textContent =
            error.message || "Unable to load diagnosis history. Check your backend connection.";
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

const refreshHistoryButton = document.getElementById("refreshDiagnosisHistory");
if (refreshHistoryButton) {
    refreshHistoryButton.addEventListener("click", loadDiagnosisHistory);
}

// Auto-load diagnosis history on page ready
loadDiagnosisHistory();

// Re-render when language selector changes
window.addEventListener("languageChanged", function () {
    loadDiagnosisHistory();
});

// =====================================================
// CLEANUP
// =====================================================

window.addEventListener("beforeunload", function () {
    stopCamera();
    clearPreviewUrl();
});
