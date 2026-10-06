
// 
const API_KEY = "8568afaf35e5465c9dc62903260609";




const locationInput = document.getElementById("location");
const searchButton = document.getElementById("searchWeather");
const suggestionsBox = document.getElementById("suggestions");




let selectedLocation = null;
let searchTimer = null;


// ========================================
// CHECK API KEY
// ========================================

if (!API_KEY || API_KEY === "YOUR_API_KEY_HERE") {

    console.error("WeatherAPI key is missing.");

}


// ========================================
// LOCATION SUGGESTIONS
// ========================================

locationInput.addEventListener("input", function () {

    clearTimeout(searchTimer);

    const query = locationInput.value.trim();

    selectedLocation = null;

    suggestionsBox.innerHTML = "";

    if (query.length < 2) {
        return;
    }

    searchTimer = setTimeout(async function () {

        try {

            const url =
                "https://api.weatherapi.com/v1/search.json" +
                "?key=" + API_KEY +
                "&q=" + encodeURIComponent(query);

            const response = await fetch(url);

            if (!response.ok) {
                return;
            }

            const locations = await response.json();

            suggestionsBox.innerHTML = "";

            // Only India
            const indiaLocations = locations.filter(function (location) {
                return location.country === "India";
            });


            // Show maximum 5 suggestions
            indiaLocations.slice(0, 5).forEach(function (location) {

                const item = document.createElement("div");

                item.className = "suggestion-item";

                item.textContent =
                    "📍 " +
                    location.name +
                    (location.region
                        ? ", " + location.region
                        : "");

                item.addEventListener("click", function () {

                    locationInput.value = location.name;

                    selectedLocation = location;

                    suggestionsBox.innerHTML = "";

                    searchLocation();

                });

                suggestionsBox.appendChild(item);

            });

        }

        catch (error) {

            console.log("Suggestion error:", error);

        }

    }, 300);

});


// ========================================
// SEARCH LOCATION
// ========================================

async function searchLocation() {

    const location = locationInput.value.trim();


    // Empty search
    if (location === "") {

        locationInput.focus();

        return;

    }


    // Loading
    searchButton.disabled = true;

    searchButton.textContent = "⏳";


    suggestionsBox.innerHTML = "";


    try {

        let query;


        // If suggestion was selected
        if (selectedLocation) {

            query =
                selectedLocation.lat +
                "," +
                selectedLocation.lon;

        }

        // Normal typing / Enter search
        else {

            query = location + ", India";

        }


        // ========================================
        // WEATHER API
        // ========================================

        let url =
            "https://api.weatherapi.com/v1/forecast.json" +
            "?key=" + API_KEY +
            "&q=" + encodeURIComponent(query) +
            "&days=5" +
            "&aqi=no" +
            "&alerts=no";


        let response = await fetch(url);

        let data = await response.json();


        // ========================================
        // SECOND ATTEMPT
        // ========================================

        // If "Pune, India" doesn't work,
        // try simply "Pune"

        if (!response.ok) {

            console.log("First weather search failed:", data);


            // Try without India
            url =
                "https://api.weatherapi.com/v1/forecast.json" +
                "?key=" + API_KEY +
                "&q=" + encodeURIComponent(location) +
                "&days=5" +
                "&aqi=no" +
                "&alerts=no";


            response = await fetch(url);

            data = await response.json();

        }


        // ========================================
        // FINAL RESPONSE CHECK
        // ========================================

        if (!response.ok) {

            console.log("WeatherAPI error:", data);

            document.querySelector(".weather-heading p").textContent =
                "Weather data is not available for this location.";

            return;

        }


        // ========================================
        // UPDATE WEATHER
        // ========================================

        updateWeather(data);

    }


    catch (error) {

        console.error("Weather error:", error);

        document.querySelector(".weather-heading p").textContent =
            "Unable to connect to weather service.";

    }


    finally {

        searchButton.disabled = false;

        searchButton.textContent = "🔍";

    }

}


// ========================================
// UPDATE WEATHER
// ========================================

function updateWeather(data) {


    // ========================================
    // LOCATION
    // ========================================

    const locationName = data.location.name;

    const region = data.location.region;


    document.querySelector(".weather-heading p").textContent =
        "Current weather in " +
        locationName +
        (region ? ", " + region : "");


    // ========================================
    // CURRENT TEMPERATURE
    // ========================================

    document.querySelector(".current-main h2").textContent =
        Math.round(data.current.temp_c) + "°C";


    // ========================================
    // CONDITION
    // ========================================

    document.querySelector(".current-main p").textContent =
        data.current.condition.text;


    // ========================================
    // EXACT WEATHERAPI CURRENT ICON
    // ========================================

    const currentIcon =
        document.querySelector(".weather-icon");


    currentIcon.innerHTML = "";


    const currentImage =
        document.createElement("img");


    currentImage.src =
        "https:" + data.current.condition.icon;


    currentImage.alt =
        data.current.condition.text;


    currentImage.title =
        data.current.condition.text;


    currentImage.width = 80;

    currentImage.height = 80;


    currentIcon.appendChild(currentImage);


    // ========================================
    // WEATHER DETAILS
    // ========================================

    const details =
        document.querySelectorAll(".weather-detail strong");


    if (details.length >= 3) {

        // Humidity
        details[0].textContent =
            data.current.humidity + "%";


        // Wind
        details[1].textContent =
            data.current.wind_kph + " km/h";


        // Rain
        details[2].textContent =
            data.current.precip_mm + " mm";

    }


    // ========================================
    // 5 DAY FORECAST
    // ========================================

    const forecastCards =
        document.querySelectorAll(".forecast-card");


    data.forecast.forecastday.forEach(function (day, index) {


        if (!forecastCards[index]) {
            return;
        }


        const card =
            forecastCards[index];


        // Date
        const date =
            new Date(day.date + "T00:00:00");


        const dayName =
            date.toLocaleDateString(
                "en-US",
                {
                    weekday: "short"
                }
            );


        // Day
        card.querySelector("h3").textContent =
            dayName;


        // ========================================
        // EXACT FORECAST ICON
        // ========================================

        const iconContainer =
            card.querySelector(".forecast-icon");


        iconContainer.innerHTML = "";


        const forecastImage =
            document.createElement("img");


        forecastImage.src =
            "https:" + day.day.condition.icon;


        forecastImage.alt =
            day.day.condition.text;


        forecastImage.title =
            day.day.condition.text;


        forecastImage.width = 64;

        forecastImage.height = 64;


        iconContainer.appendChild(forecastImage);


        // ========================================
        // MAX TEMPERATURE
        // ========================================

        card.querySelector("strong").textContent =
            Math.round(day.day.maxtemp_c) + "°C";


        // ========================================
        // MIN TEMPERATURE
        // ========================================

        card.querySelector("p").textContent =
            Math.round(day.day.mintemp_c) + "°C";


        // ========================================
        // RAIN CHANCE
        // ========================================

        card.querySelector("small").textContent =
            "🌧️ " +
            day.day.daily_chance_of_rain +
            "%";

    });


    // ========================================
    // ADDITIONAL INFORMATION
    // ========================================

    const additionalCards =
        document.querySelectorAll(".additional-card");


    if (additionalCards.length >= 4) {


        // Sunrise
        additionalCards[0]
            .querySelector("strong")
            .textContent =
            data.forecast.forecastday[0].astro.sunrise;


        // Sunset
        additionalCards[1]
            .querySelector("strong")
            .textContent =
            data.forecast.forecastday[0].astro.sunset;


        // Pressure
        additionalCards[2]
            .querySelector("strong")
            .textContent =
            data.current.pressure_mb +
            " hPa";


        // Visibility
        additionalCards[3]
            .querySelector("strong")
            .textContent =
            data.current.vis_km +
            " km";

    }


    // ========================================
    // FARMING ADVICE
    // ========================================

    updateFarmingAdvice(data);

}


// ========================================
// FARMING ADVICE
// ========================================

function updateFarmingAdvice(data) {


    const adviceCards =
        document.querySelectorAll(".advice-card");


    if (adviceCards.length < 4) {
        return;
    }


    const tomorrow =
        data.forecast.forecastday[1];


    if (!tomorrow) {
        return;
    }


    const rainChance =
        tomorrow.day.daily_chance_of_rain;


    // ========================================
    // IRRIGATION
    // ========================================

    adviceCards[0]
        .querySelector("p")
        .textContent =
        rainChance >= 50
            ? "Not Recommended"
            : "Recommended";


    // ========================================
    // RAIN ALERT
    // ========================================

    adviceCards[1]
        .querySelector("p")
        .textContent =
        rainChance >= 50
            ? "Rain expected tomorrow (" +
              rainChance +
              "%)"
            : "Low chance of rain tomorrow (" +
              rainChance +
              "%)";


    // ========================================
    // CROP PROTECTION
    // ========================================

    adviceCards[2]
        .querySelector("p")
        .textContent =
        rainChance >= 60
            ? "Protect crops from excess moisture."
            : "Normal crop protection recommended.";


    // ========================================
    // FARM ACTIVITY
    // ========================================

    adviceCards[3]
        .querySelector("p")
        .textContent =
        rainChance < 40
            ? "Good weather for farm activities."
            : "Avoid outdoor activities during rain.";

}


// ========================================
// SEARCH BUTTON
// ========================================

searchButton.addEventListener(
    "click",
    function () {

        searchLocation();

    }
);


// ========================================
// ENTER KEY
// ========================================

locationInput.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Enter") {

            event.preventDefault();

            clearTimeout(searchTimer);

            suggestionsBox.innerHTML = "";

            selectedLocation = null;

            searchLocation();

        }

    }
);


// ========================================
// CLICK OUTSIDE
// ========================================

document.addEventListener(
    "click",
    function (event) {

        if (
            !locationInput.contains(event.target) &&
            !suggestionsBox.contains(event.target)
        ) {

            suggestionsBox.innerHTML = "";

        }

    }
);