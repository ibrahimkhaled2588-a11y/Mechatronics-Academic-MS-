# TODO - Course normalization & smart matching layer

- [x] Inspect repo upload pipeline (academic_analytics + returned `academic_analytics` payload)
- [x] Add `backend/course_matching.py` with normalization + similarity scoring + confidence thresholds
- [x] Inject matching/merge preprocessing into `backend/app.py` right after `academic = {...}` creation and before response
- [x] Ensure code compiles (AST parse)
- [x] Run the FastAPI server and upload the Excel files to verify merged course counts + UI rendering
      (2026-07-13: uploaded `إحصائية تقديرات المواد حديثة.xlsx` against `/upload-excel`;
      raw sheet's 55 course rows map 1:1 to 55 entries in `academic_analytics.all_courses`
      with no mis-merges or leftover duplicates.)
- [ ] If needed, adjust thresholds or ignore-word lists based on observed mis-merges (none observed so far)

