(function () {
    "use strict";

    var storageKey = "pdp-admin-theme";

    function getTheme() {
        return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
    }

    function updateToggle(theme) {
        var toggle = document.querySelector(".pdp-theme-toggle");
        if (!toggle) return;

        var isDark = theme === "dark";
        var label = toggle.querySelector(".pdp-theme-toggle__label");

        toggle.setAttribute(
            "aria-label",
            isDark ? "Kunduzgi rejimga o‘tish" : "Tungi rejimga o‘tish"
        );
        toggle.setAttribute("aria-pressed", String(isDark));
        if (label) label.textContent = isDark ? "Light" : "Dark";
    }

    function setTheme(theme) {
        document.documentElement.dataset.theme = theme;
        document.documentElement.style.colorScheme = theme;
        localStorage.setItem(storageKey, theme);
        updateToggle(theme);
    }

    function initSidebarFilter() {
        var filter = document.getElementById("nav-filter");
        var items = Array.from(document.querySelectorAll(".pdp-sidebar__row"));
        if (!filter || !items.length) return;

        function applyFilter() {
            var query = filter.value.trim().toLocaleLowerCase();
            var hasMatch = false;

            items.forEach(function (item) {
                var matches = !query || item.textContent.toLocaleLowerCase().includes(query);
                item.hidden = !matches;
                if (matches) hasMatch = true;
            });

            filter.classList.toggle("no-results", !hasMatch);
        }

        filter.addEventListener("input", applyFilter);
        filter.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                filter.value = "";
                applyFilter();
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        updateToggle(getTheme());
        initSidebarFilter();

        var toggle = document.querySelector(".pdp-theme-toggle");
        if (toggle) {
            toggle.addEventListener("click", function () {
                setTheme(getTheme() === "dark" ? "light" : "dark");
            });
        }

        document.querySelectorAll(".messagelist > li").forEach(function (message) {
            message.setAttribute("role", "status");
        });

        initLoginPhonePrefix();
        initLoginPasswordToggle();
    });

    function digitsOnly(value) {
        return String(value || "").replace(/\D/g, "");
    }

    function localPhoneDigits(value) {
        var digits = digitsOnly(value);
        if (digits.indexOf("998") === 0) {
            digits = digits.slice(3);
        }
        return digits.slice(0, 9);
    }

    function formatLocalPhone(digits) {
        var value = localPhoneDigits(digits);
        var parts = [];
        if (value.length > 0) parts.push(value.slice(0, 2));
        if (value.length > 2) parts.push(value.slice(2, 5));
        if (value.length > 5) parts.push(value.slice(5, 7));
        if (value.length > 7) parts.push(value.slice(7, 9));
        return parts.join(" ");
    }

    function initLoginPhonePrefix() {
        var form = document.getElementById("login-form");
        var input = form && form.querySelector("#id_username");
        if (!form || !input) return;

        input.setAttribute("inputmode", "numeric");
        input.setAttribute("autocomplete", "tel");
        input.setAttribute("placeholder", "90 123 45 67");
        input.setAttribute("maxlength", "12");
        input.value = formatLocalPhone(input.value);

        input.addEventListener("input", function () {
            input.value = formatLocalPhone(input.value);
        });

        input.addEventListener("paste", function (event) {
            event.preventDefault();
            var pasted = (event.clipboardData || window.clipboardData).getData("text");
            input.value = formatLocalPhone(pasted);
        });

        form.addEventListener("submit", function () {
            var local = localPhoneDigits(input.value);
            if (local) {
                input.setAttribute("maxlength", "13");
                input.value = "+998" + local;
            }
        });
    }

    function initLoginPasswordToggle() {
        var input = document.querySelector("#login-form #id_password");
        var toggle = document.getElementById("pdp-toggle-password");
        var icon = toggle && toggle.querySelector(".pdp-login-eye__icon");
        if (!input || !toggle || !icon) return;

        var eyeOpen =
            '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12Z"/><circle cx="12" cy="12" r="3"/>';
        var eyeClosed =
            '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>' +
            '<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>' +
            '<path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>' +
            '<path d="M1 1l22 22"/>';

        input.setAttribute("placeholder", "Parolingizni kiriting");
        input.setAttribute("autocomplete", "current-password");

        toggle.addEventListener("click", function () {
            var show = input.type === "password";
            input.type = show ? "text" : "password";
            toggle.setAttribute("aria-pressed", String(show));
            toggle.setAttribute(
                "aria-label",
                show ? "Parolni yashirish" : "Parolni ko‘rsatish"
            );
            icon.innerHTML = show ? eyeClosed : eyeOpen;
        });
    }
})();
