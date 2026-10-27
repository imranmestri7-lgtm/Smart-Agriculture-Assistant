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

const languageSelector = document.getElementById("language");

function getChatLanguage() {
    if (!languageSelector) {
        return "en";
    }
    return ["en", "mr", "hi"].includes(languageSelector.value)
        ? languageSelector.value
        : "en";
}

if (languageSelector) {
    const savedLanguage = localStorage.getItem("agriSmartLanguage");
    const preferredLanguage = currentUser &&
        currentUser.preferred_language;

    const initialLanguage = savedLanguage ||
        ({"English": "en", "Marathi": "mr", "Hindi": "hi"}[
            preferredLanguage
        ]) ||
        (["en", "mr", "hi"].includes(preferredLanguage)
            ? preferredLanguage : "en");

    languageSelector.value = initialLanguage;

    languageSelector.addEventListener("change", function () {
        localStorage.setItem(
            "agriSmartLanguage",
            getChatLanguage()
        );
    });
}



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


    // Send the question to the authenticated Flask chatbot.
    const token = localStorage.getItem("agriSmartToken");

    if (!token) {
        removeThinking();
        addAssistantMessage("Your login session is missing. Please log in again to use the farming assistant.");
        return;
    }

    // Disable send button to prevent duplicate submissions
   fetch("http://127.0.0.1:5000/api/chat/message", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ message: message, language: getChatLanguage() })
    })
        .then(async function (response) {
            const data = await response.json().catch(function () {
                return {};
            });

            if (!response.ok) {
                throw new Error(
                    data.message || "The farming assistant could not answer right now."
                );
            }

            if (!data.reply) {
                throw new Error("The server returned an empty reply.");
            }

            return data;
        })
        .then(function (data) {
            removeThinking();
            sendButton.disabled = false;
            addAssistantMessage(data);
        })
        .catch(function (error) {
            removeThinking();
            sendButton.disabled = false;
            addAssistantMessage(
                error.message ||
                "Unable to connect to AgriSmart. Check that the Flask backend is running."
            );
            console.error("AgriSmart chat request failed:", error);
        });

}


// =====================================================
// =====================================================
// ADD ASSISTANT MESSAGE AND FARMING KNOWLEDGE
// =====================================================

function addAssistantMessage(response) {
    if (!chatArea) {
        return;
    }

    // Support both old string replies and structured API responses.
    const data = typeof response === "string"
        ? { reply: response }
        : (response || {});

    const assistantMessage = document.createElement("div");
    assistantMessage.className = "message assistant-message";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "🌱";

    const content = document.createElement("div");
    content.className = "message-content";

    const name = document.createElement("div");
    name.className = "message-name";
    name.textContent = "AgriSmart Assistant";

    const reply = document.createElement("p");
    reply.textContent = data.reply || "I couldn't prepare a response.";

    content.appendChild(name);
    content.appendChild(reply);

    function addDetail(title, value) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return;
        }

        const section = document.createElement("div");
        section.className = "chat-knowledge-section";

        const heading = document.createElement("strong");
        heading.textContent = title;
        section.appendChild(heading);

        const detail = document.createElement("p");

        if (Array.isArray(value)) {
            detail.textContent = value
                .filter(item => typeof item === "string" ||
                                typeof item === "number")
                .join("\n• ");
            if (detail.textContent) {
                detail.textContent = "• " + detail.textContent;
            }
        } else if (
            typeof value === "string" ||
            typeof value === "number"
        ) {
            detail.textContent = String(value);
        } else {
            return;
        }

        if (detail.textContent.trim()) {
            section.appendChild(detail);
            content.appendChild(section);
        }
    }

    const knowledge = data.knowledge;

    if (
        data.category === "disease" &&
        knowledge &&
        typeof knowledge === "object"
    ) {
        const diseaseName =
            knowledge.display_name || knowledge.class_name;

        if (diseaseName) {
            addDetail("Plant condition", diseaseName);
        }

        addDetail("About", knowledge.description);
        addDetail("Symptoms", knowledge.symptoms);
        addDetail("Possible causes", knowledge.possible_causes);
        addDetail("Prevention", knowledge.prevention);
        addDetail(
            "Care recommendations",
            knowledge.care_recommendations
        );
        addDetail("Safe treatment guidance", knowledge.safe_treatment);
        addDetail("Important note", knowledge.disclaimer);
        addDetail(
            "Crop compatibility",
            knowledge.crop_compatibility_message
        );
    }

    if (data.follow_up) {
        const followUp = document.createElement("div");
        followUp.className = "chat-follow-up";

        const prompt = document.createElement("p");
        prompt.textContent = data.follow_up;
        followUp.appendChild(prompt);

        const usePrompt = document.createElement("button");
        usePrompt.type = "button";
        usePrompt.className = "chat-follow-up-button";
        usePrompt.textContent = "Answer follow-up";

        usePrompt.addEventListener("click", function () {
            if (messageInput) {
                messageInput.value = data.follow_up;
                messageInput.focus();
            }
        });

        followUp.appendChild(usePrompt);
        content.appendChild(followUp);
    }

    assistantMessage.appendChild(avatar);
    assistantMessage.appendChild(content);
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


            recognition.lang = ({ en: "en-IN", mr: "mr-IN", hi: "hi-IN" })[getChatLanguage()];

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