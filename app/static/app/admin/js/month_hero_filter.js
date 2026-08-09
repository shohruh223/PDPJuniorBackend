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

    function getCurrentHeroId() {
        const parts = window.location.pathname.split("/").filter(Boolean);

        if (parts[parts.length - 1] !== "change") {
            return "";
        }

        return parts[parts.length - 2] || "";
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

    function loadOptions(url, select, placeholder, selectedValue) {
        select.disabled = true;

        return fetch(url)
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Ro‘yxatni yuklab bo‘lmadi.");
                }
                return response.json();
            })
            .then(function (data) {
                fillSelect(select, data.results, placeholder);

                if (selectedValue) {
                    select.value = selectedValue;
                }
            })
            .catch(function () {
                clearSelect(select, "Ma’lumot topilmadi");
            })
            .finally(function () {
                select.disabled = false;
            });
    }

    function initMonthHeroFilters() {
        const courseSelect = document.getElementById("id_course");
        const branchSelect = document.getElementById("id_branch");
        const groupSelect = document.getElementById("id_group_name");
        const studentSelect = document.getElementById("id_student_profile");
        const periodSelect = document.getElementById("id_period");

        if (
            !courseSelect ||
            !branchSelect ||
            !groupSelect ||
            !studentSelect ||
            !periodSelect
        ) {
            return;
        }

        const baseUrl = getAdminModelBaseUrl();
        const heroId = getCurrentHeroId();

        function loadAvailableMonths(selectedValue) {
            clearSelect(periodSelect, "Oyni tanlang");

            if (!studentSelect.value) {
                periodSelect.firstElementChild.textContent = "Avval studentni tanlang";
                return;
            }

            const params = new URLSearchParams({
                student_id: studentSelect.value,
            });
            if (heroId) {
                params.set("hero_id", heroId);
            }

            loadOptions(
                `${baseUrl}get-months/?${params}`,
                periodSelect,
                "Oyni tanlang",
                selectedValue
            );
        }

        courseSelect.addEventListener("change", function () {
            clearSelect(branchSelect, "Filialni tanlang");
            clearSelect(groupSelect, "Avval filialni tanlang");
            clearSelect(studentSelect, "Avval guruhni tanlang");
            clearSelect(periodSelect, "Avval studentni tanlang");

            if (!courseSelect.value) {
                return;
            }

            const params = new URLSearchParams({course_id: courseSelect.value});
            loadOptions(
                `${baseUrl}get-branches/?${params}`,
                branchSelect,
                "Filialni tanlang"
            );
        });

        branchSelect.addEventListener("change", function () {
            clearSelect(groupSelect, "Guruhni tanlang");
            clearSelect(studentSelect, "Avval guruhni tanlang");
            clearSelect(periodSelect, "Avval studentni tanlang");

            if (!courseSelect.value || !branchSelect.value) {
                return;
            }

            const params = new URLSearchParams({
                course_id: courseSelect.value,
                branch_id: branchSelect.value,
            });
            loadOptions(
                `${baseUrl}get-groups/?${params}`,
                groupSelect,
                "Guruhni tanlang"
            );
        });

        groupSelect.addEventListener("change", function () {
            clearSelect(studentSelect, "Studentni tanlang");
            clearSelect(periodSelect, "Avval studentni tanlang");

            if (!courseSelect.value || !branchSelect.value || !groupSelect.value) {
                return;
            }

            const params = new URLSearchParams({
                course_id: courseSelect.value,
                branch_id: branchSelect.value,
                group_name: groupSelect.value,
            });
            loadOptions(
                `${baseUrl}get-students/?${params}`,
                studentSelect,
                "Studentni tanlang"
            );
        });

        studentSelect.addEventListener("change", function () {
            loadAvailableMonths("");
        });

        if (studentSelect.value) {
            loadAvailableMonths(periodSelect.value);
        } else {
            clearSelect(periodSelect, "Avval studentni tanlang");
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initMonthHeroFilters);
    } else {
        initMonthHeroFilters();
    }
})();
