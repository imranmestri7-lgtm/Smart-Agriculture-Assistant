// =========================================
// DISEASE DETECTION JAVASCRIPT
// =========================================

const leafImage = document.getElementById("leafImage");
const uploadArea = document.getElementById("uploadArea");
const previewContainer = document.getElementById("previewContainer");
const imagePreview = document.getElementById("imagePreview");
const removeImage = document.getElementById("removeImage");
const analyzeBtn = document.getElementById("analyzeBtn");
const cropSelect = document.getElementById("cropSelect");
const resultSection = document.getElementById("resultSection");
const resultImage = document.getElementById("resultImage");
const scanAgain = document.getElementById("scanAgain");

let selectedFile = null;


// =========================================
// IMAGE SELECTION
// =========================================

leafImage.addEventListener("change", function () {

    const file = this.files[0];

    if (file) {
        handleImage(file);
    }

});


// =========================================
// HANDLE IMAGE
// =========================================

function handleImage(file) {

    // Check file type
    if (!file.type.startsWith("image/")) {

        alert("Please select a valid image file.");

        return;
    }


    // Check file size - 5 MB
    if (file.size > 5 * 1024 * 1024) {

        alert("Image size must be less than 5 MB.");

        return;
    }


    selectedFile = file;


    // Create image preview
    const reader = new FileReader();

    reader.onload = function (event) {

        imagePreview.src = event.target.result;

        uploadArea.style.display = "none";

        previewContainer.style.display = "block";

    };

    reader.readAsDataURL(file);
}


// =========================================
// REMOVE IMAGE
// =========================================

removeImage.addEventListener("click", function () {

    selectedFile = null;

    leafImage.value = "";

    imagePreview.src = "";

    previewContainer.style.display = "none";

    uploadArea.style.display = "block";

});


// =========================================
// DRAG & DROP
// =========================================

uploadArea.addEventListener("dragover", function (event) {

    event.preventDefault();

    uploadArea.style.borderColor = "#2e7d32";

});


uploadArea.addEventListener("dragleave", function () {

    uploadArea.style.borderColor = "#a5c9a8";

});


uploadArea.addEventListener("drop", function (event) {

    event.preventDefault();

    uploadArea.style.borderColor = "#a5c9a8";

    const file = event.dataTransfer.files[0];

    if (file) {
        handleImage(file);
    }

});


// =========================================
// ANALYZE DISEASE
// =========================================

analyzeBtn.addEventListener("click", function () {

    // Check crop
    if (cropSelect.value === "") {

        alert("Please select a crop first.");

        return;
    }


    // Check image
    if (!selectedFile) {

        alert("Please upload a leaf image first.");

        return;
    }


    // Button loading state
    analyzeBtn.disabled = true;

    analyzeBtn.innerHTML = "⏳ Analyzing...";


    // Demo AI processing
    setTimeout(function () {

        showResult();

        analyzeBtn.disabled = false;

        analyzeBtn.innerHTML = "🔍 Analyze Disease";

    }, 1500);

});


// =========================================
// SHOW DEMO RESULT
// =========================================

function showResult() {

    // Show uploaded image in result
    resultImage.src = imagePreview.src;


    // Demo result
    document.getElementById("diseaseName").textContent =
        "Leaf Blight";


    document.getElementById("confidence").textContent =
        "94%";


    // Update progress bar
    const progress = document.querySelector(".progress");

    progress.style.width = "94%";


    // Show result section
    resultSection.style.display = "block";


    // Smooth scroll
    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}


// =========================================
// SCAN ANOTHER LEAF
// =========================================

scanAgain.addEventListener("click", function () {

    selectedFile = null;

    leafImage.value = "";

    imagePreview.src = "";

    resultImage.src = "";

    previewContainer.style.display = "none";

    uploadArea.style.display = "block";

    resultSection.style.display = "none";

    cropSelect.value = "";

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

});