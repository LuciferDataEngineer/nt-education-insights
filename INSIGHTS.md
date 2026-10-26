# What the Northern Territory school numbers actually show

Retrieved 26 October 2026. Every figure below is computed from a public table in this repository. The pipeline, the checks, and the charts are in the repo. This note is the reading of those tables.

Two measurement systems sit side by side and must not be subtracted from each other.

- **National attendance** is the Productivity Commission *Report on Government Services 2026*, Table 4A.19: all schools, Years 1–10, Semester 1. 2020 was not published.
- **Northern Territory government schools** are the Department of Education enrolment and attendance workbooks: a school, a region, or a year level, usually the whole year. 2024 year-level data is Term 4 only. 2025 school data in this release stops at Term 3.

Rates suppressed by the department (`np`, usually fewer than 12 students) are missing. They are not zeroes.

## Eight findings

**1. The attendance decline is an Aboriginal gap, and it is still falling.**
Aboriginal and Torres Strait Islander students in the NT attended **58.3%** of the time in Years 1–10 in 2025, down from **68.6%** in 2016 and **63.3%** in 2019. An ordinary least-squares line through the nine published years falls by **1.19 percentage points a year** (95% confidence interval **−1.51 to −0.87**, R² **0.92**). Non-Indigenous students in the NT attended **89.4%** in 2025. Australia’s non-Indigenous rate was **89.7%**. The NT all-student rate, **76.9%**, looks low against Australia’s **88.8%** only because Aboriginal students are about two in five of the Territory’s enrolments, not because non-Indigenous attendance is unusual.

**2. Outer regional NT looks like the rest of the country. Very remote NT does not, and remoteness is not the whole explanation.**
In 2025, Aboriginal attendance in outer regional NT was **77.1%**, against **77.0%** for outer regional Australia. Remote NT was **56.9%** (Australia **66.6%**). Very remote NT was **45.8%**, against **54.2%** for very remote Australia, **53.7%** in very remote Western Australia and **64.3%** in very remote Queensland. In the same very remote NT cells, non-Indigenous attendance was **86.4%**, against **86.9%** nationally. Students in the same remoteness band, in the same jurisdiction, are not having the same school year.

**3. Inside government schools, Darwin and the Barkly are different systems.**
Whole of 2024, NT government schools:

| Region | Aboriginal attendance | Non-Aboriginal attendance | All students |
| --- | ---: | ---: | ---: |
| Darwin | 72.4% | 86.6% | 83.9% |
| Top End | 62.1% | 84.4% | 76.5% |
| Central | 53.2% | 82.4% | 65.5% |
| Big Rivers | 47.8% | 81.0% | 56.9% |
| East Arnhem | 39.0% | 81.0% | 53.6% |
| Barkly | 40.3% | 75.8% | 44.8% |

East Arnhem and Top End are not comparable with the pre-2020 regions. Arnhem was split, and Palmerston and Rural joined West Arnhem in the new Top End. Darwin, Barkly, Central (formerly Alice Springs) and Big Rivers (formerly Katherine) kept a continuous geography. The 2024 gap does not depend on that break.

**4. At school level the gradient is steep, and it is not only an ICSEA story.**
Of 152 government schools in the 2024 whole-year file, **140** have a published attendance rate. Enrolment-weighted attendance in that panel is **72.3%**. **47** schools are under 50%. **24.5%** of enrolment in the panel sits in schools under 60%.

Enrolment-weighted correlations, 2024: attendance with Aboriginal enrolment share **−0.91**, with the share of students in the bottom parental socio-educational quarter **−0.88**, with ICSEA **+0.91**.

A weighted least-squares regression on the 128 schools with a published rate, an ICSEA-related SEA quarter, and enrolment of at least 20, outcome in percentage points, weights equal to enrolment, HC1 standard errors:

| Term | Estimate | 95% interval |
| --- | ---: | --- |
| Very remote, relative to outer regional | −12.7 pp | −20.3 to −5.0 |
| Remote, relative to outer regional | −1.1 pp | −6.3 to +4.0 |
| Aboriginal enrolment, per percentage point | −0.32 pp | −0.51 to −0.13 |
| Bottom SEA quarter, per percentage point | −0.12 pp | −0.31 to +0.07 |

R² is **0.86**. Remoteness still matters after the student-body measures, for very remote schools. The bottom SEA quarter does not have a distinguishable partial association once Aboriginal enrolment and remoteness are in the model. That is collinearity, not evidence that socio-educational advantage is irrelevant: the two measures move together (the raw SEA correlation is −0.88).

The same equation inside very remote schools only (n = 63, R² 0.65) cannot separate Aboriginal enrolment from the bottom SEA quarter. Both intervals include zero. Many of those schools sit at 95–100% Aboriginal enrolment and a very high bottom SEA share, so there is little within-band variation to estimate. The between-band pattern is clear. The within-very-remote ranking is not.

**5. A few schools sit a long way off that line. Read them as residuals, not as a league table.**
Largest negative residuals in the 2024 model, attendance minus the fitted value:

| School | Remoteness | Enrolment | Attendance | Residual |
| --- | --- | ---: | ---: | ---: |
| Top End School of Flexible Learning | Outer regional | 66 | 41.7% | −20.8 pp |
| Gunbalanya School | Remote | 234 | 35.0% | −18.4 pp |
| Ampilatwatja School | Very remote | 124 | 23.5% | −16.0 pp |
| Alekarenge School | Very remote | 78 | 23.9% | −15.7 pp |
| Shepherdson College | Very remote | 538 | 29.4% | −13.2 pp |

Largest positive residuals: Milikapiti **72.8%** (+31.8 pp, enrolment 59), Pularumpi **64.5%** (+23.3 pp, enrolment 50), both very remote and almost entirely Aboriginal. Flexible-learning provision is not the same service as a community school. Gunbalanya and Shepherdson are large enough that the residual is not a small-cell fluke. None of these gaps is a verdict on a community.

**6. NAPLAN shows the same split, and absence is large enough to change what the mean means.**
Year 3 reading, 2025, proficiency among students who sat:

| Group | Mean (margin of error) | Needs additional support | Absent | Enrolled |
| --- | --- | ---: | ---: | ---: |
| Australia, all | 402.2 (1.2) | 10.8% | 1.6% | 324,404 |
| NT, non-Indigenous | 380.7 (8.9) | 15.0% | 2.1% | 1,980 |
| Australia, Indigenous | 327.2 (2.5) | 33.9% | 6.4% | 22,514 |
| NT, all | 322.5 (15.1) | 38.2% | 12.0% | 3,371 |
| NT, Indigenous | 237.5 (11.6) | 71.7% | 26.1% | 1,366 |
| NT, Indigenous, very remote | 200.0 (11.0) | 89.6% | 38.0% | 624 |

Year 3 numeracy, NT Indigenous very remote: mean **223.7**, **94.5%** needing additional support, **40.7%** absent. Year 9 reading, NT Indigenous: mean **418.3**, **67.3%** needing support, **47.0%** absent, participation **51.8%** of 1,411 enrolled students. The mean is the mean of the students who were assessed. It is not the mean of the enrolled cohort.

On the reset NAPLAN scale, NT Indigenous Year 3 reading has not improved: **248.1** (2023), **242.8** (2024), **237.5** (2025), **241.7** (2026). The share needing additional support was **63.6%** in 2023 and **71.7%** in 2025. Pre-2023 NAPLAN means are a different scale and are not used here.

School-level NAPLAN is not in the public national results file, so this project does not correlate a school’s attendance with that school’s NAPLAN. The link is at jurisdiction and remoteness, where both collections publish.

**7. Year 12 has not moved in the NT, while it has moved in Western Australia.**
ABS capped apparent retention, Year 7/8 to Year 12, all affiliations, persons:

| Year | NT, Indigenous | NT, non-Indigenous | WA, Indigenous |
| --- | ---: | ---: | ---: |
| 2016 | 35.2% | 72.5% | 44.7% |
| 2021 | 33.2% | 75.4% | 56.3% |
| 2025 | 34.9% | 67.3% | 69.7% |

Apparent retention is not a cohort rate. Students who repeat, migrate, or change sector can push it up, which is why the Bureau caps it. The NT series is flat. The WA series is not.

Closing the Gap, census, Aboriginal and Torres Strait Islander people aged 20–24 with Year 12 or equivalent, or Certificate III or above: NT **37.5%** in 2016 and **40.2%** in 2021. Australia was **68.1%** in 2021. The national target is **96%** by 2031. The Commission’s linear estimate for the NT on that series is **45.5%**.

In NT government schools, Term 4 2024, Aboriginal attendance sits near **58%** from Transition to Year 6 and near **50%** in Years 8–11. Aboriginal enrolment is **923** in Year 10 and **366** in Year 12. Non-Aboriginal enrolment is **1,037** in Year 10 and **865** in Year 12. The Year 12 Aboriginal attendance rate (62%) is higher than Year 10. The group is much smaller. That is selection, not a recovery.

**8. The Territory already spends more per student and has fewer students per teacher. The gap has not closed.**
ABS full-time-equivalent students: NT **41,069** in 2016 and **39,866** in 2025. Indigenous FTE fell from **16,470** to **15,502**. The Indigenous share moved from **40.1%** to **38.9%**. Across the states and territories combined, the 2025 Indigenous share is **6.8%**.

Government student-to-teacher ratio, 2025: NT **10.7**, Australia **13.0**.

RoGS government recurrent expenditure per FTE student, 2023–24: NT **$32,223**, Australia **$26,140**. The Australian Government component is **$8,787** in the NT and **$4,277** nationally. ACARA’s 2025 NT profile, enrolment-weighted, puts ICSEA at **903** (the index is centred on 1,000), the bottom SEA quarter at **42%** of students, government schools at **72%** of enrolments, and Remote or Very Remote schools at **39%** of enrolments, of which Very Remote is **19%**.

Lower ratios and higher recurrent funding are real. They have not produced a national attendance rate, a national proficiency distribution, or a Closing the Gap trajectory.

## How to read the regression

The school model is descriptive. Schools are not a random sample of students. Enrolment weights stop a school of 30 from counting as a school of 600, and they do not create student-level standard errors. HC1 intervals allow uneven residual variance. They do not fix the fact that Aboriginal enrolment, the bottom SEA quarter, ICSEA and remoteness are entangled. ICSEA itself is built from socio-educational measures, so putting ICSEA and the bottom SEA quarter in one equation would be double counting. The specification uses remoteness, Aboriginal enrolment share, and the bottom SEA quarter.

No coefficient here is an effect of a policy, a community, or a teacher. Changing the Aboriginal share of a school is not an intervention the model identifies.

## Charts

Static copies of the main comparisons:

- `reports/figures/01_attendance_trend.png`
- `reports/figures/02_remoteness_indigenous.png`
- `reports/figures/03_nt_regions_2024.png`
- `reports/figures/04_school_scatter_2024.png`
- `reports/figures/05_naplan_year3_reading_2025.png`
- `reports/figures/06_apparent_retention_2025.png`

The interactive versions are the Streamlit app and `dashboard/dist/index.html`.

## What would change the conclusion

A school-level NAPLAN file, with absence modelled rather than dropped, would test whether the schools that attend less are the schools that score less, or whether absence is doing the work. A true cohort from Year 7 to Year 12 would replace apparent retention. Community-controlled data, on definitions the communities set, would be a different project from this restatement of government releases.
