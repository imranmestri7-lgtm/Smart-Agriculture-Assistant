const API_URL = "/api/auth";

const phoneOption = document.getElementById("phoneOption");
const emailOption = document.getElementById("emailOption");

const phoneLoginForm = document.getElementById("phoneLoginForm");
const emailLoginForm = document.getElementById("emailLoginForm");

const mobileNumber = document.getElementById("mobileNumber");
const otp = document.getElementById("otp");

const sendOtpBtn = document.getElementById("sendOtpBtn");
const verifyOtpBtn = document.getElementById("verifyOtpBtn");

const developmentOtp = document.getElementById("developmentOtp");
const otpValue = document.getElementById("otpValue");

const changeNumberBtn = document.getElementById("changeNumberBtn");

const email = document.getElementById("email");
const password = document.getElementById("password");
const emailLoginBtn = document.getElementById("emailLoginBtn");

const message = document.getElementById("message");


// Show message
function showMessage(text, type) {
    message.textContent = text;
    message.className = "message " + type;
}


// Clear message
function clearMessage() {
    message.textContent = "";
    message.className = "message";
}


// Switch to phone login
phoneOption.addEventListener("click", () => {

    phoneOption.classList.add("active");
    emailOption.classList.remove("active");

    phoneLoginForm.style.display = "block";
    emailLoginForm.style.display = "none";

    clearMessage();
});


// Switch to email login
emailOption.addEventListener("click", () => {

    emailOption.classList.add("active");
    phoneOption.classList.remove("active");

    phoneLoginForm.style.display = "none";
    emailLoginForm.style.display = "block";

    clearMessage();
});


// Allow only numbers in mobile field
mobileNumber.addEventListener("input", () => {

    mobileNumber.value = mobileNumber.value
        .replace(/\D/g, "")
        .slice(0, 10);
});


// Allow only numbers in OTP field
otp.addEventListener("input", () => {

    otp.value = otp.value
        .replace(/\D/g, "")
        .slice(0, 6);
});


// Send OTP
sendOtpBtn.addEventListener("click", async () => {

    clearMessage();

    const mobile = mobileNumber.value.trim();

    if (!/^\d{10}$/.test(mobile)) {

        showMessage(
            (window.i18n ? window.i18n.t("msg_invalid_mobile") : "Please enter a valid 10-digit mobile number."),
            "error"
        );

        return;
    }

    sendOtpBtn.disabled = true;
    sendOtpBtn.textContent = (window.i18n ? window.i18n.t("login_send_otp_btn") : "Sending...");

    try {

        const response = await fetch(
            `${API_URL}/send-otp`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "X-Language": (window.i18n ? window.i18n.getLang() : "en")
                },

                body: JSON.stringify({
                    mobile_number: mobile
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.message || (window.i18n ? window.i18n.t("invalid_otp") : "Unable to send OTP.")
            );
        }

        showMessage(
            data.message || (window.i18n ? window.i18n.t("msg_otp_sent") : "OTP sent successfully."),
            "success"
        );

        // Development OTP
        if (data.development_otp) {

            otpValue.textContent = data.development_otp;
            developmentOtp.style.display = "block";
    // Show OTP input row after OTP is sent
    document.getElementById('otpRow').style.display = 'grid';
        }

        changeNumberBtn.style.display = "block";

    } catch (error) {

        console.error("Send OTP error:", error);

        showMessage(
            error.message || "Something went wrong while sending OTP.",
            "error"
        );

    } finally {

        sendOtpBtn.disabled = false;
        sendOtpBtn.textContent = "Send OTP";
    }
});


// Verify OTP and login
phoneLoginForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    clearMessage();

    const mobile = mobileNumber.value.trim();
    const otpValueEntered = otp.value.trim();

    if (!/^\d{10}$/.test(mobile)) {

        showMessage(
            "Please enter a valid 10-digit mobile number.",
            "error"
        );

        return;
    }

    if (!/^\d{6}$/.test(otpValueEntered)) {

        showMessage(
            (window.i18n ? window.i18n.t("msg_enter_otp") : "Please enter the 6-digit OTP."),
            "error"
        );

        return;
    }

    verifyOtpBtn.disabled = true;
    verifyOtpBtn.textContent = (window.i18n ? window.i18n.t("login_verify_otp_btn") : "Verifying...");

    try {

        const response = await fetch(
            `${API_URL}/verify-otp`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "X-Language": (window.i18n ? window.i18n.getLang() : "en")
                },

                body: JSON.stringify({
                    mobile_number: mobile,
                    otp: otpValueEntered
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.message || (window.i18n ? window.i18n.t("invalid_otp") : "OTP verification failed.")
            );
        }

        // Save logged-in user and signed authentication token
        localStorage.setItem(
            "agriSmartUser",
            JSON.stringify(data.user)
        );

        if (data.token) {
            localStorage.setItem("agriSmartToken", data.token);
        } else {
            throw new Error("Login token was not returned by the server.");
        }

        if (data.user && data.user.preferred_language) {
            const langMap = { "English": "en", "Marathi": "mr", "Hindi": "hi" };
            const langCode = langMap[data.user.preferred_language] || data.user.preferred_language;
            if (["en", "mr", "hi"].includes(langCode)) {
                if (window.i18n && typeof window.i18n.setLang === "function") {
                    window.i18n.setLang(langCode);
                } else {
                    localStorage.setItem("lang", langCode);
                }
            }
        }

        showMessage(
            (window.i18n ? window.i18n.t("msg_login_success") : "Login successful! Redirecting..."),
            "success"
        );

        setTimeout(() => {
            window.location.href = "farmer.html";
        }, 800);

    } catch (error) {

        console.error("OTP verification error:", error);

        showMessage(
            error.message || "Invalid OTP.",
            "error"
        );

    } finally {

        verifyOtpBtn.disabled = false;
        verifyOtpBtn.textContent = "Verify OTP & Login";
    }
});


// Email login
emailLoginForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    clearMessage();

    const emailValue = email.value.trim().toLowerCase();
    const passwordValue = password.value;

    if (!emailValue) {

        showMessage(
            (window.i18n ? window.i18n.t("msg_enter_email") : "Please enter your email address."),
            "error"
        );

        return;
    }

    if (!passwordValue) {

        showMessage(
            (window.i18n ? window.i18n.t("msg_enter_password") : "Please enter your password."),
            "error"
        );

        return;
    }

    emailLoginBtn.disabled = true;
    emailLoginBtn.textContent = (window.i18n ? window.i18n.t("login_submit_btn") : "Logging in...");

    try {

        const response = await fetch(
            `${API_URL}/login`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "X-Language": (window.i18n ? window.i18n.getLang() : "en")
                },

                body: JSON.stringify({
                    email: emailValue,
                    password: passwordValue
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.message || (window.i18n ? window.i18n.t("invalid_credentials") : "Login failed.")
            );
        }

        // Save logged-in user and signed authentication token
        localStorage.setItem(
            "agriSmartUser",
            JSON.stringify(data.user)
        );

        if (data.token) {
            localStorage.setItem("agriSmartToken", data.token);
        } else {
            throw new Error("Login token was not returned by the server.");
        }

        if (data.user && data.user.preferred_language) {
            const langMap = { "English": "en", "Marathi": "mr", "Hindi": "hi" };
            const langCode = langMap[data.user.preferred_language] || data.user.preferred_language;
            if (["en", "mr", "hi"].includes(langCode)) {
                if (window.i18n && typeof window.i18n.setLang === "function") {
                    window.i18n.setLang(langCode);
                } else {
                    localStorage.setItem("lang", langCode);
                }
            }
        }

        showMessage(
            (window.i18n ? window.i18n.t("msg_login_success") : "Login successful! Redirecting..."),
            "success"
        );

        setTimeout(() => {
            window.location.href = "farmer.html";
        }, 800);

    } catch (error) {

        console.error("Email login error:", error);

        showMessage(
            error.message || "Invalid email or password.",
            "error"
        );

    } finally {

        emailLoginBtn.disabled = false;
        emailLoginBtn.textContent = "Login";
    }
});


// Change mobile number
changeNumberBtn.addEventListener("click", () => {

    mobileNumber.value = "";
    otp.value = "";

    developmentOtp.style.display = "none";
    document.getElementById('otpRow').style.display = 'none';

    clearMessage();

    mobileNumber.focus();
});