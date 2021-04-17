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
        4326)
order by last_updated desc;

alter table report_map_tbl owner to spilluser;    
alter index idx_geom_report_map owner to spilluser;

UPDATE spill_reports SET report_date = spill_date WHERE recorded_by='CCG Legacy';

UPDATE spill_reports SET report_date = spill_date WHERE report_date is null;

select * from report_map_view rmv where report_num='2019-1042';  --2019-1010

select * from report_map_view rmv where report_num='2019-1010';

--delete from report_map_tbl where report_num='2019-1042';

select * from report_map_tbl where report_num='2019-1042';

insert into report_map_tbl select * from report_map_view rmv where report_num='2019-1042';

select distinct(er_region) from spill_reports;

select * from spill_reports sr where report_num ='2019-1010';

--delete from public.user where id=3;

select * from spill_reports sr where report_num='2019-1042';

insert into public.user_roles (user_id, role_id) values (2, 1);

--delete from public.user_roles;
