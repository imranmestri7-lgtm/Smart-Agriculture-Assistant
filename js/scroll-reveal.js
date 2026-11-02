/**
 * js/scroll-reveal.js — AgriSmart Universal Animation & Micro-Interaction Engine
 * Lightweight, hardware-accelerated scroll reveal, card staggering, and stat count-up.
 * Fully vanilla ES6, zero external libraries, respects prefers-reduced-motion.
 */

(function () {
  "use strict";

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Known grid containers to stagger child animations
  const STAGGER_CONTAINERS = [
    ".features-grid",
    ".steps-container",
    ".why-grid",
    ".dashboard-section .dashboard-grid",
    ".dashboard-actions-grid",
    ".summary-cards-grid",
    ".analytics-summary-cards",
    ".iot-metrics-grid",
    ".forecast-grid",
    ".forecast-cards",
    ".tips-grid",
    ".benefits-grid",
    ".farmer-actions-grid",
    ".crop-grid",
    ".farms-grid",
    ".crops-grid"
  ];

  // Specific stat elements that should animate count-up on entrance
  const COUNTUP_SELECTORS = [
    ".stat-number",
    ".summary-card-value",
    ".analytics-stat-val",
    ".hero-card-stat-val",
    "#metricTotalFarms",
    "#metricTotalCrops",
    "#metricTotalDiagnoses",
    "#metricTotalIrrigations",
    "#metricCropsGrowing",
    "#metricCropsReady"
  ];

  /**
   * Smoothly animates numeric text from 0 to target value
   */
  function animateCountUp(el, duration = 850) {
    if (prefersReducedMotion || el.dataset.counted === "true") return;

    const rawText = el.textContent.trim();
    if (!rawText || rawText === "--" || rawText === "0") return;

    // Match leading numbers and optional decimals
    const match = rawText.match(/^([+-]?\d+(?:\.\d+)?)(.*)$/);
    if (!match) return;

    const targetVal = parseFloat(match[1]);
    const suffix = match[2] || "";
    if (isNaN(targetVal) || targetVal === 0) return;

    el.dataset.counted = "true";
    const startTime = performance.now();
    const hasDecimal = match[1].includes(".");
    const decimalPlaces = hasDecimal ? (match[1].split(".")[1] || "").length : 0;

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic: 1 - (1 - progress)^3
      const ease = 1 - Math.pow(1 - progress, 3);
      const currentVal = targetVal * ease;

      el.textContent = (hasDecimal ? currentVal.toFixed(decimalPlaces) : Math.round(currentVal)) + suffix;

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        el.textContent = rawText; // Exact final value
      }
    }

    requestAnimationFrame(update);
  }

  let observer = null;

  /**
   * Initialize or re-scan DOM for reveal targets
   */
  function scanAndObserve() {
    if (prefersReducedMotion) {
      document.querySelectorAll("[data-reveal], .reveal, .reveal-up, .reveal-left, .reveal-right, .reveal-scale")
        .forEach(el => el.classList.add("visible", "is-revealed"));
      return;
    }

    // 1. Setup staggered containers
    STAGGER_CONTAINERS.forEach(selector => {
      document.querySelectorAll(selector).forEach(container => {
        const children = Array.from(container.children).filter(c => c.nodeType === 1);
        children.forEach((child, idx) => {
          if (!child.classList.contains("no-reveal") && !child.classList.contains("visible")) {
            child.classList.add("reveal-up");
            const delay = Math.min(idx * 0.07, 0.45);
            child.style.transitionDelay = `${delay}s`;
          }
        });
      });
    });

    // 2. Collect elements to reveal
    const revealTargets = new Set();

    document.querySelectorAll("[data-reveal], .reveal, .reveal-up, .reveal-left, .reveal-right, .reveal-scale")
      .forEach(el => {
        if (!el.classList.contains("visible")) revealTargets.add(el);
      });

    // Also auto-target major sections and cards
    document.querySelectorAll("section:not(.no-reveal), .feature-card, .dashboard-card, .step-card, .info-card, .forecast-card, .option-card, .notif-card")
      .forEach(el => {
        if (!el.classList.contains("visible") && !el.classList.contains("no-reveal")) {
          if (!el.classList.contains("reveal-up") && !el.classList.contains("reveal-left") && !el.classList.contains("reveal-right")) {
            el.classList.add("reveal-up");
          }
          revealTargets.add(el);
        }
      });

    // 3. Observe elements
    if (!observer) {
      const observerOptions = {
        root: null,
        rootMargin: "0px 0px -30px 0px",
        threshold: 0.06
      };

      observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const el = entry.target;
            el.classList.add("visible", "is-revealed");
            obs.unobserve(el); // Only run once, avoid repeated distractions

            // Trigger count-up on child stats if any
            COUNTUP_SELECTORS.forEach(sel => {
              if (el.matches(sel)) {
                animateCountUp(el);
              } else {
                el.querySelectorAll(sel).forEach(statEl => animateCountUp(statEl));
              }
            });
          }
        });
      }, observerOptions);
    }

    revealTargets.forEach(el => observer.observe(el));
  }

  /**
   * Bind smooth anchor scrolling for hash links
   */
  function bindSmoothAnchors() {
    document.querySelectorAll('a[href^="#"]:not([href="#"]):not([href="#!"])').forEach(anchor => {
      // Avoid duplicate listeners
      if (anchor.dataset.smoothBound === "true") return;
      anchor.dataset.smoothBound = "true";

      anchor.addEventListener("click", function (e) {
        const hash = this.getAttribute("href");
        try {
          const target = document.querySelector(hash);
          if (target) {
            e.preventDefault();
            const nav = document.querySelector(".navbar");
            const navHeight = nav ? nav.offsetHeight : 72;
            const top = target.getBoundingClientRect().top + window.pageYOffset - navHeight - 16;
            window.scrollTo({
              top: Math.max(0, top),
              behavior: "smooth"
            });
          }
        } catch (err) {
          // Fall back gracefully if selector fails
        }
      });
    });
  }

  function init() {
    scanAndObserve();
    bindSmoothAnchors();

    // Re-check periodically when dynamic tabs change or API loads content
    setTimeout(scanAndObserve, 500);
    setTimeout(scanAndObserve, 1500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose global helper for dynamic content reruns (e.g. after tab switch or API fetch)
  window.AgriSmartAnimations = {
    refresh: scanAndObserve,
    countUp: animateCountUp
  };
})();
