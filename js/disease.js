// =====================================================
// AGRISMART - PLANT DISEASE DETECTION
// Connects frontend to Flask + TensorFlow model
// =====================================================


// =====================================================
// CONFIGURATION
// =====================================================

const API_URL = "http://127.0.0.1:5000/api/disease/predict";

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;


// =====================================================
// HTML ELEMENTS
// =====================================================

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


// =====================================================
// APPLICATION STATE
// =====================================================

let selectedFile = null;

let cameraStream = null;

let previewObjectUrl = null;


// =====================================================
// CREATE RESULT SECTION
// Your current disease.html does not contain a result
// section, so JavaScript creates it automatically.
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
                alt="Analyzed leaf"
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
            >
                --
            </h3>

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


// Insert results after the scanner section
const scannerSection = document.getElementById("scanner");

if (scannerSection) {
    scannerSection.insertAdjacentElement(
        "afterend",
        resultSection
    );
}


// =====================================================
// HELPER: DISPLAY MESSAGES
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
            analyzeButton.insertAdjacentElement(
                "afterend",
                messageBox
            );
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
// HELPER: CLEAN UP PREVIOUS PREVIEW URL
// =====================================================

function clearPreviewUrl() {

    if (previewObjectUrl) {

        URL.revokeObjectURL(previewObjectUrl);

        previewObjectUrl = null;
    }
}


// =====================================================
// HELPER: DISPLAY SELECTED IMAGE
// =====================================================

function displaySelectedImage(file) {

    clearPreviewUrl();

    previewObjectUrl = URL.createObjectURL(file);

    previewImage.src = previewObjectUrl;

    imagePreview.style.display = "flex";

    if (uploadArea) {
        uploadArea.style.display = "none";
    }

    resultSection.style.display = "none";

    clearMessage();
}


// =====================================================
// IMAGE SELECTION
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
// HANDLE IMAGE
// =====================================================

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
// CAMERA: START
// =====================================================

if (cameraButton) {

    cameraButton.addEventListener("click", async function () {

        clearMessage();

        if (!navigator.mediaDevices ||
            !navigator.mediaDevices.getUserMedia) {

            showMessage(
                "Camera access is unavailable. Open the website using localhost or HTTPS."
            );

            return;
        }

        try {

            stopCamera();

            cameraStream = await navigator.mediaDevices.getUserMedia({

                video: {
                    facingMode: "environment"
                },

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


// =====================================================
// CAMERA: STOP
// =====================================================

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


// =====================================================
// CAMERA: CLOSE BUTTON
// =====================================================

if (closeCameraButton) {

    closeCameraButton.addEventListener("click", function () {

        stopCamera();

    });

}


// =====================================================
// CAMERA: CAPTURE IMAGE
// =====================================================

if (captureButton) {

    captureButton.addEventListener("click", function () {

        if (!cameraStream || !camera.videoWidth) {

            showMessage(
                "Please wait for the camera to start."
            );

            return;
        }

        const canvas = document.createElement("canvas");

        canvas.width = camera.videoWidth;

        canvas.height = camera.videoHeight;

        const context = canvas.getContext("2d");

        context.drawImage(
            camera,
            0,
            0,
            canvas.width,
            canvas.height
        );

        canvas.toBlob(function (blob) {

            if (!blob) {

                showMessage(
                    "Could not capture the image. Please try again."
                );

                return;
            }

            const file = new File(
                [blob],
                "captured_leaf.jpg",
                {
                    type: "image/jpeg"
                }
            );

            handleImage(file);

            stopCamera();

        }, "image/jpeg", 0.92);

    });

}


// =====================================================
// FORMAT MODEL CLASS NAME
// Example:
// Apple___Apple_scab -> Apple — Apple scab
// =====================================================

function formatClassName(className) {

    return className
        .replace(/___/g, " — ")
        .replace(/_/g, " ");
}


// =====================================================
// DISPLAY TOP PREDICTIONS
// =====================================================

function displayTopPredictions(predictions) {

    const container = document.getElementById("topPredictions");

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

        score.textContent = `${Number(item.confidence).toFixed(2)}%`;

        row.appendChild(name);

        row.appendChild(score);

        container.appendChild(row);

    });

}


// =====================================================
// DISPLAY REAL MODEL RESULT
// =====================================================

function showResult(data) {

    const prediction = data.prediction;

    document.getElementById("resultImage").src =
        previewImage.src;

    document.getElementById("diseaseName").textContent =
        formatClassName(prediction.class_name);

    const confidence = Number(prediction.confidence);

    document.getElementById("confidence").textContent =
        `${confidence.toFixed(2)}%`;

    document.getElementById("confidenceBar").style.width =
        `${Math.min(100, Math.max(0, confidence))}%`;

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
// ANALYZE DISEASE USING THE REAL FLASK API
// =====================================================

if (analyzeButton) {

    analyzeButton.addEventListener("click", async function () {

        clearMessage();

        // Image is required
        if (!selectedFile) {

            showMessage(
                "Please upload a leaf image or capture one using the camera."
            );

            return;
        }

        const originalButtonText = analyzeButton.textContent;

        analyzeButton.disabled = true;

        analyzeButton.textContent = "⏳ Analyzing image...";

        try {

            // Prepare multipart form data
            const formData = new FormData();

            formData.append("image", selectedFile);

            // Send image to the trained model
            const response = await fetch(API_URL, {

                method: "POST",

                body: formData

            });

            let data;

            try {

                data = await response.json();

            } catch {

                throw new Error(
                    "The backend returned an invalid response."
                );

            }

            if (!response.ok) {

                throw new Error(
                    data.message ||
                    "Disease prediction failed."
                );

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

            // Display the actual prediction from TensorFlow
            showResult(data);

        } catch (error) {

            console.error("Disease prediction error:", error);

            showMessage(
                error.message.includes("Failed to fetch")
                    ? "Cannot connect to the Flask backend. Check that http://127.0.0.1:5000 is running."
                    : error.message
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
// CLEAN UP CAMERA WHEN LEAVING THE PAGE
// =====================================================

window.addEventListener("beforeunload", function () {

    stopCamera();

    clearPreviewUrl();

});