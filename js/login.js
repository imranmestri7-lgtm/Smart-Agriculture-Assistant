const API_URL = "http://127.0.0.1:5000/api/auth";

const loginForm = document.getElementById("loginForm");
const mobileNumberInput = document.getElementById("mobileNumber");

const sendOtpButton = document.getElementById("sendOtpButton");

const otpSection = document.getElementById("otpSection");
const otpInput = document.getElementById("otp");
const verifyOtpButton = document.getElementById("verifyOtpButton");
const changeNumberButton = document.getElementById("changeNumberButton");

const message = document.getElementById("message");

const developmentOtp = document.getElementById("developmentOtp");
const otpValue = document.getElementById("otpValue");


/* --------------------------------------------------
   SHOW MESSAGE
-------------------------------------------------- */

function showMessage(text, type) {

    message.textContent = text;

    message.className = "message " + type;
}


/* --------------------------------------------------
   CLEAR MESSAGE
-------------------------------------------------- */

function clearMessage() {

    message.textContent = "";
    message.className = "message";
}


/* --------------------------------------------------
   ONLY ALLOW NUMBERS
-------------------------------------------------- */

mobileNumberInput.addEventListener("input", function () {

    this.value = this.value.replace(/\D/g, "").slice(0, 10);

});


otpInput.addEventListener("input", function () {

    this.value = this.value.replace(/\D/g, "").slice(0, 6);

});


/* --------------------------------------------------
   SEND OTP
-------------------------------------------------- */

loginForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    clearMessage();

    const mobileNumber = mobileNumberInput.value.trim();

    if (!/^\d{10}$/.test(mobileNumber)) {

        showMessage(
            "Please enter a valid 10-digit mobile number.",
            "error"
        );

        return;
    }

    sendOtpButton.disabled = true;
    sendOtpButton.textContent = "Sending OTP...";

    try {

        const response = await fetch(
            `${API_URL}/send-otp`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    mobile_number: mobileNumber
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.message || "Unable to send OTP."
            );
        }


        /* Show OTP section */

        otpSection.classList.add("show");

        /* Hide mobile form button */

        sendOtpButton.style.display = "none";

        mobileNumberInput.readOnly = true;


        /* Development OTP */

        if (data.development_otp) {

            otpValue.textContent = data.development_otp;

            developmentOtp.style.display = "block";
        }


        showMessage(
            "OTP generated successfully. Enter the OTP to continue.",
            "success"
        );


        /* Focus OTP field */

        otpInput.focus();


    } catch (error) {

        console.error("Send OTP error:", error);

        showMessage(
            error.message || "Unable to connect to the server.",
            "error"
        );

    } finally {

        sendOtpButton.disabled = false;
        sendOtpButton.textContent = "Send OTP";

    }

});


/* --------------------------------------------------
   VERIFY OTP
-------------------------------------------------- */

verifyOtpButton.addEventListener("click", async function () {

    clearMessage();

    const mobileNumber = mobileNumberInput.value.trim();
    const otp = otpInput.value.trim();


    if (!/^\d{6}$/.test(otp)) {

        showMessage(
            "Please enter the 6-digit OTP.",
            "error"
        );

        return;
    }


    verifyOtpButton.disabled = true;
    verifyOtpButton.textContent = "Verifying...";


    try {

        const response = await fetch(
            `${API_URL}/verify-otp`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    mobile_number: mobileNumber,
                    otp: otp
                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.message || "OTP verification failed."
            );
        }


        /* Save logged-in user */

        localStorage.setItem(
            "agriSmartUser",
            JSON.stringify(data.user)
        );


        showMessage(
            "OTP verified successfully! Redirecting...",
            "success"
        );


        /* Redirect to Farmer Assistant */

        setTimeout(function () {

            window.location.href = "farmer.html";

        }, 800);


    } catch (error) {

        console.error("OTP verification error:", error);

        showMessage(
            error.message || "Unable to verify OTP.",
            "error"
        );

    } finally {

        verifyOtpButton.disabled = false;
        verifyOtpButton.textContent = "Verify OTP";

    }

});


/* --------------------------------------------------
   CHANGE MOBILE NUMBER
-------------------------------------------------- */

changeNumberButton.addEventListener("click", function () {

    clearMessage();

    otpSection.classList.remove("show");

    developmentOtp.style.display = "none";

    otpInput.value = "";

    mobileNumberInput.readOnly = false;

    sendOtpButton.style.display = "block";

    mobileNumberInput.focus();

});