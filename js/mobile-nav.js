// mobile-nav.js – Responsive mobile navigation drawer for AgriSmart
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector(".mobile-menu-toggle");
    const navLinks = document.querySelector(".nav-links");
    if (!toggle || !navLinks) return;

    toggle.addEventListener("click", () => {
        const isOpen = navLinks.classList.toggle("mobile-open");
        toggle.classList.toggle("active", isOpen);
        toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    // Close when clicking any nav link
    navLinks.querySelectorAll("a").forEach(link => {
        link.addEventListener("click", () => {
            navLinks.classList.remove("mobile-open");
            toggle.classList.remove("active");
            toggle.setAttribute("aria-expanded", "false");
        });
    });

    // Close on click outside
    document.addEventListener("click", (e) => {
        if (!navLinks.contains(e.target) && !toggle.contains(e.target) && navLinks.classList.contains("mobile-open")) {
            navLinks.classList.remove("mobile-open");
            toggle.classList.remove("active");
            toggle.setAttribute("aria-expanded", "false");
        }
    });
});
