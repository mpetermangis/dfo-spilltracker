    SELECT DISTINCT ON (report_num) * FROM public.spill_reports
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ORDER BY report_num, last_updated DESC
;


DROP VIEW IF EXISTS report_map_view;
CREATE VIEW report_map_view AS
SELECT DISTINCT ON (report_num) ST_SetSRID( ST_Point( longitude, latitude), 4326) AS geometry,
* FROM public.spill_reports
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
ORDER BY report_num, last_updated DESC;

CREATE VIEW report_map2 AS
SELECT DISTINCT ON (report_num) ST_SetSRID( ST_MakePoint( longitude, latitude), 4326) AS geometry,
* FROM public.spill_reports
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
ORDER BY report_num, last_updated DESC;


SELECT ST_SetSRID( ST_Point( longitude, latitude), 4326) AS geom geometry(POINT, 4326), * FROM public.spill_reports
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
