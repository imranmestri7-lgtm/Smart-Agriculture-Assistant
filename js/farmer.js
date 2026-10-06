// ==========================================
// AGRISMART FARMER ASSISTANT
// CHAT FUNCTIONALITY
// ==========================================

const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const chatArea = document.getElementById("chatArea");


// ------------------------------------------
// SEND MESSAGE
// ------------------------------------------

function sendMessage() {

    const message = messageInput.value.trim();

    // Empty message
    if (message === "") {
        return;
    }


    // --------------------------------------
    // CREATE FARMER MESSAGE
    // --------------------------------------

    const userMessage = document.createElement("div");

    userMessage.className = "message user-message";

    userMessage.innerHTML = `
        <div class="message-content">
            <p></p>
        </div>

        <div class="message-avatar">
            👨‍🌾
        </div>
    `;

    // Add text safely
    userMessage.querySelector("p").textContent = message;

    chatArea.appendChild(userMessage);


    // Clear input
    messageInput.value = "";


    // Scroll to latest message
    scrollToBottom();


    // --------------------------------------
    // SHOW THINKING
    // --------------------------------------

    showThinking();

}


// ------------------------------------------
// SHOW THINKING ANIMATION
// ------------------------------------------

function showThinking() {

    if (document.getElementById("thinkingMessage")) {
        return;
    }

    const thinkingMessage = document.createElement("div");

    thinkingMessage.className = "message assistant-message";
    thinkingMessage.id = "thinkingMessage";

    thinkingMessage.innerHTML = `
        <div class="message-avatar">
            🤖
        </div>

        <div class="thinking-bubble">
            <span class="thinking-text">Thinking</span>
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
        </div>
    `;

    chatArea.appendChild(thinkingMessage);

    scrollToBottom();
}


// ------------------------------------------
// REMOVE THINKING
// ------------------------------------------

function removeThinking() {

    const thinkingMessage =
        document.getElementById("thinkingMessage");

    if (thinkingMessage) {
        thinkingMessage.remove();
    }

}


// ------------------------------------------
// SCROLL TO BOTTOM
// ------------------------------------------

function scrollToBottom() {

    chatArea.scrollTo({
        top: chatArea.scrollHeight,
        behavior: "smooth"
    });

}


// ------------------------------------------
// SEND BUTTON
// ------------------------------------------

if (sendButton) {

    sendButton.addEventListener("click", function () {

        sendMessage();

    });

}


// ------------------------------------------
// ENTER KEY
// ------------------------------------------

if (messageInput) {

    messageInput.addEventListener("keydown", function (event) {

        if (event.key === "Enter" && !event.shiftKey) {

            event.preventDefault();

            sendMessage();

        }

    });

}


// ==========================================
// QUICK ACTIONS
// ==========================================

const quickActions = document.querySelectorAll(".quick-actions button");

quickActions.forEach(function (button) {

    button.addEventListener("click", function () {

        const action = button.textContent.trim();

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
                "How can I control pests in my crop?",

            "📊 Market Prices":
                "What is the current market price of my crop?",

            "🌍 Soil Health":
                "How can I improve my soil health?"
        };

        const question = questions[action];

        if (question) {

            messageInput.value = question;

            sendMessage();

        }

    });

});


const addButton = document.getElementById("addButton");
const addMenu = document.getElementById("addMenu");

if (addButton && addMenu) {

    addButton.addEventListener("click", function (event) {
        event.stopPropagation();
        addMenu.classList.toggle("show");
    });

    document.addEventListener("click", function () {
        addMenu.classList.remove("show");
    });

    addMenu.addEventListener("click", function (event) {
        event.stopPropagation();
    });
}