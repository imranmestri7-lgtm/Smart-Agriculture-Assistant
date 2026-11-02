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

    logoutButton.addEventListener("click", async function () {

        const confirmLogout =
            confirm(window.i18n ? window.i18n.t("confirm_logout") : "Are you sure you want to logout?");

        if (!confirmLogout) {
            return;
        }

        // Notify backend logout endpoint
        try {
            await fetch("/api/auth/logout", { method: "POST" });
        } catch (e) {
            // Ignore network errors during logout
        }

        // Purge private PWA cached user data
        if (window.AgriSmartPWA && typeof window.AgriSmartPWA.clearPrivateCache === "function") {
            try {
                await window.AgriSmartPWA.clearPrivateCache();
            } catch (e) {}
        }

        localStorage.removeItem("agriSmartUser");
        localStorage.removeItem("agriSmartToken");
        localStorage.removeItem("token");
        localStorage.removeItem("agriSmart_last_user_id");

        // Revert to guest language choice without retaining private user preference
        const guestLang = localStorage.getItem("guest_lang") || "en";
        localStorage.setItem("lang", guestLang);

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

                let imageHtml = "";
                let displayMsg = item.clean_message || item.message || "";
                let itemImgUrl = item.image_url;

                if (!itemImgUrl && typeof item.message === "string") {
                    const match = item.message.match(/\[image:(\/api\/chat\/image\/[^\]]+)\]/);
                    if (match) {
                        itemImgUrl = match[1];
                        displayMsg = item.message.replace(/\[image:\/api\/chat\/image\/[^\]]+\]\s*/, "");
                    }
                }

                if (itemImgUrl) {
                    const authenticatedImgUrl = itemImgUrl + (itemImgUrl.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(token);
                    imageHtml = `
                        <div class="user-chat-image-wrap">
                            <img src="${authenticatedImgUrl}" class="user-chat-image" alt="Historical plant photo" onclick="window.open(this.src, '_blank')">
                        </div>
                    `;
                }

                userMsg.innerHTML = `
                    <div class="message-content">
                        ${imageHtml}
                        <p></p>
                        <span class="message-time">${formatChatTime(item.created_at)}</span>
                    </div>
                    <div class="message-avatar">👨‍🌾</div>
                `;
                userMsg.querySelector("p").textContent = displayMsg;
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
// CHAT IMAGE ATTACHMENT STATE & HELPERS
// =====================================================

let currentChatImageFile = null;

const chatFileInput = document.getElementById("chatFileInput");
const chatImagePreviewBar = document.getElementById("chatImagePreviewBar");
const chatImagePreviewThumb = document.getElementById("chatImagePreviewThumb");
const chatImagePreviewName = document.getElementById("chatImagePreviewName");
const chatImagePreviewSize = document.getElementById("chatImagePreviewSize");
const btnRemoveChatImage = document.getElementById("btnRemoveChatImage");

function formatFileSize(bytes) {
    if (!bytes || bytes <= 0) return "0 B";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function clearChatImage() {
    currentChatImageFile = null;
    if (chatFileInput) {
        chatFileInput.value = "";
    }
    if (chatImagePreviewThumb) {
        chatImagePreviewThumb.src = "";
    }
    if (chatImagePreviewBar) {
        chatImagePreviewBar.style.display = "none";
    }
}

function setChatImage(file) {
    if (!file) return;

    // Format validation
    const validTypes = ["image/jpeg", "image/png", "image/webp", "image/jpg"];
    const ext = file.name ? file.name.substring(file.name.lastIndexOf(".")).toLowerCase() : "";
    const validExts = [".jpg", ".jpeg", ".png", ".webp"];
    if (!validTypes.includes(file.type) && !validExts.includes(ext)) {
        const msg = window.i18n ? window.i18n.t("image_invalid_type") : "Invalid image format. Supported formats: JPG, PNG, WEBP.";
        alert(msg);
        return;
    }

    // Size validation: max 5 MB
    const maxBytes = 5 * 1024 * 1024;
    if (file.size > maxBytes) {
        const msg = window.i18n ? window.i18n.t("image_oversize_error") : "Image size must not exceed 5 MB.";
        alert(msg);
        return;
    }

    currentChatImageFile = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = function (e) {
        if (chatImagePreviewThumb) {
            chatImagePreviewThumb.src = e.target.result;
        }
        if (chatImagePreviewName) {
            chatImagePreviewName.textContent = file.name || "plant_image.jpg";
        }
        if (chatImagePreviewSize) {
            chatImagePreviewSize.textContent = formatFileSize(file.size);
        }
        if (chatImagePreviewBar) {
            chatImagePreviewBar.style.display = "flex";
        }
        if (addMenu) {
            addMenu.classList.remove("show");
        }
        if (messageInput) {
            messageInput.focus();
        }
    };
    reader.readAsDataURL(file);
}

if (btnRemoveChatImage) {
    btnRemoveChatImage.addEventListener("click", function (e) {
        e.stopPropagation();
        clearChatImage();
    });
}

if (chatFileInput) {
    chatFileInput.addEventListener("change", function () {
        if (chatFileInput.files && chatFileInput.files.length > 0) {
            setChatImage(chatFileInput.files[0]);
        }
    });
}


// =====================================================
// SEND MESSAGE (TEXT OR MULTIMODAL IMAGE VISION)
// =====================================================

function sendMessage() {
    if (!messageInput || !chatArea) {
        return;
    }

    let message = messageInput.value.trim();
    const hasImage = Boolean(currentChatImageFile);

    // If both message and image are empty, do nothing
    if (message === "" && !hasImage) {
        return;
    }

    const lang = getChatLanguage();

    // If sending image with empty text, assign a sensible default prompt
    if (hasImage && message === "") {
        if (lang === "mr") {
            message = "कृपया या वनस्पतीचे फोटो तपासा आणि यावर कोणताही रोग आहे का किंवा काय काळजी घ्यावी ते सांगा.";
        } else if (lang === "hi") {
            message = "कृपया इस पौधे की तस्वीर का विश्लेषण करें और बताएं कि क्या इसमें कोई बीमारी है या क्या देखभाल आवश्यक है।";
        } else {
            message = "Please analyze this plant image and tell me if it has any disease or needs care.";
        }
    }

    // -------------------------------------------------
    // CREATE FARMER MESSAGE BUBBLE
    // -------------------------------------------------
    const userMessage = document.createElement("div");
    userMessage.className = "message user-message";

    let imageHtml = "";
    if (hasImage && chatImagePreviewThumb && chatImagePreviewThumb.src) {
        imageHtml = `
            <div class="user-chat-image-wrap">
                <img src="${chatImagePreviewThumb.src}" class="user-chat-image" alt="Uploaded plant image" onclick="window.open(this.src, '_blank')">
            </div>
        `;
    }

    userMessage.innerHTML = `
        <div class="message-content">
            ${imageHtml}
            <p></p>
            <span class="message-time">${formatChatTime(new Date())}</span>
        </div>
        <div class="message-avatar">
            👨‍🌾
        </div>
    `;

    userMessage.querySelector("p").textContent = message;
    chatArea.appendChild(userMessage);

    // Snapshot image to send and clear selection bar
    const imageToSend = currentChatImageFile;
    clearChatImage();

    // Clear input
    messageInput.value = "";

    // Scroll
    scrollToBottom();

    // Show thinking indicator
    showThinking();

    const token = localStorage.getItem("agriSmartToken") || localStorage.getItem("token");
    if (!token) {
        removeThinking();
        addAssistantMessage("Your login session is missing. Please log in again to use the farming assistant.");
        return;
    }

    if (sendButton) {
        sendButton.disabled = true;
    }

    let requestPromise;
    if (imageToSend) {
        const formData = new FormData();
        formData.append("image", imageToSend);
        formData.append("message", message);
        formData.append("language", lang);

        requestPromise = fetch("/api/chat/message", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`
            },
            body: formData
        });
    } else {
        requestPromise = fetch("/api/chat/message", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ message: message, language: lang })
        });
    }

    requestPromise
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
// ADD MENU OPTIONS (UPLOAD IMAGE & OPEN CAMERA)
// =====================================================

const uploadLeaf = document.getElementById("uploadLeaf");
const openCamera = document.getElementById("openCamera");

// Camera DOM elements
const cameraModalBackdrop = document.getElementById("cameraModalBackdrop");
const cameraVideo = document.getElementById("cameraVideo");
const cameraCanvas = document.getElementById("cameraCanvas");
const cameraCapturedPreview = document.getElementById("cameraCapturedPreview");
const cameraOverlayBox = document.getElementById("cameraOverlayBox");
const cameraErrorMessage = document.getElementById("cameraErrorMessage");
const cameraErrorText = document.getElementById("cameraErrorText");
const cameraLiveControls = document.getElementById("cameraLiveControls");
const cameraPreviewControls = document.getElementById("cameraPreviewControls");
const btnCapturePhoto = document.getElementById("btnCapturePhoto");
const btnFlipCamera = document.getElementById("btnFlipCamera");
const btnCancelCamera = document.getElementById("btnCancelCamera");
const btnCloseCameraModal = document.getElementById("btnCloseCameraModal");
const btnRetakePhoto = document.getElementById("btnRetakePhoto");
const btnUsePhoto = document.getElementById("btnUsePhoto");

let activeCameraStream = null;
let currentFacingMode = "environment";
let capturedPhotoBlob = null;

async function startCamera() {
    if (cameraErrorMessage) cameraErrorMessage.style.display = "none";
    if (cameraCapturedPreview) cameraCapturedPreview.style.display = "none";
    if (cameraVideo) cameraVideo.style.display = "block";
    if (cameraOverlayBox) cameraOverlayBox.style.display = "block";
    if (cameraLiveControls) cameraLiveControls.style.display = "flex";
    if (cameraPreviewControls) cameraPreviewControls.style.display = "none";

    stopCameraStream();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showCameraError(window.i18n ? window.i18n.t("camera_error_unavailable") : "Camera is not supported on this browser or device.");
        return;
    }

    try {
        const constraints = {
            video: {
                facingMode: currentFacingMode,
                width: { ideal: 1280 },
                height: { ideal: 960 }
            },
            audio: false
        };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        activeCameraStream = stream;
        if (cameraVideo) {
            cameraVideo.srcObject = stream;
            cameraVideo.play().catch(function () {});
        }
    } catch (err) {
        console.warn("Camera access error with facingMode:", err);
        // Fallback without facingMode
        try {
            const fallbackStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            activeCameraStream = fallbackStream;
            if (cameraVideo) {
                cameraVideo.srcObject = fallbackStream;
                cameraVideo.play().catch(function () {});
            }
        } catch (fallbackErr) {
            console.error("Camera fallback failed:", fallbackErr);
            const isDenied = fallbackErr.name === "NotAllowedError" || fallbackErr.name === "PermissionDeniedError";
            const msg = isDenied
                ? (window.i18n ? window.i18n.t("camera_error_denied") : "Camera access denied. Please enable camera permissions in your browser or upload an image file instead.")
                : (window.i18n ? window.i18n.t("camera_error_unavailable") : "Camera device not found or unavailable on this device.");
            showCameraError(msg);
        }
    }
}

function showCameraError(msg) {
    if (cameraErrorText) cameraErrorText.textContent = msg;
    if (cameraErrorMessage) cameraErrorMessage.style.display = "flex";
    if (cameraOverlayBox) cameraOverlayBox.style.display = "none";
    if (cameraLiveControls) cameraLiveControls.style.display = "none";
}

function stopCameraStream() {
    if (activeCameraStream) {
        activeCameraStream.getTracks().forEach(function (track) {
            try {
                track.stop();
            } catch (e) {}
        });
        activeCameraStream = null;
    }
    if (cameraVideo) {
        cameraVideo.srcObject = null;
    }
}

function openCameraModal() {
    if (addMenu) addMenu.classList.remove("show");
    if (cameraModalBackdrop) cameraModalBackdrop.style.display = "flex";
    capturedPhotoBlob = null;
    startCamera();
}

function closeCameraModal() {
    stopCameraStream();
    capturedPhotoBlob = null;
    if (cameraModalBackdrop) cameraModalBackdrop.style.display = "none";
}

function capturePhoto() {
    if (!cameraVideo || !cameraCanvas) return;
    const width = cameraVideo.videoWidth || 640;
    const height = cameraVideo.videoHeight || 480;
    cameraCanvas.width = width;
    cameraCanvas.height = height;
    const ctx = cameraCanvas.getContext("2d");
    ctx.drawImage(cameraVideo, 0, 0, width, height);

    const dataUrl = cameraCanvas.toDataURL("image/jpeg", 0.92);
    if (cameraCapturedPreview) {
        cameraCapturedPreview.src = dataUrl;
        cameraCapturedPreview.style.display = "block";
    }
    if (cameraVideo) cameraVideo.style.display = "none";
    if (cameraOverlayBox) cameraOverlayBox.style.display = "none";
    if (cameraLiveControls) cameraLiveControls.style.display = "none";
    if (cameraPreviewControls) cameraPreviewControls.style.display = "flex";

    cameraCanvas.toBlob(function (blob) {
        capturedPhotoBlob = blob;
    }, "image/jpeg", 0.92);
}

function retakePhoto() {
    capturedPhotoBlob = null;
    if (cameraCapturedPreview) cameraCapturedPreview.style.display = "none";
    if (cameraVideo) cameraVideo.style.display = "block";
    if (cameraOverlayBox) cameraOverlayBox.style.display = "block";
    if (cameraLiveControls) cameraLiveControls.style.display = "flex";
    if (cameraPreviewControls) cameraPreviewControls.style.display = "none";
}

function usePhoto() {
    if (capturedPhotoBlob) {
        const file = new File([capturedPhotoBlob], "plant_camera_capture.jpg", { type: "image/jpeg" });
        setChatImage(file);
        closeCameraModal();
    } else if (cameraCanvas) {
        cameraCanvas.toBlob(function (blob) {
            const file = new File([blob || new Blob()], "plant_camera_capture.jpg", { type: "image/jpeg" });
            setChatImage(file);
            closeCameraModal();
        }, "image/jpeg", 0.92);
    }
}

function flipCamera() {
    currentFacingMode = currentFacingMode === "environment" ? "user" : "environment";
    startCamera();
}

// Bind camera modal events
if (btnCapturePhoto) btnCapturePhoto.addEventListener("click", capturePhoto);
if (btnRetakePhoto) btnRetakePhoto.addEventListener("click", retakePhoto);
if (btnUsePhoto) btnUsePhoto.addEventListener("click", usePhoto);
if (btnFlipCamera) btnFlipCamera.addEventListener("click", flipCamera);
if (btnCancelCamera) btnCancelCamera.addEventListener("click", closeCameraModal);
if (btnCloseCameraModal) btnCloseCameraModal.addEventListener("click", closeCameraModal);
if (cameraModalBackdrop) {
    cameraModalBackdrop.addEventListener("click", function (e) {
        if (e.target === cameraModalBackdrop) {
            closeCameraModal();
        }
    });
}

// Option 1: Upload Image (triggers file input)
if (uploadLeaf) {
    uploadLeaf.addEventListener("click", function (event) {
        event.stopPropagation();
        if (addMenu) addMenu.classList.remove("show");
        if (chatFileInput) {
            chatFileInput.click();
        }
    });
}

// Option 2: Open Camera
if (openCamera) {
    openCamera.addEventListener("click", function (event) {
        event.stopPropagation();
        openCameraModal();
    });
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
// INITIALIZE CHAT HISTORY ON LOAD & LANGUAGE LISTENER
// =====================================================

window.addEventListener("languageChanged", function(e) {
    if (window.i18n && typeof window.i18n.applyTranslations === "function") {
        window.i18n.applyTranslations();
    }
    const lang = e.detail && e.detail.lang ? e.detail.lang : (window.i18n ? window.i18n.getLang() : "en");
    if (Array.isArray(quickActions) || quickActions instanceof NodeList) {
        quickActions.forEach(function (button) {
            const actionKey = button.getAttribute("data-quick-action");
            if (actionKey) {
                const keyMap = {
                    crop_status: "chip_crop_status",
                    irrigation_guidance: "chip_irrigation",
                    disease_prevention: "chip_disease",
                    weather_info: "chip_weather",
                    harvest_reminders: "chip_harvest",
                    farm_summary: "chip_summary"
                };
                if (keyMap[actionKey] && window.i18n) {
                    button.textContent = window.i18n.t(keyMap[actionKey]);
                }
            }
        });
    }
});

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadChatHistory);
} else {
    loadChatHistory();
}
