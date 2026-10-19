const API_URL = "http://127.0.0.1:5000/api/auth";


// --------------------------------------------------
// ELEMENTS
// --------------------------------------------------

const registerForm = document.getElementById("registerForm");

const fullNameInput = document.getElementById("fullName");

const mobileNumberInput =
    document.getElementById("mobileNumber");

const emailInput =
    document.getElementById("email");

const passwordInput =
    document.getElementById("password");

const confirmPasswordInput =
    document.getElementById("confirmPassword");

const languageInput =
    document.getElementById("language");

const phoneFields =
    document.getElementById("phoneFields");

const emailFields =
    document.getElementById("emailFields");

const registerButton =
    document.getElementById("registerButton");

const message =
    document.getElementById("message");

const phoneMethod =
    document.getElementById("phoneMethod");

const emailMethod =
    document.getElementById("emailMethod");


// --------------------------------------------------
// MESSAGE
// --------------------------------------------------

function showMessage(text, type) {

    message.textContent = text;

    message.className =
        "message " + type;
}


function clearMessage() {

    message.textContent = "";

    message.className = "message";
}


// --------------------------------------------------
// AUTH METHOD
// --------------------------------------------------

function getAuthMethod() {

    if (phoneMethod.checked) {
        return "phone";
    }

    return "email";
}


// --------------------------------------------------
// SWITCH PHONE / EMAIL
// --------------------------------------------------

function updateAuthMethod() {

    clearMessage();

    const method = getAuthMethod();


    if (method === "phone") {

        phoneFields.classList.remove("hidden");

        emailFields.classList.add("hidden");


        mobileNumberInput.required = true;

        emailInput.required = false;
        passwordInput.required = false;
        confirmPasswordInput.required = false;


    } else {

        phoneFields.classList.add("hidden");

        emailFields.classList.remove("hidden");


        mobileNumberInput.required = false;

        emailInput.required = true;
        passwordInput.required = true;
        confirmPasswordInput.required = true;
    }
}


phoneMethod.addEventListener(
    "change",
    updateAuthMethod
);


emailMethod.addEventListener(
    "change",
    updateAuthMethod
);


// --------------------------------------------------
// MOBILE NUMBER VALIDATION
// --------------------------------------------------

mobileNumberInput.addEventListener(
    "input",
    function () {

        this.value = this.value
            .replace(/\D/g, "")
            .slice(0, 10);

    }
);


// --------------------------------------------------
// REGISTER
// --------------------------------------------------

registerForm.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();

        clearMessage();


        const fullName =
            fullNameInput.value.trim();

        const preferredLanguage =
            languageInput.value;

        const authMethod =
            getAuthMethod();


        // --------------------------------------------------
        // FULL NAME
        // --------------------------------------------------

        if (!fullName) {

            showMessage(
                "Please enter your full name.",
                "error"
            );

            return;
        }


        // --------------------------------------------------
        // PHONE REGISTRATION
        // --------------------------------------------------

        if (authMethod === "phone") {

            const mobileNumber =
                mobileNumberInput.value.trim();


            if (!/^\d{10}$/.test(mobileNumber)) {

                showMessage(
                    "Please enter a valid 10-digit mobile number.",
                    "error"
                );

                return;
            }


            registerButton.disabled = true;

            registerButton.textContent =
                "Creating Account...";


            try {

                const response =
                    await fetch(
                        `${API_URL}/register`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({

                                full_name:
                                    fullName,

                                auth_method:
                                    "phone",

                                mobile_number:
                                    mobileNumber,

                                preferred_language:
                                    preferredLanguage

                            })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.message ||
                        "Registration failed."
                    );
                }


                showMessage(
                    "Account created successfully! Redirecting to login...",
                    "success"
                );


                setTimeout(
                    function () {

                        window.location.href =
                            "login.html";

                    },
                    1200
                );


            } catch (error) {

                console.error(
                    "Phone registration error:",
                    error
                );


                showMessage(
                    error.message ||
                    "Unable to connect to the server.",
                    "error"
                );


            } finally {

                registerButton.disabled =
                    false;

                registerButton.textContent =
                    "Create Account";
            }


            return;
        }


        // --------------------------------------------------
        // EMAIL REGISTRATION
        // --------------------------------------------------

        const email =
            emailInput.value.trim().toLowerCase();

        const password =
            passwordInput.value;

        const confirmPassword =
            confirmPasswordInput.value;


        if (!email) {

            showMessage(
                "Please enter your email address.",
                "error"
            );

            return;
        }


        if (password.length < 6) {

            showMessage(
                "Password must contain at least 6 characters.",
                "error"
            );

            return;
        }


        if (password !== confirmPassword) {

            showMessage(
                "Passwords do not match.",
                "error"
            );

            return;
        }


        registerButton.disabled = true;

        registerButton.textContent =
            "Creating Account...";


        try {

            const response =
                await fetch(
                    `${API_URL}/register`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            full_name:
                                fullName,

                            auth_method:
                                "email",

                            email:
                                email,

                            password:
                                password,

                            confirm_password:
                                confirmPassword,

                            preferred_language:
                                preferredLanguage

                        })
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.message ||
                    "Registration failed."
                );
            }


            showMessage(
                "Account created successfully! Redirecting to login...",
                "success"
            );


            setTimeout(
                function () {

                    window.location.href =
                        "login.html";

                },
                1200
            );


        } catch (error) {

            console.error(
                "Email registration error:",
                error
            );


            showMessage(
                error.message ||
                "Unable to connect to the server.",
                "error"
            );


        } finally {

            registerButton.disabled =
                false;

            registerButton.textContent =
                "Create Account";
        }

    }
);


// --------------------------------------------------
// INITIAL STATE
// --------------------------------------------------

updateAuthMethod();