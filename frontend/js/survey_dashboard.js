const surveyFilesInput = document.getElementById("surveyFiles");
const generateSurveyBtn = document.getElementById("generateSurveyBtn");
const surveyStatus = document.getElementById("surveyStatus");
const surveyResult = document.getElementById("surveyResult");
const surveyLinks = document.getElementById("surveyLinks");
const surveyZone = document.getElementById("survey-upload-zone");
const surveyFilesName = document.getElementById("surveyFilesName");

function updateSurveyZoneLabel(files) {
    if (!surveyFilesName) return;
    if (!files || files.length === 0) {
        surveyFilesName.textContent = '';
        if (surveyZone) surveyZone.classList.remove('has-file');
        return;
    }
    surveyFilesName.textContent = files.length === 1
        ? files[0].name
        : `${files.length} files selected`;
    if (surveyZone) surveyZone.classList.add('has-file');
}

if (surveyFilesInput) {
    surveyFilesInput.addEventListener('change', () => {
        updateSurveyZoneLabel(Array.from(surveyFilesInput.files || []));
    });
}

if (surveyZone) {
    surveyZone.addEventListener('dragover', (e) => { e.preventDefault(); surveyZone.classList.add('drag-over'); });
    surveyZone.addEventListener('dragleave', () => surveyZone.classList.remove('drag-over'));
    surveyZone.addEventListener('drop', (e) => {
        e.preventDefault();
        surveyZone.classList.remove('drag-over');
        const droppedFiles = e.dataTransfer?.files;
        if (droppedFiles && droppedFiles.length > 0 && surveyFilesInput) {
            const dt = new DataTransfer();
            Array.from(droppedFiles).forEach((f) => dt.items.add(f));
            surveyFilesInput.files = dt.files;
            updateSurveyZoneLabel(Array.from(droppedFiles));
        }
    });
}

async function generateSurveyDashboard() {
    const files = surveyFilesInput?.files;
    if (!files || files.length === 0) {
        surveyStatus.textContent = "Please select at least one .xlsx file.";
        surveyStatus.classList.add("error");
        return;
    }

    surveyStatus.textContent = "Generating dashboards and PowerPoint...";
    surveyStatus.classList.remove("error");
    surveyResult.hidden = true;
    generateSurveyBtn.disabled = true;

    const formData = new FormData();
    Array.from(files).forEach((file) => formData.append("files", file));

    try {
        const response = await fetch("/api/survey/dashboard", {
            method: "POST",
            body: formData,
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || "Survey dashboard generation failed.");
        }
        const data = await response.json();

        surveyLinks.innerHTML = "";
        const zipLink = document.createElement("a");
        zipLink.href = data.zip_url;
        zipLink.textContent = "Download All Outputs (ZIP)";
        zipLink.className = "btn-ghost";
        zipLink.target = "_blank";
        surveyLinks.appendChild(zipLink);

        const pptLink = document.createElement("a");
        pptLink.href = data.pptx_url;
        pptLink.textContent = "Download PowerPoint (.pptx)";
        pptLink.className = "btn-ghost";
        pptLink.target = "_blank";
        surveyLinks.appendChild(pptLink);

        (data.dashboard_images || []).forEach((url, idx) => {
            const imageLink = document.createElement("a");
            imageLink.href = url;
            imageLink.textContent = `Download Survey ${idx + 1} Dashboard (.png)`;
            imageLink.className = "btn-ghost";
            imageLink.target = "_blank";
            surveyLinks.appendChild(imageLink);
        });

        surveyStatus.textContent = `Done. Processed ${data.surveys_processed} survey file(s).`;
        surveyResult.hidden = false;
    } catch (error) {
        surveyStatus.textContent = error.message || "Unexpected error occurred.";
        surveyStatus.classList.add("error");
    } finally {
        generateSurveyBtn.disabled = false;
    }
}

if (generateSurveyBtn) {
    generateSurveyBtn.addEventListener("click", generateSurveyDashboard);
}
