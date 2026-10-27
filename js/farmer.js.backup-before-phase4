// =====================================================
// AGRISMART FARMER DASHBOARD
// =====================================================


// =====================================================
// AUTHENTICATION CHECK
// =====================================================

const storedUser = localStorage.getItem("agriSmartUser");

if (!storedUser) {

    window.location.href = "login.html";

}


// =====================================================
// GET USER DATA
// =====================================================

let currentUser = null;

try {

    currentUser = JSON.parse(storedUser);

} catch (error) {

    console.error("Invalid user data:", error);

    localStorage.removeItem("agriSmartUser");

    window.location.href = "login.html";

}


// =====================================================
// USER NAME
// =====================================================

function getUserName() {

    if (!currentUser) {
        return "Farmer";
    }

    return (
        currentUser.full_name ||
        currentUser.fullName ||
        currentUser.name ||
        "Farmer"
    );

}


const farmerName = getUserName();


// =====================================================
// DISPLAY USER NAME
// =====================================================

const farmerNameElement =
    document.getElementById("farmerName");

const profileNameElement =
    document.getElementById("profileName");

const chatFarmerNameElement =
    document.getElementById("chatFarmerName");

const welcomeTextElement =
    document.getElementById("welcomeText");


if (farmerNameElement) {

    farmerNameElement.textContent = farmerName;

}


if (profileNameElement) {

    profileNameElement.textContent = farmerName;

}


if (chatFarmerNameElement) {

    chatFarmerNameElement.textContent = farmerName;

}


if (welcomeTextElement) {

    welcomeTextElement.textContent =
        `Welcome, ${farmerName}`;

}


// =====================================================
// LOGOUT
// =====================================================

const logoutButton =
    document.getElementById("logoutButton");


if (logoutButton) {

    logoutButton.addEventListener("click", function () {

        const confirmLogout =
            confirm("Are you sure you want to logout?");

        if (!confirmLogout) {
            return;
        }

        localStorage.removeItem("agriSmartUser");

        window.location.href = "login.html";

    });

}


// =====================================================
// CHAT ELEMENTS
// =====================================================

const messageInput =
    document.getElementById("messageInput");

const sendButton =
    document.getElementById("sendButton");

const chatArea =
    document.getElementById("chatArea");


// =====================================================
// SEND MESSAGE
// =====================================================

function sendMessage() {

    if (!messageInput || !chatArea) {
        return;
    }


    const message =
        messageInput.value.trim();


    // Empty message

    if (message === "") {
        return;
    }


    // -------------------------------------------------
    // CREATE FARMER MESSAGE
    // -------------------------------------------------

    const userMessage =
        document.createElement("div");

    userMessage.className =
        "message user-message";


    userMessage.innerHTML = `

        <div class="message-content">

            <p></p>

        </div>

        <div class="message-avatar">
            👨‍🌾
        </div>

    `;


    // Safely insert user text

    userMessage
        .querySelector("p")
        .textContent = message;


    chatArea.appendChild(userMessage);


    // Clear input

    messageInput.value = "";


    // Scroll

    scrollToBottom();


    // Show thinking

    showThinking();


    // -------------------------------------------------
    // TEMPORARY ASSISTANT RESPONSE
    // -------------------------------------------------

    setTimeout(function () {

        removeThinking();

        addAssistantMessage(
            getAssistantResponse(message)
        );

    }, 1000);

}


// =====================================================
// TEMPORARY ASSISTANT RESPONSE
// =====================================================

function getAssistantResponse(message) {

    const text =
        message.toLowerCase();


    if (
        text.includes("crop") ||
        text.includes("पीक") ||
        text.includes("फसल")
    ) {

        return "I can help you with crop selection, crop management and farming conditions. The crop recommendation feature will be connected to the backend next.";

    }


    if (
        text.includes("water") ||
        text.includes("irrigation") ||
        text.includes("पाणी") ||
        text.includes("सिंचाई")
    ) {

        return "Irrigation guidance will use your crop information and environmental conditions. The irrigation module will be connected next.";

    }


    if (
        text.includes("disease") ||
        text.includes("disease") ||
        text.includes("रोग")
    ) {

        return "You can use Disease Detection to upload a plant image. The plant-disease model will be connected in the next development stage.";

    }


    if (
        text.includes("weather") ||
        text.includes("हवामान") ||
        text.includes("मौसम")
    ) {

        return "The Weather module will provide farming-related weather information. We will connect the weather API after the core modules are ready.";

    }


    return "Thanks for your question! The AgriSmart Assistant is ready for the next backend integration. More farming features will be connected step by step.";

}


// =====================================================
// ADD ASSISTANT MESSAGE
// =====================================================

function addAssistantMessage(message) {

    if (!chatArea) {
        return;
    }


    const assistantMessage =
        document.createElement("div");


    assistantMessage.className =
        "message assistant-message";


    assistantMessage.innerHTML = `

        <div class="message-avatar">
            🌱
        </div>

        <div class="message-content">

            <div class="message-name">
                AgriSmart Assistant
            </div>

            <p></p>

        </div>

    `;


    assistantMessage
        .querySelector("p")
        .textContent = message;


    chatArea.appendChild(assistantMessage);


    scrollToBottom();

}


// =====================================================
// THINKING ANIMATION
// =====================================================

function showThinking() {

    if (!chatArea) {
        return;
    }


    if (
        document.getElementById("thinkingMessage")
    ) {

        return;

    }


    const thinkingMessage =
        document.createElement("div");


    thinkingMessage.className =
        "message assistant-message";


    thinkingMessage.id =
        "thinkingMessage";


    thinkingMessage.innerHTML = `

        <div class="message-avatar">
            🌱
        </div>

        <div class="thinking-bubble">

            <span class="thinking-text">
                Thinking
            </span>

            <span class="dot"></span>

            <span class="dot"></span>

            <span class="dot"></span>

        </div>

    `;


    chatArea.appendChild(thinkingMessage);


    scrollToBottom();

}


// =====================================================
// REMOVE THINKING
// =====================================================

function removeThinking() {

    const thinkingMessage =
        document.getElementById(
            "thinkingMessage"
        );


    if (thinkingMessage) {

        thinkingMessage.remove();

    }

}


// =====================================================
// SCROLL TO BOTTOM
// =====================================================

function scrollToBottom() {

    if (!chatArea) {
        return;
    }


    chatArea.scrollTo({

        top: chatArea.scrollHeight,

        behavior: "smooth"

    });

}


// =====================================================
// SEND BUTTON
// =====================================================

if (sendButton) {

    sendButton.addEventListener(
        "click",
        sendMessage
    );

}


// =====================================================
// ENTER KEY
// =====================================================

if (messageInput) {

    messageInput.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendMessage();

            }

        }
    );

}


// =====================================================
// QUICK ACTIONS
// =====================================================

const quickActions =
    document.querySelectorAll(
        ".quick-actions button"
    );


quickActions.forEach(function (button) {

    button.addEventListener(
        "click",
        function () {

            const action =
                button.textContent.trim();


            const questions = {

                "🌾 Crop Recommendation":
                    "Which crop is suitable for my soil?",

                "💧 Irrigation Advice":
                    "How much water does my crop need?",

                "🍃 Disease Detection":
                    "How can I identify a disease in my crop?",

                "🌦️ Weather Information":
                    "What weather conditions are suitable for farming?",

                "🌱 Fertilizer Recommendation":
                    "Which fertilizer is suitable for my crop?",

                "🐛 Pest Management":
                    "How can I manage pests in my crop?",

                "📊 Market Prices":
                    "What is the current market price of my crop?",

                "🌍 Soil Health":
                    "How can I improve my soil health?"

            };


            const question =
                questions[action];


            if (question && messageInput) {

                messageInput.value =
                    question;

                sendMessage();

            }

        }
    );

});


// =====================================================
// ADD BUTTON MENU
// =====================================================

const addButton =
    document.getElementById("addButton");

const addMenu =
    document.getElementById("addMenu");


if (addButton && addMenu) {


    // OPEN / CLOSE

    addButton.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

            addMenu.classList.toggle("show");

        }
    );


    // CLICK OUTSIDE

    document.addEventListener(
        "click",
        function () {

            addMenu.classList.remove("show");

        }
    );


    // DON'T CLOSE WHEN MENU IS CLICKED

    addMenu.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

        }
    );

}


// =====================================================
// ADD MENU OPTIONS
// =====================================================

const uploadLeaf =
    document.getElementById("uploadLeaf");

const uploadFile =
    document.getElementById("uploadFile");

const openCamera =
    document.getElementById("openCamera");


if (uploadLeaf) {

    uploadLeaf.addEventListener(
        "click",
        function () {

            window.location.href =
                "disease.html";

        }
    );

}


if (uploadFile) {

    uploadFile.addEventListener(
        "click",
        function () {

            alert(
                "File upload will be connected with the assistant later."
            );

        }
    );

}


if (openCamera) {

    openCamera.addEventListener(
        "click",
        function () {

            alert(
                "Camera-based plant detection will be connected in the disease detection module."
            );

        }
    );

}


// =====================================================
// PROFILE BUTTON
// =====================================================

const profileButton =
    document.getElementById("profileButton");


if (profileButton) {

    profileButton.addEventListener(
        "click",
        function () {

            alert(
                `Logged in as ${farmerName}`
            );

        }
    );

}


// =====================================================
// THINK BUTTON
// =====================================================

const thinkButton =
    document.getElementById("thinkButton");


if (thinkButton) {

    thinkButton.addEventListener(
        "click",
        function () {

            alert(
                "Enhanced assistant reasoning will be connected when the assistant backend is implemented."
            );

        }
    );

}


// =====================================================
// VOICE BUTTON
// =====================================================

const voiceButton =
    document.getElementById("voiceButton");


if (voiceButton) {

    voiceButton.addEventListener(
        "click",
        function () {

            if (
                !(
                    "webkitSpeechRecognition" in window ||
                    "SpeechRecognition" in window
                )
            ) {

                alert(
                    "Voice input is not supported by this browser."
                );

                return;

            }


            const SpeechRecognition =
                window.SpeechRecognition ||
                window.webkitSpeechRecognition;


            const recognition =
                new SpeechRecognition();


            recognition.lang = "en-IN";

            recognition.interimResults = false;

            recognition.maxAlternatives = 1;


            recognition.start();


            recognition.onresult =
                function (event) {

                    const transcript =
                        event.results[0][0].transcript;


                    if (messageInput) {

                        messageInput.value =
                            transcript;

                    }

                };


            recognition.onerror =
                function () {

                    alert(
                        "Unable to capture voice input. Please try again."
                    );

                };

        }
    );

}