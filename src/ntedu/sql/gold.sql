-- Gold marts. Silver tables are registered as views before this script runs.
-- Rates are proportions (0–1) unless the column name ends in _pct (0–100).

CREATE OR REPLACE TABLE school_year AS
SELECT
    s.calendar_year,
    s.period,
    s.series_role,
    s.school_name,
    s.acara_id,
    s.acara_school_name,
    s.match_method,
    s.match_score,
    s.enrolment,
    s.attendance_rate,
    s.suppressed,
    s.name_markers,
    s.suburb,
    s.acara_sector,
    s.school_type,
    s.geolocation,
    s.icsea,
    s.icsea_percentile,
    s.bottom_sea_pct,
    s.top_sea_pct,
    s.indigenous_pct,
    s.lbote_pct,
    s.teaching_staff_fte,
    s.acara_enrolments,
    l.latitude,
    l.longitude,
    l.abs_remoteness,
    l.lga_name,
    l.sa2_name,
    l.sa3_name,
    CASE
        WHEN s.attendance_rate IS NULL THEN NULL
        WHEN s.attendance_rate < 0.50 THEN 'Under 50%'
        WHEN s.attendance_rate < 0.70 THEN '50 to under 70%'
        WHEN s.attendance_rate < 0.80 THEN '70 to under 80%'
        WHEN s.attendance_rate < 0.90 THEN '80 to under 90%'
        ELSE '90% or higher'
    END AS attendance_band
FROM nt_school_matched s
LEFT JOIN acara_location l ON s.acara_id = l.acara_id;

CREATE OR REPLACE TABLE nt_region_year AS
SELECT
    calendar_year,
    period,
    region_harmonised AS region,
    section AS region_published,
    population,
    enrolment,
    attendance_rate,
    CASE
        WHEN region_harmonised IN ('East Arnhem', 'Top End') AND calendar_year < 2020 THEN FALSE
        ELSE TRUE
    END AS comparable_with_2020_boundaries
FROM nt_group_attendance
WHERE grain = 'region'
  AND row_kind = 'total'
  AND region_harmonised IS NOT NULL
  AND population IN ('indigenous', 'non_indigenous', 'total');

CREATE OR REPLACE TABLE nt_remoteness_year AS
SELECT
    calendar_year,
    period,
    remoteness,
    region_harmonised AS region,
    row_label,
    row_kind,
    population,
    enrolment,
    attendance_rate
FROM nt_group_attendance
WHERE grain = 'remoteness'
  AND remoteness IS NOT NULL
  AND population IN ('indigenous', 'non_indigenous', 'total');

CREATE OR REPLACE TABLE nt_yearlevel_year AS
SELECT
    calendar_year,
    period,
    stage,
    band,
    row_label AS year_level,
    row_kind,
    population,
    enrolment,
    attendance_rate
FROM nt_group_attendance
WHERE grain = 'year_level';

CREATE OR REPLACE TABLE jurisdiction_attendance AS
SELECT *
FROM rogs_attendance
WHERE year_span IN ('Years 1-6', 'Years 7-10', 'Years 1-10', 'Year 7', 'Year 10');

CREATE OR REPLACE TABLE naplan_focus AS
SELECT *
FROM naplan_results
WHERE subgroup IN (
    'All',
    'Indigenous',
    'Non-Indigenous',
    'Major cities',
    'Inner regional',
    'Outer regional',
    'Remote',
    'Very remote',
    'Indigenous major cities',
    'Indigenous inner regional',
    'Indigenous outer regional',
    'Indigenous remote',
    'Indigenous very remote',
    'Non-Indigenous major cities',
    'Non-Indigenous inner regional',
    'Non-Indigenous outer regional',
    'Non-Indigenous remote',
    'Non-Indigenous very remote',
    'Parental education: bachelor',
    'Parental education: Year 11'
);
