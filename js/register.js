const API_BASE_URL = "http://127.0.0.1:5000";

const registerForm = document.getElementById("registerForm");
const registerButton = document.getElementById("registerButton");
const messageBox = document.getElementById("message");


function showMessage(message, type) {
    messageBox.textContent = message;
    messageBox.className = `message ${type}`;
}


registerForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    const fullName =
        document.getElementById("fullName").value.trim();

    const email =
        document.getElementById("email").value.trim();

    const password =
        document.getElementById("password").value;

    const confirmPassword =
        document.getElementById("confirmPassword").value;


    if (!fullName || !email || !password || !confirmPassword) {

        showMessage(
            "Please fill in all required fields.",
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
    registerButton.textContent = "Creating Account...";


    try {

        const response = await fetch(
            `${API_BASE_URL}/api/auth/register`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    password: password
                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            showMessage(
                data.message || "Registration failed.",
                "error"
            );

            return;
        }


        showMessage(
            "Account created successfully. Redirecting to login...",
            "success"
        );


        setTimeout(function () {

            window.location.href = "login.html";

        }, 1000);


    } catch (error) {

        console.error("Registration error:", error);

        showMessage(
            "Unable to connect to the server. Please make sure Flask is running.",
            "error"
        );

    } finally {

        registerButton.disabled = false;
        registerButton.textContent = "Create Account";

    }

});