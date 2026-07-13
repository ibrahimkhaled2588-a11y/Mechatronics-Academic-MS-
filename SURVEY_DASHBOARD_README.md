# Survey Dashboard Page

This project now includes a new web page for survey analysis:

- URL: `/survey-dashboard.html`
- Backend API: `/api/survey/dashboard`
- Template download: `/api/survey/template`

## Required Excel Format

- File type: `.xlsx`
- Each file = one survey group (students / graduates / employers)
- Each column = one question
- Each cell must contain one of:
  - `موافق تماماً`
  - `موافق`
  - `محايد`
  - `غير موافق`
  - `غير موافق تماماً`

Example columns:

- `Q1 جودة المقررات`
- `Q2 كفاءة أعضاء هيئة التدريس`
- `Q3 خدمات المعامل`

## What the page generates

- High-resolution dashboard image (`.png`) for each uploaded survey file
- PowerPoint report (`.pptx`) with each survey in a separate slide
- ZIP bundle containing all outputs

## Run Instructions

1. Install dependencies:
   - `pip install -r backend/requirements.txt`
2. Start backend:
   - `python backend/app.py`
3. Open app in browser:
   - `http://127.0.0.1:3500/`
4. From home page, open **Survey Dashboard Page**
5. Upload `.xlsx` files and click **Generate Dashboard Package**

## Notes

- Charts use fixed colors:
  - Dark Blue: `موافق تماماً`
  - Orange: `موافق`
  - Gray: `محايد`
  - Yellow: `غير موافق`
  - Light Blue: `غير موافق تماماً`
- Arabic shaping is handled with a best-effort fallback for environments without extra Arabic-rendering packages.
