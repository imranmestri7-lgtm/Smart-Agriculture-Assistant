const API_BASE_URL = "http://127.0.0.1:5000";

const loginForm = document.getElementById("loginForm");
const loginButton = document.getElementById("loginButton");
const messageBox = document.getElementById("message");


function showMessage(message, type) {
    messageBox.textContent = message;
    messageBox.className = `message ${type}`;
}


loginForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!email || !password) {
        showMessage("Please enter your email and password.", "error");
        return;
    }

    loginButton.disabled = true;
    loginButton.textContent = "Logging in...";

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/auth/login`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    email: email,
                    password: password
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {

            showMessage(
                data.message || "Login failed.",
                "error"
            );

            return;
        }


        // Store logged-in user information
        localStorage.setItem(
            "agriSmartUser",
            JSON.stringify(data.user)
        );


        showMessage(
            "Login successful. Redirecting...",
            "success"
        );


        setTimeout(function () {

            window.location.href = "farmer.html";

        }, 800);


    } catch (error) {

        console.error("Login error:", error);

        showMessage(
            "Unable to connect to the server. Please make sure Flask is running.",
            "error"
        );

    } finally {

        loginButton.disabled = false;
        loginButton.textContent = "Login";

    }

});