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
        localStorage.removeItem("agriSmartToken");
        localStorage.removeItem("token");

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
    if (window.i18n && typeof window.i18n.getLang === "function") {
        return window.i18n.getLang();
    }
    const current = localStorage.getItem("lang") || localStorage.getItem("agriSmartLanguage");
    if (["en", "mr", "hi"].includes(current)) {
        return current;
    }
    if (languageSelector && ["en", "mr", "hi"].includes(languageSelector.value)) {
        return languageSelector.value;
    }
    return "en";
}

if (languageSelector) {
    const savedLanguage = localStorage.getItem("lang") ||
        localStorage.getItem("agriSmartLanguage") ||
        (currentUser && currentUser.preferred_language) ||
        "en";

    const initialLanguage =
        ({"English": "en", "Marathi": "mr", "Hindi": "hi"}[savedLanguage]) ||
        (["en", "mr", "hi"].includes(savedLanguage) ? savedLanguage : "en");

    languageSelector.value = initialLanguage;

    languageSelector.addEventListener("change", function () {
        const chosen = languageSelector.value;
        localStorage.setItem("lang", chosen);
        localStorage.setItem("agriSmartLanguage", chosen);
        if (window.i18n && typeof window.i18n.setLang === "function") {
            window.i18n.setLang(chosen);
            window.i18n.applyTranslations();
        }
        const globalSelect = document.getElementById("lang-select");
        if (globalSelect && globalSelect.value !== chosen) {
            globalSelect.value = chosen;
        }
        window.dispatchEvent(new CustomEvent("languageChanged", { detail: { lang: chosen } }));
    });

    window.addEventListener("languageChanged", function (e) {
        if (languageSelector && e.detail && e.detail.lang) {
            languageSelector.value = e.detail.lang;
        }
    });
}


// =====================================================
// TIME FORMATTER
// =====================================================

function formatChatTime(dateInput) {
    try {
        const date = dateInput ? new Date(dateInput) : new Date();
        if (isNaN(date.getTime())) {
            return "Just now";
        }
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
        return "Just now";
    }
}


// =====================================================
// LOAD CHAT HISTORY
// =====================================================

function loadChatHistory() {
    if (!chatArea) {
        return;
    }

    const token = localStorage.getItem("agriSmartToken") || localStorage.getItem("token");
    if (!token) {
        return;
    }

    fetch("/api/chat/history?limit=50", {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    })
    .then(function (res) {
        if (!res.ok) {
            throw new Error(`HTTP error ${res.status}`);
        }
        return res.json();
    })
    .then(function (data) {
        if (data.status === "success" && Array.isArray(data.history) && data.history.length > 0) {
            const divider = document.createElement("div");
            divider.className = "chat-history-divider";
            divider.innerHTML = `<span data-i18n="previous_conversations">${window.i18n ? window.i18n.t("previous_conversations") : "Previous Conversations"}</span>`;
            chatArea.appendChild(divider);

            data.history.forEach(function (item) {
                // Historical user message
                const userMsg = document.createElement("div");
                userMsg.className = "message user-message";
                userMsg.innerHTML = `
                    <div class="message-content">
                        <p></p>
                        <span class="message-time">${formatChatTime(item.created_at)}</span>
                    </div>
                    <div class="message-avatar">👨‍🌾</div>
                `;
                userMsg.querySelector("p").textContent = item.message;
                chatArea.appendChild(userMsg);

                // Historical assistant message
                const botMsg = document.createElement("div");
                botMsg.className = "message assistant-message";
                botMsg.innerHTML = `
                    <div class="message-avatar">🌱</div>
                    <div class="message-content">
                        <div class="message-name">AgriSmart Assistant</div>
                        <p></p>
                        <span class="message-time">${formatChatTime(item.created_at)}</span>
                    </div>
                `;
                botMsg.querySelector("p").textContent = item.response;
                chatArea.appendChild(botMsg);
            });

            scrollToBottom();
        }
    })
    .catch(function (err) {
        console.warn("Could not load previous chat history:", err);
    });
}


// =====================================================
// CLEAR CHAT HISTORY
// =====================================================

const clearChatBtn = document.getElementById("clearChatBtn");

if (clearChatBtn) {
    clearChatBtn.addEventListener("click", function () {
        const confirmMsg = window.i18n
            ? window.i18n.t("clear_chat_confirm")
            : "Are you sure you want to clear your conversation history?";

        if (!confirm(confirmMsg)) {
            return;
        }

        const token = localStorage.getItem("agriSmartToken") || localStorage.getItem("token");
        if (!token) {
            alert("Please log in to clear your chat history.");
            return;
        }

        clearChatBtn.disabled = true;

        fetch("/api/chat/history", {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        })
        .then(function (res) {
            return res.json().catch(function () { return {}; });
        })
        .then(function (data) {
            clearChatBtn.disabled = false;
            if (data.status === "success") {
                chatArea.innerHTML = `
                    <div class="message assistant-message">
                        <div class="message-avatar">
                            🌱
                        </div>
                        <div class="message-content">
                            <div class="message-name">
                                AgriSmart Assistant
                            </div>
                            <p>
                                Hello <span id="chatFarmerName">${getUserName()}</span>! 👋
                            </p>
                            <p>
                                I can help you with crops, irrigation,
                                weather, plant diseases, pests and
                                general farming guidance.
                            </p>
                            <span class="message-time">
                                Just now
                            </span>
                        </div>
                    </div>
                `;
                const successMsg = window.i18n
                    ? window.i18n.t("clear_chat_success")
                    : "Conversation history cleared.";
                alert(successMsg);
            } else {
                alert(data.message || "Could not clear chat history.");
            }
        })
        .catch(function (err) {
            clearChatBtn.disabled = false;
            console.error("Error clearing chat history:", err);
            alert("Could not connect to server to clear chat history.");
        });
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
            <span class="message-time">${formatChatTime(new Date())}</span>

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
    const token = localStorage.getItem("agriSmartToken") || localStorage.getItem("token");

    if (!token) {
        removeThinking();
        addAssistantMessage("Your login session is missing. Please log in again to use the farming assistant.");
        return;
    }

    if (sendButton) {
        sendButton.disabled = true;
    }

    fetch("/api/chat/message", {
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
            if (sendButton) {
                sendButton.disabled = false;
            }
            addAssistantMessage(data);
        })
        .catch(function (error) {
            removeThinking();
            if (sendButton) {
                sendButton.disabled = false;
            }
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

    const timeSpan = document.createElement("span");
    timeSpan.className = "message-time";
    timeSpan.textContent = formatChatTime(new Date());
    content.appendChild(timeSpan);

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
            const actionKey = button.getAttribute("data-quick-action");
            const lang = (typeof getChatLanguage === "function" ? getChatLanguage() : "en") || "en";

            const questionMap = {
                crop_status: {
                    en: "What is my crop status?",
                    mr: "माझ्या पिकांची स्थिती काय आहे?",
                    hi: "मेरी फसलों की स्थिति क्या है?"
                },
                irrigation_guidance: {
                    en: "What irrigation recommendation did I receive?",
                    mr: "सिंचन मार्गदर्शन",
                    hi: "सिंचाई मार्गदर्शन"
                },
                disease_prevention: {
                    en: "Show my recent disease diagnosis",
                    mr: "रोग प्रतिबंध",
                    hi: "रोग रोकथाम"
                },
                weather_info: {
                    en: "Weather information",
                    mr: "हवामान माहिती",
                    hi: "मौसम जानकारी"
                },
                harvest_reminders: {
                    en: "Which crops are ready for harvest?",
                    mr: "काढणी स्मरणपत्रे",
                    hi: "कटाई रिमाइंडर"
                },
                farm_summary: {
                    en: "Give me my farm summary",
                    mr: "माझ्या शेताचा सारांश द्या",
                    hi: "मेरे खेत का सारांश दें"
                }
            };

            const legacyQuestions = {
                "🌾 Crop Recommendation": "Which crop is suitable for my soil?",
                "💧 Irrigation Advice": "How much water does my crop need?",
                "🍃 Disease Detection": "How can I identify a disease in my crop?",
                "🌦️ Weather Information": "What weather conditions are suitable for farming?",
                "🌱 Fertilizer Recommendation": "Which fertilizer is suitable for my crop?",
                "🐛 Pest Management": "How can I manage pests in my crop?",
                "📊 Market Prices": "What is the current market price of my crop?",
                "🌍 Soil Health": "How can I improve my soil health?"
            };

            let question = "";
            if (actionKey && questionMap[actionKey]) {
                question = questionMap[actionKey][lang] || questionMap[actionKey]["en"];
            } else {
                const actionText = button.textContent.trim();
                question = legacyQuestions[actionText] || actionText;
            }

            if (question && messageInput) {
                messageInput.value = question;
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

                const notSupportedMsg = window.i18n
                    ? window.i18n.t("voice_not_supported")
                    : "Voice input is not supported by this browser.";

                alert(notSupportedMsg);

                return;

            }


            const SpeechRecognition =
                window.SpeechRecognition ||
                window.webkitSpeechRecognition;


            const recognition =
                new SpeechRecognition();


            recognition.lang = ({ en: "en-IN", mr: "mr-IN", hi: "hi-IN" })[getChatLanguage()] || "en-IN";

            recognition.interimResults = false;

            recognition.maxAlternatives = 1;


            recognition.onstart = function () {
                voiceButton.classList.add("recording");
                voiceButton.title = window.i18n
                    ? window.i18n.t("listening")
                    : "Listening...";
            };

            recognition.onend = function () {
                voiceButton.classList.remove("recording");
                voiceButton.title = "Voice Input";
            };

            recognition.onresult =
                function (event) {
                    voiceButton.classList.remove("recording");

                    if (event.results && event.results[0] && event.results[0][0]) {
                        const transcript =
                            event.results[0][0].transcript;

                        if (messageInput) {
                            messageInput.value =
                                transcript;
                            messageInput.focus();
                        }
                    }
                };


            recognition.onerror =
                function (event) {
                    voiceButton.classList.remove("recording");

                    if (event.error === "not-allowed" || event.error === "permission-denied") {
                        const deniedMsg = window.i18n
                            ? window.i18n.t("mic_permission_denied")
                            : "Microphone access was denied. Please allow microphone permissions in your browser.";
                        alert(deniedMsg);
                    } else if (event.error === "no-speech") {
                        console.warn("No speech was detected.");
                    } else {
                        console.error("Speech recognition error:", event.error);
                        alert(
                            "Voice recognition error: " +
                            (event.error || "Unable to capture voice.")
                        );
                    }
                };

            try {
                recognition.start();
            } catch (err) {
                console.error("Speech recognition start failed:", err);
                voiceButton.classList.remove("recording");
            }

        }
    );

}


// =====================================================
// INITIALIZE CHAT HISTORY ON LOAD
// =====================================================

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadChatHistory);
} else {
    loadChatHistory();
}
