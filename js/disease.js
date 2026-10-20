
 // =====================================================
 // AGRISMART - PLANT DISEASE DETECTION
 // Flask API + TensorFlow model + farmer follow-up
 // =====================================================

const API_URL = "http://127.0.0.1:5000/api/disease/predict";
const RECOMMEND_API_URL = "http://127.0.0.1:5000/api/disease/recommend";
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
    followUp.style.display = isLowConfidence ? "block" : "none";
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
    farmerQuestionsForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const answers = [
            ["Plant or fruit", document.getElementById("farmerPlant").value],
            ["Symptoms", document.getElementById("farmerSymptoms").value],
            ["Problem duration", document.getElementById("farmerDuration").value],
            ["Spread", document.getElementById("farmerSpread").value]
        ];

        const answersResult = document.getElementById("farmerAnswersResult");
        answersResult.replaceChildren();

        const heading = document.createElement("h4");
        heading.textContent = "Your answers";
        heading.style.marginBottom = "8px";
        answersResult.appendChild(heading);

        answers.forEach(function (answer) {
            const line = document.createElement("p");
            const label = document.createElement("strong");

            label.textContent = `${answer[0]}: `;
            line.appendChild(label);
            line.appendChild(document.createTextNode(answer[1] || "Not provided"));

            answersResult.appendChild(line);
        });

        const note = document.createElement("p");
        note.style.marginTop = "10px";
        note.textContent =
            "Thank you. These details can help guide a future assessment, but they have not confirmed the disease or generated a treatment recommendation.";

        answersResult.appendChild(note);
        answersResult.style.display = "block";
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

        analyzeButton.disabled = true;
        analyzeButton.textContent = "⏳ Analyzing image...";

        try {
            const formData = new FormData();
            formData.append("image", selectedFile);

            const response = await fetch(API_URL, {
                method: "POST",
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
        } catch (error) {
            console.error("Disease prediction error:", error);

            const errorMessage = error.message || "An unexpected error occurred.";

            showMessage(
                errorMessage.includes("Failed to fetch")
                    ? "Cannot connect to the Flask backend. Check that http://127.0.0.1:5000 is running."
                    : errorMessage
            );
        } finally {
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
// CLEANUP
// =====================================================

window.addEventListener("beforeunload", function () {
    stopCamera();
    clearPreviewUrl();
});
