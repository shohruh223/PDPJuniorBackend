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
    });
})();
