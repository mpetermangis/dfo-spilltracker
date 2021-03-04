select count(*) from spill_reports sr;

select * from spill_reports sr 	where report_num ='2019-0612';

select count(*) from spill_reports sr ;

create table report_map_tbl as select * from report_map_view rmv ;

CREATE INDEX idx_geom_report_map
    ON report_map_tbl
    USING GIST (geometry);
   
   
SELECT *
FROM   report_map_tbl
WHERE  geometry 
    -- && -- intersects,  gets more rows  -- CHOOSE ONLY THE
    @ -- contained by, gets fewer rows -- ONE YOU NEED!
    ST_MakeEnvelope (
        -123.098, 49.0, -- bounding 
        -123.0, 49.141, -- box limits
        4326);

alter table report_map_tbl owner to spilluser;    
alter index idx_geom_report_map owner to spilluser;
