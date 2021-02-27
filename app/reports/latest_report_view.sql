SELECT DISTINCT ON (report_num) * FROM public.spill_reports 
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
ORDER BY report_num, last_updated DESC
;