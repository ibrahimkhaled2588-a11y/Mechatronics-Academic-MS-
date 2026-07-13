# TODO - Course normalization & smart matching layer

- [x] Inspect repo upload pipeline (academic_analytics + returned `academic_analytics` payload)
- [x] Add `backend/course_matching.py` with normalization + similarity scoring + confidence thresholds
- [x] Inject matching/merge preprocessing into `backend/app.py` right after `academic = {...}` creation and before response
- [x] Ensure code compiles (AST parse)
- [ ] Run the FastAPI server and upload the Excel files to verify merged course counts + UI rendering
- [ ] If needed, adjust thresholds or ignore-word lists based on observed mis-merges

