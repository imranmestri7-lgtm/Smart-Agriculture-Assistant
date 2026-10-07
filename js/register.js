const API_URL = "http://127.0.0.1:5000/api/auth";

const registerForm = document.getElementById("registerForm");

const fullNameInput = document.getElementById("fullName");
const mobileNumberInput = document.getElementById("mobileNumber");
const languageInput = document.getElementById("language");

const registerButton = document.getElementById("registerButton");

const message = document.getElementById("message");


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
   ONLY ALLOW NUMBERS IN MOBILE FIELD
-------------------------------------------------- */

mobileNumberInput.addEventListener("input", function () {

    this.value = this.value
        .replace(/\D/g, "")
        .slice(0, 10);

});


/* --------------------------------------------------
   REGISTER USER
-------------------------------------------------- */

registerForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    clearMessage();


    const fullName = fullNameInput.value.trim();

    const mobileNumber = mobileNumberInput.value.trim();

    const preferredLanguage = languageInput.value;


    /* --------------------------------------------------
       VALIDATE FULL NAME
    -------------------------------------------------- */

    if (!fullName) {

        showMessage(
            "Please enter your full name.",
            "error"
        );

        return;
    }


    /* --------------------------------------------------
       VALIDATE MOBILE NUMBER
    -------------------------------------------------- */

    if (!/^\d{10}$/.test(mobileNumber)) {

        showMessage(
            "Please enter a valid 10-digit mobile number.",
            "error"
        );

        return;
    }


    /* --------------------------------------------------
       DISABLE BUTTON
    -------------------------------------------------- */

    registerButton.disabled = true;

    registerButton.textContent = "Creating Account...";


    try {

        const response = await fetch(
            `${API_URL}/register`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    full_name: fullName,

                    mobile_number: mobileNumber,

                    preferred_language: preferredLanguage

                })
            }
        );


        const data = await response.json();


        /* --------------------------------------------------
           HANDLE BACKEND ERROR
        -------------------------------------------------- */

        if (!response.ok) {

            throw new Error(
                data.message || "Registration failed."
            );
        }


        /* --------------------------------------------------
           SUCCESS
        -------------------------------------------------- */

        showMessage(
            "Account created successfully! Redirecting to login...",
            "success"
        );


        /* --------------------------------------------------
           REDIRECT TO LOGIN
        -------------------------------------------------- */

        setTimeout(function () {

            window.location.href = "login.html";

        }, 1200);


    } catch (error) {

        console.error(
            "Registration error:",
            error
        );

        showMessage(
            error.message ||
            "Unable to connect to the server.",
            "error"
        );

    } finally {

        registerButton.disabled = false;

        registerButton.textContent = "Create Account";

    }

});