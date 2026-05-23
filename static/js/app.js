async function jsonFetch(url, options = {}) {
    const headers = options.body instanceof FormData ? {} : { "Content-Type": "application/json" };
    const response = await fetch(url, {
        headers,
        ...options,
    });
    const data = await response.json();
    if (!response.ok || data.ok === false) {
        throw new Error(data.message || "Request failed");
    }
    return data;
}

function el(id) {
    return document.getElementById(id);
}

function textFor(key, fallback) {
    return (window.APP_TEXTS && window.APP_TEXTS[key]) || fallback;
}

function toggleSidebar(forceOpen) {
    const shouldOpen = typeof forceOpen === "boolean" ? forceOpen : !document.body.classList.contains("sidebar-open");
    document.body.classList.toggle("sidebar-open", shouldOpen);
}

function detectBrowserLanguage() {
    const browserLang = navigator.language || navigator.userLanguage || "en";
    if (browserLang.toLowerCase().startsWith("ru")) return "ru";
    if (browserLang.toLowerCase().startsWith("kk") || browserLang.toLowerCase().startsWith("kz")) return "kz";
    return "en";
}

function syncAutoLanguage() {
    const storageKey = "preferred_language";
    const storedLanguage = window.localStorage.getItem(storageKey);
    const detectedLanguage = storedLanguage || detectBrowserLanguage();
    window.localStorage.setItem(storageKey, detectedLanguage);
    if (window.APP_LANG !== detectedLanguage && window.APP_SET_LANGUAGE_TEMPLATE) {
        const nextUrl = `${window.location.pathname}${window.location.search}`;
        const target = window.APP_SET_LANGUAGE_TEMPLATE.replace("__LANG__", detectedLanguage);
        window.location.replace(`${target}?next=${encodeURIComponent(nextUrl)}`);
        return true;
    }
    return false;
}

async function refreshFiles(moduleId) {
    const list = document.querySelector(`#fileList[data-module-id="${moduleId}"]`);
    if (!list) return;
    const data = await jsonFetch(`/api/module/${moduleId}/lab/files`);
    list.innerHTML = "";
    if (!data.files.length) {
        list.innerHTML = `<div class="file-item"><span>${textFor("no_files", "No files uploaded yet")}</span></div>`;
        return;
    }
    data.files.forEach((file) => {
        const item = document.createElement("div");
        item.className = "file-item";
        item.innerHTML = `
            <span>${file.name} (${file.size} bytes)</span>
            <a class="primary-btn" href="${file.download_url}">${textFor("download", "Download")}</a>
        `;
        list.appendChild(item);
    });
}

function renderArtifacts(artifacts) {
    const gallery = el("artifactGallery");
    if (!gallery) return;
    gallery.innerHTML = "";
    artifacts.forEach((artifact) => {
        const wrapper = document.createElement("a");
        wrapper.href = artifact.url;
        wrapper.target = "_blank";
        wrapper.rel = "noreferrer";
        wrapper.innerHTML = `<img src="${artifact.url}" alt="${artifact.name}">`;
        gallery.appendChild(wrapper);
    });
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

async function loadTest(moduleId) {
    const container = el("testContainer");
    const data = await jsonFetch(`/api/module/${moduleId}/test`);
    container.innerHTML = "";
    data.questions.forEach((question, index) => {
        const block = document.createElement("div");
        block.className = "test-question";
        const optionsHtml = question.options.map((option) => `
            <label class="test-option">
                <input type="radio" name="test_${question.id}" value="${option}">
                <span>${escapeHtml(option)}</span>
            </label>
        `).join("");
        block.innerHTML = `<strong class="question-title">${index + 1}. ${escapeHtml(question.question)}</strong><div class="radio-group">${optionsHtml}</div>`;
        container.appendChild(block);
    });
    const button = document.createElement("button");
    button.className = "primary-btn";
    button.type = "button";
    button.textContent = textFor("submit_test", "Submit test");
    button.onclick = async () => {
        const answers = {};
        data.questions.forEach((question) => {
            const selected = document.querySelector(`input[name="test_${question.id}"]:checked`);
            if (selected) answers[String(question.id)] = selected.value;
        });
        try {
            const result = await jsonFetch(`/api/module/${moduleId}/test/submit`, {
                method: "POST",
                body: JSON.stringify({ answers }),
            });
            const feedback = document.createElement("div");
            feedback.className = "feedback-box";
            feedback.innerHTML = `${textFor("score_label", "Score")}: ${result.score}/${result.total}<br>${
                result.passed ? textFor("passed_message", "Passed. Practice unlocked.") : textFor("failed_message", "Not passed. Review the explanations below.")
            }`;
            container.appendChild(feedback);
            if (!result.passed && result.feedback.length) {
                result.feedback.forEach((item) => {
                    const f = document.createElement("div");
                    f.className = "feedback-box";
                    f.innerHTML = `<strong>${escapeHtml(item.question)}</strong><br>Correct: ${escapeHtml(item.correct_answer)}<br>${escapeHtml(item.explanation)}`;
                    container.appendChild(f);
                });
            } else if (result.passed) {
                window.location.reload();
            }
        } catch (error) {
            alert(error.message);
        }
    };
    container.appendChild(button);
}

document.addEventListener("DOMContentLoaded", () => {
    if (syncAutoLanguage()) {
        return;
    }

    const sidebarToggle = document.querySelector("[data-sidebar-toggle]");
    const sidebarClose = document.querySelector("[data-sidebar-close]");
    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", () => toggleSidebar());
    }
    if (sidebarClose) {
        sidebarClose.addEventListener("click", () => toggleSidebar(false));
    }

    const completeTheoryBtn = el("completeTheoryBtn");
    if (completeTheoryBtn) {
        completeTheoryBtn.addEventListener("click", async () => {
            try {
                await jsonFetch(`/module/${completeTheoryBtn.dataset.moduleId}/theory/complete`, { method: "POST" });
                window.location.reload();
            } catch (error) {
                alert(error.message);
            }
        });
    }

    const loadTestBtn = el("loadTestBtn");
    if (loadTestBtn) {
        loadTestBtn.addEventListener("click", () => loadTest(loadTestBtn.dataset.moduleId));
    }

    const practiceBtn = el("practiceBtn");
    if (practiceBtn) {
        practiceBtn.addEventListener("click", async () => {
            try {
                const data = await jsonFetch(`/api/module/${practiceBtn.dataset.moduleId}/practice/submit`, {
                    method: "POST",
                    body: JSON.stringify({ submission: el("practiceText").value }),
                });
                el("practiceFeedback").textContent = `${data.feedback} ${textFor("score_label", "Score")}: ${data.score}`;
                window.setTimeout(() => window.location.reload(), 900);
            } catch (error) {
                alert(error.message);
            }
        });
    }

    const homeworkBtn = el("homeworkBtn");
    if (homeworkBtn) {
        homeworkBtn.addEventListener("click", async () => {
            try {
                const data = await jsonFetch(`/api/module/${homeworkBtn.dataset.moduleId}/homework/submit`, {
                    method: "POST",
                    body: JSON.stringify({ submission: "" }),
                });
                el("homeworkFeedback").textContent = `${data.feedback} ${textFor("score_label", "Score")}: ${data.score}`;
                window.setTimeout(() => window.location.reload(), 900);
            } catch (error) {
                alert(error.message);
            }
        });
    }

    const runCodeBtn = el("runCodeBtn");
    if (runCodeBtn) {
        refreshFiles(runCodeBtn.dataset.moduleId);
        runCodeBtn.addEventListener("click", async () => {
            el("codeOutput").textContent = "Running...";
            el("codeError").textContent = "";
            try {
                const data = await jsonFetch(`/api/module/${runCodeBtn.dataset.moduleId}/lab/run`, {
                    method: "POST",
                    body: JSON.stringify({
                        code: el("codeEditor").value,
                        stdin: el("stdinInput") ? el("stdinInput").value : "",
                    }),
                });
                el("codeOutput").textContent = data.stdout || `[${data.status}] No stdout`;
                el("codeError").textContent = data.stderr || "";
                renderArtifacts(data.artifacts || []);
                refreshFiles(runCodeBtn.dataset.moduleId);
            } catch (error) {
                el("codeOutput").textContent = "";
                el("codeError").textContent = error.message;
            }
        });
    }

    const uploadForm = el("uploadForm");
    if (uploadForm) {
        uploadForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const fileInput = el("labFileInput");
            if (!fileInput.files.length) {
                alert(textFor("choose_file_first", "Choose a file first."));
                return;
            }
            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            try {
                await jsonFetch(`/api/module/${uploadForm.dataset.moduleId}/lab/upload`, {
                    method: "POST",
                    body: formData,
                });
                fileInput.value = "";
                refreshFiles(uploadForm.dataset.moduleId);
            } catch (error) {
                alert(error.message);
            }
        });
    }

    const tutorBtn = el("tutorBtn");
    if (tutorBtn) {
        tutorBtn.addEventListener("click", async () => {
            try {
                const data = await jsonFetch(`/api/module/${tutorBtn.dataset.moduleId}/tutor`, {
                    method: "POST",
                    body: JSON.stringify({ question: el("tutorQuestion").value }),
                });
                el("tutorAnswer").textContent = data.answer;
            } catch (error) {
                alert(error.message);
            }
        });
    }
});
