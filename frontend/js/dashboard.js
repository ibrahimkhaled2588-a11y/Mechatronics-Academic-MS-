const startBtn = document.getElementById('startBtn');
if (startBtn) {
    startBtn.addEventListener('click', () => {
        window.location.href = 'dashboard.html';
    });
}

const coursePageBtn = document.getElementById('coursePageBtn');
if (coursePageBtn) {
    coursePageBtn.addEventListener('click', () => {
        window.location.href = 'course-report.html';
    });
}

const programPageBtn = document.getElementById('programPageBtn');
if (programPageBtn) {
    programPageBtn.addEventListener('click', () => {
        window.location.href = 'program-report.html';
    });
}

const surveyPageBtn = document.getElementById('surveyPageBtn');
if (surveyPageBtn) {
    surveyPageBtn.addEventListener('click', () => {
        window.location.href = 'survey-dashboard.html';
    });
}

// translation toggle for index page
const indexTranslateBtn = document.getElementById('translateBtn');
if (indexTranslateBtn) {
    indexTranslateBtn.addEventListener('click', () => {
        const btn = indexTranslateBtn;
        if (btn.innerText === 'العربية') {
            document.getElementById('startBtn').innerText = 'ابدأ التحليل';
            const tag = document.getElementById('tagline');
            if (tag) tag.textContent = 'برنامج هندسة الميكاترونكس – كلية الهندسة – جامعة المنوفية';
            const desc = document.getElementById('taglineDesc');
            if (desc) desc.textContent = 'تحليلات جودة البيانات والأداء الأكاديمي للمقررات والدرجات';
            btn.innerText = 'English';
        } else {
            document.getElementById('startBtn').innerText = 'Start Analysis';
            const tag = document.getElementById('tagline');
            if (tag) tag.textContent = 'Mechatronics Engineering Program – Faculty of Engineering – Menoufia University';
            const desc = document.getElementById('taglineDesc');
            if (desc) desc.textContent = 'Data quality and academic performance analytics for courses and grades';
            btn.innerText = 'العربية';
        }
    });
}
