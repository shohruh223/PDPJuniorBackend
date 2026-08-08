(function () {
    function getAdminModelBaseUrl() {
        const parts = window.location.pathname.split("/").filter(Boolean);

        if (parts[parts.length - 1] === "add") {
            parts.pop();
            return "/" + parts.join("/") + "/";
        }

        if (parts[parts.length - 1] === "change") {
            parts.pop();
            parts.pop();
            return "/" + parts.join("/") + "/";
        }

        return window.location.pathname;
    }

    function clearSelect(select, placeholder) {
        select.innerHTML = "";

        const option = document.createElement("option");
        option.value = "";
        option.textContent = placeholder;

        select.appendChild(option);
    }

    function fillSelect(select, items, placeholder) {
        clearSelect(select, placeholder);

        items.forEach(function (item) {
            const option = document.createElement("option");
            option.value = item.id;
            option.textContent = item.name;

            select.appendChild(option);
        });
    }

    function initQuestionFilters() {
        const courseSelect = document.getElementById("id_course");
        const moduleSelect = document.getElementById("id_module");
        const lessonSelect = document.getElementById("id_lesson");

        if (!courseSelect || !moduleSelect || !lessonSelect) {
            return;
        }

        const baseUrl = getAdminModelBaseUrl();

        courseSelect.addEventListener("change", function () {
            const courseId = courseSelect.value;

            clearSelect(moduleSelect, "Module tanlang");
            clearSelect(lessonSelect, "Avval moduleni tanlang");

            if (!courseId) {
                return;
            }

            fetch(`${baseUrl}get-modules/?course_id=${courseId}`)
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    fillSelect(moduleSelect, data.results, "Module tanlang");
                });
        });

        moduleSelect.addEventListener("change", function () {
            const moduleId = moduleSelect.value;

            clearSelect(lessonSelect, "Lesson tanlang");

            if (!moduleId) {
                return;
            }

            fetch(`${baseUrl}get-lessons/?module_id=${moduleId}`)
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    fillSelect(lessonSelect, data.results, "Lesson tanlang");
                });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initQuestionFilters);
    } else {
        initQuestionFilters();
    }
})();