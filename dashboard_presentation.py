# PRESENTATION MODE — reads from local parquet files, no Snowflake connection
# Run with: streamlit run dashboard_presentation.py

import streamlit as st
import pandas as pd
import os
from datetime import date, timedelta
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

st.set_page_config(page_title="Frontline Health Dashboard", layout="wide")

DATA_DIR = os.path.join(os.path.dirname(__file__), "presentation_data")


SNAPSHOT_SQL = """
with  



sizes as (

select distinct 

size

,MAKE

,MODEL

from  REPLICATED.BUY.DBO_TBLMMRVEHICLEDESCRIPTION  mmr

LEFT JOIN inventory.vehicle.stock s

    On s.MMR_MID = TRY_TO_NUMBER(mmr.mmr_mid)

left join INVENTORY.BUY.FACTVEHICLE v

    on s.stocknumber=v.stocknumber

),





STOCKS AS (

SELECT

    SDD.WEEK_ENDING_SUNDAY AS ACQUISITION_WEEK

    , ST.ACQUISITIONDATE

    , ST.STOCKNUMBER

    , SG.SIZE_GROUPS_EURO AS SIZEGROUP

   ,st.classmake

    ,st.classmodel

    ,siz.size

    , KG.KBB_GROUP

    ,mmr.commonmodel

FROM INVENTORY.VEHICLE.STOCK ST



LEFT JOIN SHARED.DIMENSION.DATE SDD

ON SDD.CALENDAR_DATE = ST.ACQUISITIONDATE



LEFT JOIN INVENTORY.BUY.FACTVEHICLE FV

ON FV.STOCKNUMBER = ST.STOCKNUMBER



LEFT JOIN INVENTORY.BUY.VEHICLE BV

ON FV.BUYONIC_BUY_AUCTION_VEHICLE_ID = BV.BUYAUCTIONVEHICLEID



LEFT JOIN REPLICATED.BUY.DBO_TBLMMRVEHICLEDESCRIPTION  mmr 

ON ST.MMR_MID=MMR.MMR_MID



left join sizes siz

    on st.classmake=siz.make

    and st.classmodel=siz.model



LEFT JOIN RISK_SANDBOX.OROCKWOOD.SIZE_GROUPS SG

    ON coalesce(UPPER(REGEXP_REPLACE(BV.SIZE,'SALMON ','')),MMR.size,siz.size) = SG.Size



LEFT JOIN Inventory_Sandbox.Public.Incremental_BuyBox BB

        ON ST.StockNumber = BB.StockNumber



LEFT JOIN INVENTORY_SANDBOX.PI7CALC_REFERENCE.STATES_SUPER_REGIONS_REF STATE

    ON BV.PICKUPLOCATIONSTATE = STATE.STATE

LEFT JOIN INVENTORY_SANDBOX.PI7CALC_REFERENCE.SUPER_REGIONS SR

    ON STATE.SUPER_REGION_ID = SR.SUPER_REGION_ID



LEFT JOIN INVENTORY_SANDBOX.STETSON_SANDBOX.KBB_GROUPS KG

    ON ifnull(BV.KBBVALUE,fv.kbb_value) BETWEEN KG.KBB_MIN AND KG.KBB_MAX

    where ST.STOCKNUMBER NOT ILIKE '2%%'

),







adpfinal as (

SELECT distinct

    S.*

    ,CASE WHEN sizegroup IN (

        'COMPACT'

        ,'LARGE'

        ,'MEDIUM'

        ) THEN 'CAR'

    WHEN sizegroup IN (

        'EURO'

        ,'SPECIALTY'

        ,'SPORTS'

        ) THEN 'SPECIALTY'

    WHEN sizegroup IN (

        'CROSSOVER'

        ,'LARGE SUV'

        ,'MEDIUM SUV'

        ,'SMALL SUV'

         ,'VAN'

        ) THEN 'SUV'

     WHEN sizegroup IN (

         'LARGE TRUCK'

         ,'SMALL TRUCK'

        ) THEN 'TRUCK'  

    ELSE 'UNKNOWN' END AS SIZEGROUP2

    

    ,case when sizegroup2 = 'SUV' and   sizegroup='MEDIUM SUV' and   KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K','14K-16K') then 'SUV-MediumSUVSize-0K-16K KBB'

  when sizegroup2 = 'SUV' and (  sizegroup= 'SMALL SUV' or   sizegroup = 'CROSSOVER') and   KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K') then 'SUV-SmallSUVSize-0K-14K KBB'

    when sizegroup2 = 'SUV' and (  sizegroup= 'SMALL SUV' or   sizegroup = 'CROSSOVER') and   kbb_group in ('14K-16K','16K-18K','18K-20K','20K-22K','22K-99K')  then 'SUV-SmallSUVSize-14K-99K KBB'

    when sizegroup2= 'SUV' and   sizegroup= 'MEDIUM SUV'  and   KBB_group in ('16K-18K','18K-20K','20K-22K') then 'SUV-MediumSUVSize-16K-22K KBB'

    when sizegroup2= 'SUV' and   sizegroup= 'MEDIUM SUV'  and   KBB_group in ('22K-99K') then 'SUV-MediumSUVSize-22K-99K KBB'

     when sizegroup2= 'SUV' and   sizegroup= 'MEDIUM SUV'  and   KBB_group is null then 'SUV-MediumSUVSize-22K-99K KBB'

    when (sizegroup2= 'CAR' and   sizegroup= 'MEDIUM' OR   sizegroup = 'EURO' OR   SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN') and   KBB_group in ('12K-14K','14K-16K','16K-18K') then 'CAR-AnySize-12K-18K KBB'

     when (sizegroup2= 'CAR' and   sizegroup= 'MEDIUM' OR   sizegroup = 'EURO' OR   SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN')  and   KBB_group in ('18K-20K') then 'CAR-AnySize-18K-20K KBB'

     when (sizegroup2= 'CAR' and   sizegroup= 'MEDIUM' OR   sizegroup = 'EURO' OR   SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN')  and   KBB_group in ('20K-22K','22K-99K') then 'CAR-AnySize-20K-99K KBB'

     when (sizegroup2= 'CAR' OR  SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and   KBB_group in ('0K-8K','8K-10K','10K-12K') then 'CAR-AnySize-0K-12K KBB'

      when (sizegroup2= 'CAR' OR  SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and   KBB_group in ('12K-14K','14K-16K','16K-18K') then 'CAR-AnySize-12K-18K KBB'

       when (sizegroup2= 'CAR' OR  SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and   KBB_group in ('20K-22K','22K-99K') then 'CAR-AnySize-20K-99K KBB'

           when (sizegroup2= 'CAR' OR  SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and   KBB_group in ('18K-20K') then 'CAR-AnySize-18K-20K KBB'

     when (sizegroup2= 'SUV' or   sizegroup='VAN' or   sizegroup='LARGE SUV') then 'SUV-LargeSUV-0K-99K KBB'

     when sizegroup2= 'TRUCK' then 'TRUCK-TruckSize-0K-99K KBB'

     when sizegroup2= 'SUV' and   KBB_group is null then'SUV-LargeSUV-0K-99K KBB'

     WHEN  sizegroup2= 'CAR' AND   KBB_GROUP IS NULL THEN 'CAR-AnySize-20K-99K KBB'

     when   sizegroup = 'VAN' AND   KBB_GROUP IS NULL THEN 'SUV-LargeSUV-0K-99K KBB'

     WHEN   SIZEGROUP='COMPACT' AND   KBB_GROUP IS NULL THEN 'CAR-AnySize-20K-99K KBB'

     WHEN SIZEGROUP2= 'UNKNOWN' THEN 'CAR-AnySize-20K-99K KBB'

     when sizegroup2='SPECIALTY' and   kbb_group is null then 'CAR-AnySize-20K-99K KBB'

     end as DistroGroups

     ,row_number() over (partition by STOCKNUMBER order by ACQUISITIONDATE desc) as rownumber

FROM STOCKS S

where acquisition_week >= '2025-01-01'

),



distrogroups as (

select distinct distrogroups

from adpfinal

),



classmodel as (

select distinct classmodel

from  adpfinal



),



layaways as (

select distinct asofdate,st.stocknumber,ccd.childcostcenterdesc,ccd.parentcostcenterdesc,classmake,classmodel,distrogroups, ifnull(mm.commonmodel,mm2.commonmodel) as commonmodel,sourcingregion

from INVENTORY.VEHICLE.STOCKTREND st

left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

on st.currentcostcenterid=childcostcenterid

left join INVENTORY.TITLE.INFO_AVAILABILITY_TREND t

    on st.stocknumber=t.stock_number

    and st.asofdate= upload_date

left join adpfinal a

    on st.stocknumber=a.stocknumber

left join 

(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm

where iscurrent=1) mm

   on COALESCE(upper(a.commonmodel),UPPER(SPLIT_PART(A.CLASSMODEL, ' ', 1)),CONCAT('OTHER_',sizegroup))=upper(mm.commonmodel)

  AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

    when MM.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

    upper(MM.crlld) end=upper(ccd.parentcostcenterdesc)

left join 

(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm

where iscurrent=1) mm2

   on CONCAT('OTHER_',case when sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE SIZEGROUP END)=upper(mm2.commonmodel)

  AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

    when MM2.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

    upper(MM2.crlld) end=upper(ccd.parentcostcenterdesc)

where in_process_desc in ('Dealer','Holding Lot','Lot Repair')

and title_distro_ready='Unavailable' 

and title_location <> 'Dealership-Shipped'

and status_code= 'LA'

and ccd.program='DT'

and ccd.in_process_desc ilike 'Dealer'

--and asofdate = '{target_date}'

),



website_stock as (

SELECT 

distinct fv.stock_number as website_stocks

,upper(trim(ccd.PARENTCOSTCENTERDESC)) as ParentCostCenterDesc 

,stat

, TO_DATE(E.event_date_time) as AsOfDate



from risk.affordability.ga2_pos_affordability E

LEFT JOIN risk.affordability.ga2_pos_affordability_financed_vehicle FV

ON E.business_event_id = FV.business_event_id

left join INVENTORY.VEHICLE.STOCKTODAYACTIVE st on st.stknbr= fv.stock_number

--left join inventory.vehicle.stock st on st.stocknumber= fv.stock_number

left join inventory_sandbox.admdev.dbo_tblccdmapping ccd on ccd.crllt= st.clot

--;select *from inventory.vehicle.stock limit 10;st;

--left join inventory_sandbox.admdev.dbo_tblccdmapping ccd on ccd.crllt= st.currentlot

--where stocknumber = 1660043728 ;

-- WHERE --TO_DATE(E.event_date_time) > '2024-01-01' 

-- --and TO_DATE(E.event_date_time) < to_date(Getdate())

-- to_date(e.event_date_time) = current_date--'2026-01-12'

and E.event_name = 'ga2Affordability'

AND FV.stock_number NOT LIKE '2%%'

and stat= 'AV'

--and in_process_desc ='Dealer'

--and fv.stock_number=1010200734



union all



SELECT 

distinct fv.stock_number as website_stocks

,upper(trim(ccd.PARENTCOSTCENTERDESC)) as ParentCostCenterDesc 

,stat

, TO_DATE(E.event_date_time) as AsOfDate



from risk.affordability.ga2_pos_affordability E

LEFT JOIN risk.affordability.ga2_pos_affordability_financed_vehicle FV

ON E.business_event_id = FV.business_event_id

left join INVENTORY.VEHICLE.STOCKTODAYACTIVE st on st.stknbr= fv.stock_number

left join inventory_sandbox.admdev.dbo_tblccdmapping ccd on ccd.crllt= st.clot

-- WHERE 

-- to_date(e.event_date_time) = current_date--'2026-01-12'

and E.event_name = 'posAffordability'

AND FV.stock_number NOT LIKE '2%%'

and childcostcenterdesc in ('MONTCLAIR', 'RIVERSIDE')

and stat= 'AV'

--and in_process_desc ='Dealer'

--and fv.stock_number=1010200734



),



stocknextdate as (

    select stocknumber, asofdate,

        ifnull(lead(asofdate) over (partition by stocknumber order by asofdate), current_date()) as nextdate

    from (select distinct stocknumber, asofdate from INVENTORY.VEHICLE.STOCKTREND where stocknumber < 1990000000 and asofdate >= '2025-01-01')

 --   where stocknumber =1120265036

),



trendedfrontlines as (

select distinct st.stocknumber,st.asofdate, ccd.childcostcenterid,ccd.childcostcenterdesc,in_process_desc,ccd.parentcostcenterdesc

,snd.nextdate

,a.classmake,a.classmodel,distrogroups,SIZEGROUP,sourcingregion

,coalesce(mm.commonmodel,mm2.commonmodel,CONCAT('OTHER_',case when sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE SIZEGROUP END)) as commonmodel

,case when t.stock_number is not null and in_process_desc ilike 'Dealer' then 1 else 0 end as Frontline

,case when ws.website_stocks is not null then 1 else 0 end as websiteunit

--,CASE WHEN mm.commonmodel IS NULL THEN CONCAT('OTHER_',sizegroup) ELSE MM.COMMONMODEL END AS COMMONMODEL

,activedealerdays

,reportingregiondescription

,case when s.odometer <40000 then '0-40000'

when s.odometer between 40000 and 60000 then '40000-60000'

when s.odometer between 60001 and 80000 then '60000-80000'

when s.odometer between 80001 and 100000 then '80000-100000'

when s.odometer between 100001 and 120000 then '100000-120000'

when s.odometer between 120001 and 140000 then '120000-140000'

when s.odometer between 140001 and 160000 then '140000-160000'

when s.odometer > 160000 then '160000+' else 'UNKNOWN'

end as Mileagebucket

 ,CONCAT('OTHER_',case when sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE SIZEGROUP END)

from INVENTORY.VEHICLE.STOCKTREND st

left join inventory.vehicle.stock s

    on st.stocknumber=s.stocknumber

inner join stocknextdate snd

    on st.stocknumber = snd.stocknumber

    and st.asofdate = snd.asofdate

left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

on st.currentcostcenterid=childcostcenterid

left join 

(select stock_number,min(upload_date) as upload_Date

from INVENTORY.TITLE.INFO_AVAILABILITY_TREND t

where title_distro_ready ilike 'AVAILABLE'

group by stock_number) t

    on st.stocknumber=t.stock_number

    and st.asofdate::Date>=upload_date::Date

left join website_stock ws

    on st.stocknumber=ws.website_stocks

    and st.asofdate=ws.asofdate

left join 

adpfinal a

    on st.stocknumber=a.stocknumber

    and rownumber = 1

left join 

(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm

--where iscurrent=1

) mm

   on COALESCE(upper(a.commonmodel),UPPER(SPLIT_PART(A.CLASSMODEL, ' ', 1)),CONCAT('OTHER_',sizegroup))=upper(mm.commonmodel)

   AND ST.ASOFDATE::dATE BETWEEN MM.BEGINDATE::DATE AND IFNULL(MM.ENDDATE::dATE,CURRENT_DATE)

  AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

    when MM.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

    upper(MM.crlld) end=upper(ccd.parentcostcenterdesc)

left join 

(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm

--where iscurrent=1

) mm2

   on CONCAT('OTHER_',case when sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE SIZEGROUP END)=upper(mm2.commonmodel)

   AND ST.ASOFDATE::dATE BETWEEN MM.BEGINDATE::DATE AND IFNULL(MM.ENDDATE::dATE,CURRENT_DATE)

  AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

    when MM2.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

    upper(MM2.crlld) end=upper(ccd.parentcostcenterdesc)

  left join RISK_SANDBOX.MKOURYADHOC.STOCKLEVELADP sl

on st.stocknumber=sl.stocknumber

where st.stocknumber <1990000000

and st.asofdate >= '2025-01-01'

--and st.asofdate>='{target_date}'

--and ccd.parentcostcenterdesc ilike '%albany%'

and st.stocknumber not in (select stocknumber from layaways )

--and st.stocknumber = 1010233954

--and t.status_code <> 'LA';

),

--group by stocknumber;





-- select parentcostcenterdesc,sum(websiteunit) as website

-- from trendedfrontlines

-- group by parentcostcenterdesc;



Duplicates as (

select asofdate,parentcostcenterdesc,commonmodel,Mileagebucket,DistroGroups,count(stocknumber) as totaldupes

from trendedfrontlines

--where parentcostcenterdesc in ('Dealer')

-- where asofdate= '2026-06-14'

-- and parentcostcenterdesc ilike 'RALEIGH'

group by asofdate,parentcostcenterdesc,commonmodel,Mileagebucket,DistroGroups





),





minreasonLR AS (

    SELECT 

        CH.stock_number, 

        MIN(created_date) AS mindayinlr,

        CH.CLAIM_NUMBER

    FROM 

        ANCILLARY.LOT_REPAIR.CLAIM_HEADER CH

    LEFT JOIN 

        ANCILLARY.LOT_REPAIR.CLAIM_DETAIL CD

        ON CH.CLAIM_ID = CD.CLAIM_ID

    left join ANCILLARY.LOT_REPAIR.SERVICEDRIVE_CLAIM_REASON CR

        on CH.CLAIM_ID=CR.CLAIM_ID

       where UPPER(Ch.Claim_Approval_Status) NOT IN ('PENDING', 'DENIED')

        AND   (  case when parent_claim_reason='EMMS'

           and (description ilike '%emis%' or description ilike '%inspec%') then 1 else 0 end =1

           OR

           case when claim_reason='EMMS'

           and (description ilike '%emis%' or description ilike '%inspec%') then 1 else 0 end =1 OR

            description ILIKE 'EMMS' or

            description ILIKE '%Emi%' OR

            description ILIKE '%emm%' or

           -- description ILIKE '%emo%' or

            description ILIKE '%insp%' OR 

            description ILIKE '%msi%' OR 

            description ILIKE '%ncsi%' OR 

            description ILIKE '%safety insp%' or

            description ILIKE '%safely insp%' or

            description ILIKE '%state in%' or

            description ILIKE '%state is%' or

             description ILIKE '%states em%' or

            description ILIKE '%state em%' OR

            description ILIKE 'EMMS')

    GROUP BY 

        CH.stock_number,CH.CLAIM_NUMBER

),



totalextraspend as (

select ch.stock_number, total_paid,requested_total_amount,description,ch.created_date

from

    ANCILLARY.LOT_REPAIR.CLAIM_HEADER ch

LEFT JOIN 

    ANCILLARY.LOT_REPAIR.CLAIM_DETAIL CD

    ON ch.CLAIM_ID = CD.CLAIM_ID 

LEFT JOIN 

    minreasonLR minr

    ON ch.stock_number = minr.stock_number

    AND ch.created_date = minr.mindayinlr 

WHERE 

    ch.closed_date IS NOT NULL

     --AND ch.created_date >= '2024-01-01'

--     AND NOT EXISTS (

--         SELECT 1 

--         FROM inspectioncenter ic 

--         WHERE ic.stocknumber = lrc.stocknumber

--     )

--and description is not null

and description not in ('Emissions Test','State Inspection','Inspection Fee - Pending','Used Car Inspection / MPI')

and minr.stock_number is not null

--and lrc.STOCKNUMBER = 1330075923



and status not in ('Denied')

),



lotrepairstore as (

select distinct ch.stock_number,parentcostcenterdesc,ch.created_date

,case when ts.stock_number is not null then 1 else 0 end as EmissionsExtraRepair

,case when minr.stock_number is not null and dr.storecostcenter_id is not null and ts.stock_number is null then 1 else 0 end as PreFrontlineProcessCar

,case when minr.stock_number is not null and dr.storecostcenter_id is null and ts.stock_number is null then 1 else 0 end as EmissionsReUp 

FROM 

        ANCILLARY.LOT_REPAIR.CLAIM_HEADER CH

    LEFT JOIN 

        ANCILLARY.LOT_REPAIR.CLAIM_DETAIL CD

        ON CH.CLAIM_ID = CD.CLAIM_ID

    left join ANCILLARY.LOT_REPAIR.SERVICEDRIVE_CLAIM_REASON CR

        on CH.CLAIM_ID=CR.CLAIM_ID

    left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

        on ch.store_number=ccd.crllt

    LEFT JOIN ANCILLARY.LOT_REPAIR.CLAIM_CYCLE_DATES lr

    ON ch.claim_number = lr.claim_number

   left join totalextraspend ts

    on ch.stock_number=ts.stock_number

    and cd.description=ts.description

    and cd.total_paid=ts.total_paid

    and ch.created_date=ts.created_date

    LEFT JOIN 

    minreasonLR minr

    ON ch.stock_number = minr.stock_number

    AND ch.created_date = minr.mindayinlr

    AND CH.CLAIM_NUMBER=MINR.CLAIM_NUMBER

    left join INVENTORY_SANDBOX.SUPPLYCHAIN.TBLDISTROREQUIREMENTS dr

        on ccd.childcostcenterid=dr.storecostcenter_id

where ch.repair_facility_name not ilike '%Unwinds%'

and ch.created_date>= '2026-01-01'

--and ch.stock_number=1120265036;

),



lotrepair as (

select asofdate,tf.stocknumber,tf.childcostcenterdesc,lr.parentcostcenterdesc,tf.distrogroups,sourcingregion,in_process_desc

,coalesce(mm.commonmodel,mm2.commonmodel,CONCAT('OTHER_',case when a.sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE a.SIZEGROUP END)) as commonmodel

,EmissionsExtraRepair,PreFrontlineProcessCar,EmissionsReUp,nextdate

,tf.classmake

,tf.classmodel

from trendedfrontlines tf

left join lotrepairstore lr

    on tf.stocknumber=lr.stock_number

    and asofdate::Date between lr.created_date::date and nextdate::date

left join 

adpfinal a

    on tf.stocknumber=a.stocknumber

    and rownumber = 1

left join 

(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm

--where iscurrent=1

) mm

   on COALESCE(upper(a.commonmodel),UPPER(SPLIT_PART(A.CLASSMODEL, ' ', 1)),CONCAT('OTHER_',A.sizegroup))=upper(mm.commonmodel)

   AND TF.ASOFDATE::dATE BETWEEN MM.BEGINDATE::DATE AND IFNULL(MM.ENDDATE::dATE,CURRENT_DATE)

  AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

    when MM.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

    upper(MM.crlld) end=upper(lr.parentcostcenterdesc)

left join 

(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm

--where iscurrent=1

) mm2

   on CONCAT('OTHER_',case when A.sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE A.SIZEGROUP END)=upper(mm2.commonmodel)

   AND TF.ASOFDATE::dATE BETWEEN MM.BEGINDATE::DATE AND IFNULL(MM.ENDDATE::dATE,CURRENT_DATE)

  AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

    when MM2.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

    upper(MM2.crlld) end=upper(lr.parentcostcenterdesc)

where in_process_desc = 'Lot Repair'

--and asofdate = '{target_date}';

--and tf.STOCKNUMBER= 1120265036



),



-- select distinct parentcostcenterdesc

-- from lotrepair

-- where asofdate= '2026-06-09'

-- ;





allocations as (

SELECT distinct

       t.stocknumber,

        t.allocationdate::date AS allocationdate,

        ccd.parentcostcenterdesc,

        ccd2.sourcingregion AS RC

        --allocationstatustypedescription

      --  maxchangedate::date as enddate

        ,classmake,classmodel,distrogroups

        ,case when allocationstatustypedescription in ('Removed','Completed','Unfulfilled') then maxchangedate::date else current_date() end as enddate

        ,ifnull(mm.commonmodel,mm2.commonmodel) as commonmodel

        ,ccd.sourcingregion

      -- case when  allocationstatustypedescription ilike 'Removed' or allocationstatustypedescription ilike 'Unfulfilled' then lastchangeddatetime::date else null end as RemovedDate

    FROM 

        INVENTORY.TRANSPORT.TRANSFERALLOCATIONTREND t

        inner join  (    select stocknumber,allocationdate, max(lastchangeddatetime::date) as maxchangedate

        from  INVENTORY.TRANSPORT.TRANSFERALLOCATIONTREND

       -- where allocationstatustypedescription in ('Removed','Completed','Unfulfilled')

        group by stocknumber,allocationdate

        ) t3

        on t.stocknumber=t3.stocknumber

        and t.allocationdate=t3.allocationdate

    LEFT JOIN 

        INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

        ON ccd.crllt = tolocationkey

    LEFT JOIN 

        INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd2

        ON ccd2.crllt = fromlocationkey

    left join adpfinal a

        on t.stocknumber=a.stocknumber

    left join 

(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm

where iscurrent=1) mm

   on COALESCE(upper(a.commonmodel),UPPER(SPLIT_PART(A.CLASSMODEL, ' ', 1)),CONCAT('OTHER_',sizegroup))=upper(mm.commonmodel)

  -- AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

  --   when MM.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

  --   upper(MM.crlld) end=upper(ccd.parentcostcenterdesc)

left join 

(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm

where iscurrent=1) mm2

   on CONCAT('OTHER_',case when sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE SIZEGROUP END)=upper(mm2.commonmodel)

  -- AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

  --   when MM2.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

  --   upper(MM2.crlld) end=upper(ccd.parentcostcenterdesc)

where (ccd.in_process_desc ilike 'Dealer' or  ccd.in_process_desc ilike 'Holding Lot')

    order by allocationdate desc

--where allocationstatustypedescription ilike 'Removed'

),





-- select*

-- from allocations

-- where allocationdate = '2026-05-13'

-- and parentcostcenterdesc ilike 'Albuq%'

-- ;

finalallocations as(

select distinct calendardate,A.stocknumber,A.parentcostcenterdesc,A.classmake,A.classmodel,A.distrogroups,a.commonmodel,a.sourcingregion

from allocations A

left join SHARED.DIMENSION.DIMDATE d

    on calendardate between allocationdate and enddate

    and allocationdate >= DATEADD(DAY,-7,calendardate)

LEFT JOIN TRENDEDFRONTLINES  T

    ON A.STOCKNUMBER=T.STOCKNUMBER

    AND D.calendardate::DATE=T.ASOFDATE::DATE

    AND A.PARENTCOSTCENTERDESC=T.PARENTCOSTCENTERDESC

WHERE T.STOCKNUMBER IS NULL

--where stocknumber = 1630098172

--and calendardate = '2026-06-08';

),



-- select*

-- from finalallocations

-- where calendardate = '2026-05-13'

-- and parentcostcenterdesc ilike 'Albuq%'

-- --AND STOCKNUMBER = 1050216790

-- ;





titlesinprocess as (

select asofdate,stocknumber,childcostcenterdesc,parentcostcenterdesc,classmake,classmodel,distrogroups,t.*

from trendedfrontlines tf

left join INVENTORY.TITLE.INFO_AVAILABILITY_TREND t

    on tf.stocknumber=t.stock_number

    and tf.asofdate= upload_date

where in_process_desc in ('Dealer','Holding Lot','Lot Repair')

and title_distro_ready='Unavailable' 

and title_location <> 'Dealership-Shipped'

and status_code <> 'LA'

-- and parentcostcenterdesc ilike 'Conyers'

 --and asofdate = '2025-10-15'

),





dealeroptimums as (

select costcenter_id,childcostcenterdesc,low,high,effectivedate,enddate,parentcostcenterdesc,capacity

from INVENTORY_SANDBOX.SUPPLYCHAIN.DEALERSHIPLOTOPTIMUMS

left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

    on costcenter_id=ccd.childcostcenterid

--where open_location= 'Y'

--where childcostcenterdesc ilike 'esco%'

),



holdingoptimum as (

select costcenter,childcostcenterdesc,opt,effective_date,end_date,parentcostcenterdesc,capacity

from INVENTORY_SANDBOX.SUPPLYCHAIN.HOLDINGLOTOPTIMUMS h

left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

    on h.crllt=ccd.crllt

),



dailysales as (

select df.calendar_date

,ParentCostCenterDesc

	,  SUM( df.Units) as today

	,  SUM(df2.Units) as day1

	, SUM(df3.Units) as  day2

    , SUM(df4.Units) as  day3

    , SUM(df5.Units) as  day4

    , SUM(df6.Units) as  day5

    , SUM(df7.Units) as  day6

   -- ,sum(df8.units)  as Day30

from INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df

left join SHARED.DIMENSION.DIMDATE dd

    on df.calendar_date=dd.calendardate

inner join 

(select calendar_date, max(load_time_stamp) as maxload

from INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df

group by calendar_date

) d

    on df.calendar_date=d.calendar_date

    and df.load_time_stamp=d.maxload

       LEFT join INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df2

        on df2.calendar_date=dateadd(day,1,df.calendar_date)

        and df.costcenter_id=df2.costcenter_id

        and df.load_period=df2.load_period

        AND DF.LOAD_TIME_STAMP=DF2.LOAD_TIME_STAMP

       left join INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df3

        on df3.calendar_date=dateadd(day,2,df.calendar_date)

        and df.costcenter_id=df3.costcenter_id

        and df.load_period=df3.load_period

         AND DF.LOAD_TIME_STAMP=DF3.LOAD_TIME_STAMP

        left join INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df4

        on df4.calendar_date=dateadd(day,3,df.calendar_date)

        and df.costcenter_id=df4.costcenter_id

        and df.load_period=df4.load_period

         AND DF.LOAD_TIME_STAMP=DF4.LOAD_TIME_STAMP

        left join INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df5

        on df5.calendar_date=dateadd(day,4,df.calendar_date)

        and df.costcenter_id=df5.costcenter_id

        and df.load_period=df5.load_period

         AND DF.LOAD_TIME_STAMP=DF5.LOAD_TIME_STAMP

        left join INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df6

         on df6.calendar_date=dateadd(day,5,df.calendar_date)

         and df.costcenter_id=df6.costcenter_id

        and df.load_period=df6.load_period

         AND DF.LOAD_TIME_STAMP=DF6.LOAD_TIME_STAMP

        left join INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df7

         on df7.calendar_date=dateadd(day,6,df.calendar_date)

         and df.costcenter_id=df7.costcenter_id

        and df.load_period=df7.load_period

         AND DF.LOAD_TIME_STAMP=DF7.LOAD_TIME_STAMP

        --     left join INVENTORY_SANDBOX.SUPPLYCHAIN.DAILYUNITFORECAST df8

        --  on df8.calendar_date between df.calendar_date and dateadd(day,30,df.calendar_date) 

        --  and df.costcenter_id=df8.costcenter_id

        -- and df.load_period=df8.load_period

        --  AND DF.LOAD_TIME_STAMP=DF8.LOAD_TIME_STAMP

inner join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

On df.costcenter_id = ccd.ChildCostCenterID

--Where df.IsCurrent = 1

	WHERE ccd.Program = 'DT'

     -- and df.calendar_date= '2025-07-08'

     -- and parentcostcenterdesc= 'FT PIERCE'

Group By df.calendar_date,ParentCostCenterDesc

),



distrorequirements as (

select distinct StoreCostCenter_ID,ParentCostCenterDesc

from INVENTORY_SANDBOX.SUPPLYCHAIN.TBLDISTROREQUIREMENTS

inner join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

on StoreCostCenter_ID=ChildCostCenterID

and program ilike 'DT'

and In_Process_Desc ilike 'dealer'



),



HOLDINGLOTCAPACITY AS (

SELECT distinct parentcostcenterdesc,childcostcenterdesc,capacity

FROM  INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING

WHERE IN_PROCESS_DESC ILIKE 'Holding Lot'

and program = 'DT'

and open_location= 'Y'

),





 

 allsales as (

SELECT STOCKNUMBER, SALEDATE, SALETIMEOFDAY, 1 AS NETSALEID, 'Sale' as SALETYPE, BACKOUTDATE,parentcostcenterdesc,sourcingregion

FROM RETAIL.SALE.CENTRALIZEDSALE

left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

    on salelocationnumber=crllt

WHERE saledate >= '2024-01-01'

AND stocknumber < 1990000000



UNION 



SELECT STOCKNUMBER, BACKOUTDATE AS SALEDATE, SALETIMEOFDAY, -1 AS NETSALEID, SALETYPE, NULL AS BACKOUTDATE,parentcostcenterdesc,sourcingregion

FROM RETAIL.SALE.CENTRALIZEDSALE

left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

    on salelocationnumber=crllt

WHERE SALETYPE = 'Backed Out Sale'

AND saledate >= '2024-01-01'

AND stocknumber < 1990000000

),



finalallsales as (

select stocknumber, sum(netsaleid) as netsaleid,saledate,parentcostcenterdesc,sourcingregion

from allsales

where saledate>='2024-01-01'

and stocknumber < 1990000000

group by stocknumber,saledate,parentcostcenterdesc,sourcingregion

),



maxdate as (

select distinct stocknumber, max(asofdate) as maxdate

from trendedfrontlines

group by stocknumber

),



maxreportingregion as (

select distinct  t.stocknumber,t.reportingregiondescription

from trendedfrontlines t

inner join maxdate m    

on t.stocknumber=m.stocknumber

and t.asofdate=m.maxdate

),



Daysonfrontline as (

select DISTINCT

asofdate

,in_process_desc

 ,t.stocknumber

,m.reportingregiondescription as  reportingregiondescription

,distrogroups

,row_number() over (partition by t.stocknumber, in_process_desc order by asofdate) as totaldaysonfrontline

,mileagebucket

from trendedfrontlines t

--LEFT JOIN 

-- left join finalallsales f

--     on t.stocknumber=f.stocknumber

    --and asofdate>= saledate

left join maxreportingregion m

    on t.stocknumber=m.stocknumber

--where in_process_desc= 'Dealer'

where t.frontline=1 

-- and t.stocknumber = 1330079805

-- and asofdate= '2026-06-10'

-- ;

)



, daily_sales as (

     select

   d.calendardate, ccd.parentcostcenterdesc

    , ifnull(sum(netsaleid),0) as day_sales

    ,ccd.sourcingregion

    ,count(distinct case when totaldaysonfrontline<=7 then s.stocknumber end) as Soldin7

   -- ,s.stocknumber

    --,dof.totaldaysonfrontline

    from SHARED.DIMENSION.DIMDATE d

    left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

        on 1=1

        and ccd.in_process_desc ilike 'dealer'

        and program='DT'

        and open_location='Y'

    left join finalallsales s

        on s.saledate = d.calendardate

        and s.parentcostcenterdesc=ccd.parentcostcenterdesc

    left join Daysonfrontline dof

        on s.stocknumber=dof.stocknumber

        and dateadd(day,-1,calendardate)=dof.asofdate

    where calendardate between dateadd(day, -7, '{target_date}') and '{target_date}'

   --and s.STOCKNUMBER=1330079805

    group by d.calendardate, ccd.parentcostcenterdesc,ccd.sourcingregion

    

)





-- select distinct asofdate,stocknumber,parentcostcenterdesc,childcostcenterdesc,in_process_desc,classmake,classmodel,distrogroups,commonmodel

-- from trendedfrontlines f

-- where in_process_desc ilike 'Dealer'

-- AND ASOFDATE::dATE = '2026-06-04'

-- AND DISTROGROUPS IS NULL



-- ;



select

--src.stocknumber

d.calendardate as datekey

,ifnull(src.parentcostcenterdesc,imm.parentcostcenterdesc) as parentcostcenterdesc

,ifnull(src.sourcingregion,imm.sourcingregion) as SourcingRegion

,imm.commonmodel as CommonModel

,avg(src.activedealerdays) as avgdealerdays

,count(distinct case when src.in_process_desc ilike 'Dealer' and src.frontline>=1 then src.stocknumber end) as Frontline

,count(distinct case when websiteunit>=1 then src.stocknumber end) as WebsiteUnit

,count(distinct case when f2.in_process_desc ilike 'Dealer' and f2.frontline>= 1 then f2.stocknumber end) as Last7DaysFrontline

,totalstocks as StoreTotalFrontlineInventory

,count(distinct case when src.in_process_desc ilike 'Holding Lot' then src.stocknumber end) as  HoldingLot

,count(distinct case when src.in_process_desc ilike 'Allocation' then src.stocknumber end) as  Allocations

,count(distinct case when src.in_process_desc ilike 'Lot Repair' then src.stocknumber end) as  LotRepair

,count(distinct case when src.PreFrontlineProcessCar>=1 and  EmissionsExtraRepair=0 then src.stocknumber end) as PreFrontlineProcessStock

,count(distinct case when EmissionsExtraRepair=1 then src.stocknumber end) as PreFrontlineProcessExtraRepair

,count(distinct case when src.emissionsreup=1 then src.stocknumber end) as EmissionsReUp

,count(distinct case when src.in_process_desc ilike 'Layaway' then src.stocknumber end) as  Layaway

,null AS today

,null aS  day1

,null aS day2

,null aS day3

,null aS day4

,null aS day5

,null aS day6

,case when dr.parentcostcenterdesc is not null then 1 else 0 end as PrefrontlineProcess

,null as DealerOptimum

,null as HoldingOptimum

,null as DealerCapacity

,null as HoldingLotCapacity

-- ,LTS

-- ,LTS_BUDGET

,imm.finalmerchmix

,null as sales

,null as last7dayssales

,null as soldin7

from SHARED.DIMENSION.DIMDATE d

right join  (select imm.*,sourcingregion,parentcostcenterdesc

 from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX imm

 left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd

    on  case when imm.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

    when imm.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

    upper(imm.crlld) end=upper(ccd.parentcostcenterdesc)

-- where crlld ilike 'north houston'

 ) imm

    on  

    d.calendardate::DATE between imm.begindate::DATE and ifnull(imm.enddate::dATE,current_date())

left join

(

    SELECT stocknumber, distrogroups, parentcostcenterdesc,classmake,commonmodel, asofdate AS datekey,in_process_desc,sourcingregion,activedealerdays,frontline,websiteunit,null as EmissionsExtraRepair,null as PreFrontlineProcessCar,null as emissionsreup FROM trendedfrontlines

    where in_process_desc in ('Dealer','Holding Lot')

    UNION all

    

    SELECT stocknumber, distrogroups, parentcostcenterdesc,classmake,commonmodel, calendardate as datekey,'Allocation' as in_process_desc,sourcingregion,null as activedealerdays,null as frontline,null as websiteunit,null as EmissionsExtraRepair,null as PreFrontlineProcessCar,null as emissionsreup FROM finalallocations

    UNION all

    

    SELECT stocknumber, distrogroups, parentcostcenterdesc,classmake,commonmodel, asofdate as datekey, in_process_desc,sourcingregion,null as activedealerdays,null as frontline,null as websiteunit,EmissionsExtraRepair,PreFrontlineProcessCar,EmissionsReUp FROM lotrepair



    union all 

    

    SELECT stocknumber, distrogroups, parentcostcenterdesc,classmake,commonmodel, asofdate as datekey,'Layaway' as in_process_desc,sourcingregion,null as activedealerdays,null as frontline,null as websiteunit,null as EmissionsExtraRepair,null as PreFrontlineProcessCar,null as emissionsreup FROM layaways

) src

on d.calendardate=src.datekey

and upper(imm.commonmodel)= upper(src.commonmodel)

    and 

    case when imm.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

    when imm.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

    upper(imm.crlld) end=upper(src.parentcostcenterdesc)

left join

(select distinct asofdate,stocknumber,parentcostcenterdesc,childcostcenterdesc,in_process_desc,classmake,classmodel,distrogroups,commonmodel,activedealerdays,Frontline

from trendedfrontlines f

where (in_process_desc ilike 'Dealer'

or in_process_desc ilike 'Holding Lot')

) f2

    on f2.parentcostcenterdesc=src.parentcostcenterdesc

    and f2.asofdate::date>=dateadd(day,-7,d.calendardate::date)

    and src.distrogroups=f2.distrogroups

    and src.commonmodel=f2.commonmodel

left join (

select distinct asofdate,count(distinct stocknumber) as totalstocks,parentcostcenterdesc,childcostcenterdesc

from trendedfrontlines f

where in_process_desc ilike 'Dealer'

group by asofdate,parentcostcenterdesc,childcostcenterdesc

) f3

 on f3.parentcostcenterdesc=src.parentcostcenterdesc

    and f3.asofdate::date=d.calendardate::date

left join distrorequirements dr

    on src.parentcostcenterdesc=dr.parentcostcenterdesc

-- right join  (select*

--  from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX

-- -- where crlld ilike 'north houston'

--  ) imm

--      on upper(imm.commonmodel)= src.commonmodel

--     and 

--     case when imm.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'

--     when imm.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else

--     upper(imm.crlld) end=upper(src.parentcostcenterdesc)

--     and d.calendardate between imm.begindate and ifnull(imm.enddate,current_date())

-- left join LTSFINAL lts

--     on upper(src.parentcostcenterdesc)=upper(lts.crlld)

--     and datekey::date=lts.day::date

-- left join 

-- (select distinct stocknumber,asofdate,totaldaysonfrontline

-- from Daysonfrontline) dof

--     on src.stocknumber=dof.stocknumber

--     and src.datekey::date=dof.asofdate::Date

--where datekey between '2026-01-01' and current_date()

where d.calendardate = '{target_date}'

--and src.stocknumber = 1120256745



--and ifnull(src.parentcostcenterdesc,imm.crlld) ilike 'ALBANY%'

group by d.calendardate

,src.parentcostcenterdesc

,src.sourcingregion

,src.commonmodel

,totalstocks

,imm.finalmerchmix

,dr.parentcostcenterdesc

-- ,LTS

-- ,LTS_BUDGET

,imm.commonmodel

,imm.parentcostcenterdesc

,imm.sourcingregion





--,src.stocknumber





UNION ALL



SELECT DISTINCT

d.calendardate as datekey

,do.parentcostcenterdesc as parentcostcenterdesc

,null as sourcingregion

--,null as commonmodel

--,f.commonmodel

,null as commonmodel

,null as avgdealerdays

,null as Frontline

,null as WebsiteUnit

,null as Last7DaysFrontline

,null as StoreTotalFrontlineInventory

,null as  HoldingLot

--,ifnull(allocations,0) as allocations

,null AS ALLOCATIONS 

,null AS LOTREPAIR

,null as PreFrontlineProcessStock

,null as PreFrontlineProcessExtraRepair

,null as EmissionsReUp

--,IFNULL(TitlesInProcess,0) AS TITLESINPROCESS

,null AS LAYAWAY

,IFNULL(today,0) AS today

,IFNULL(day1,0) AS  day1

,IFNULL(day2,0) AS day2

,IFNULL(day3,0) AS day3

,IFNULL(day4,0) AS day4

,IFNULL(day5,0) AS day5

,IFNULL(day6,0) AS day6

,null  as PrefrontlineProcess

,do.high as DealerOptimum

,ho.opt as HoldingOptimum

,do.capacity as DealerCapacity

,ho.capacity as HoldingLotCapacity

,null as finalmerchmix

,null as sales

,null as last7dayssales

,null as soldin7

FROM SHARED.DIMENSION.DIMDATE d

left join dealeroptimums do 

    --on ccd.parentcostcenterdesc=do.parentcostcenterdesc

    ON d.calendardate between do.effectivedate and do.enddate 

    --and 

left join holdingoptimum ho

     on DO.parentcostcenterdesc=ho.parentcostcenterdesc

    AND d.calendardate between ho.effective_date and ho.end_date 

left join dailysales s

    on do.parentcostcenterdesc=s.parentcostcenterdesc

    and d.calendardate::date=s.calendar_date::date

--where d.calendardate between '2026-01-01' and current_date()

where d.calendardate = '{target_date}'

--and do.parentcostcenterdesc ilike 'north houston'



union all



 select calendardate as datekey

,parentcostcenterdesc as parentcostcenterdesc

,sourcingregion as sourcingregion

--,null as commonmodel

--,f.commonmodel

,null as commonmodel

,null as avgdealerdays

,null as Frontline

,null as WebsiteUnit

,null as Last7DaysFrontline

,null as StoreTotalFrontlineInventory

,null as  HoldingLot

--,ifnull(allocations,0) as allocations

,null AS ALLOCATIONS 

,null AS LOTREPAIR

,null as PreFrontlineProcessStock

,null as PreFrontlineProcessExtraRepair

,null as EmissionsReUp

--,IFNULL(TitlesInProcess,0) AS TITLESINPROCESS

,null AS LAYAWAYS

,NULL AS today

,NULL AS  day1

,NULL AS day2

,NULL AS day3

,NULL AS day4

,NULL AS day5

,NULL AS day6

--,IFNULL(DAY30,0) AS DAY30

,null  as PrefrontlineProcess

,null as DealerOptimum

,null as HoldingOptimum

,null as DealerCapacity

,null as HoldingLotCapacity

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'CAR-AnySize-0K-12K KBB'       THEN src.stocknumber END) AS "CAR-AnySize-0K-12K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'CAR-AnySize-12K-18K KBB'      THEN src.stocknumber END) AS "CAR-AnySize-12K-18K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'CAR-AnySize-18K-20K KBB'      THEN src.stocknumber END) AS "CAR-AnySize-18K-20K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'CAR-AnySize-20K-99K KBB'      THEN src.stocknumber END) AS "CAR-AnySize-20K-99K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'SUV-LargeSUV-0K-99K KBB'      THEN src.stocknumber END) AS "SUV-LargeSUV-0K-99K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'SUV-MediumSUVSize-0K-16K KBB' THEN src.stocknumber END) AS "SUV-MediumSUVSize-0K-16K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'SUV-MediumSUVSize-16K-22K KBB'THEN src.stocknumber END) AS "SUV-MediumSUVSize-16K-22K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'SUV-MediumSUVSize-22K-99K KBB'THEN src.stocknumber END) AS "SUV-MediumSUVSize-22K-99K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'SUV-SmallSUVSize-0K-14K KBB'  THEN src.stocknumber END) AS "SUV-SmallSUVSize-0K-14K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'SUV-SmallSUVSize-14K-99K KBB' THEN src.stocknumber END) AS "SUV-SmallSUVSize-14K-99K KBB"

-- ,COUNT(DISTINCT CASE WHEN src.distrogroups = 'TRUCK-TruckSize-0K-99K KBB'   THEN src.stocknumber END) AS "TRUCK-TruckSize-0K-99K KBB"



,null as finalmerchmix

, coalesce(day_sales, 0) as sales

,(

        select sum(day_sales)

        from daily_sales d2

        where d2.parentcostcenterdesc = d1.parentcostcenterdesc

          and d2.calendardate >= dateadd(day, -7, d1.calendardate)

          and d2.calendardate <= d1.calendardate

    ) as  last7dayssales

,Soldin7 as Soldin7

from daily_sales d1



--where calendardate between '2026-01-01' and current_date()

where calendardate = '{target_date}'

--and parentcostcenterdesc ilike 'central%'
"""


TRENDS_SQL = """
with

sizes as (
select distinct
size
,MAKE
,MODEL
from REPLICATED.BUY.DBO_TBLMMRVEHICLEDESCRIPTION mmr
LEFT JOIN inventory.vehicle.stock s
    On s.MMR_MID = TRY_TO_NUMBER(mmr.mmr_mid)
left join INVENTORY.BUY.FACTVEHICLE v
    on s.stocknumber=v.stocknumber
),

STOCKS AS (
SELECT
    SDD.WEEK_ENDING_SUNDAY AS ACQUISITION_WEEK
    , ST.STOCKNUMBER
    , SG.SIZE_GROUPS_EURO AS SIZEGROUP
    ,st.classmake
    ,st.classmodel
    ,siz.size
    , KG.KBB_GROUP
    ,mmr.commonmodel
FROM INVENTORY.VEHICLE.STOCK ST
LEFT JOIN SHARED.DIMENSION.DATE SDD
    ON SDD.CALENDAR_DATE = ST.ACQUISITIONDATE
LEFT JOIN INVENTORY.BUY.FACTVEHICLE FV
    ON FV.STOCKNUMBER = ST.STOCKNUMBER
LEFT JOIN INVENTORY.BUY.VEHICLE BV
    ON FV.BUYONIC_BUY_AUCTION_VEHICLE_ID = BV.BUYAUCTIONVEHICLEID
LEFT JOIN REPLICATED.BUY.DBO_TBLMMRVEHICLEDESCRIPTION mmr
    ON ST.MMR_MID=MMR.MMR_MID
left join sizes siz
    on st.classmake=siz.make
    and st.classmodel=siz.model
LEFT JOIN RISK_SANDBOX.OROCKWOOD.SIZE_GROUPS SG
    ON coalesce(UPPER(REGEXP_REPLACE(BV.SIZE,'SALMON ','')),MMR.size,siz.size) = SG.Size
LEFT JOIN Inventory_Sandbox.Public.Incremental_BuyBox BB
    ON ST.StockNumber = BB.StockNumber
LEFT JOIN INVENTORY_SANDBOX.PI7CALC_REFERENCE.STATES_SUPER_REGIONS_REF STATE
    ON BV.PICKUPLOCATIONSTATE = STATE.STATE
LEFT JOIN INVENTORY_SANDBOX.PI7CALC_REFERENCE.SUPER_REGIONS SR
    ON STATE.SUPER_REGION_ID = SR.SUPER_REGION_ID
LEFT JOIN INVENTORY_SANDBOX.STETSON_SANDBOX.KBB_GROUPS KG
    ON ifnull(BV.KBBVALUE,fv.kbb_value) BETWEEN KG.KBB_MIN AND KG.KBB_MAX
WHERE ST.STOCKNUMBER NOT ILIKE '2%%'
),

adpfinal as (
SELECT distinct
    S.*
    ,CASE WHEN sizegroup IN ('COMPACT','LARGE','MEDIUM') THEN 'CAR'
    WHEN sizegroup IN ('EURO','SPECIALTY','SPORTS') THEN 'SPECIALTY'
    WHEN sizegroup IN ('CROSSOVER','LARGE SUV','MEDIUM SUV','SMALL SUV','VAN') THEN 'SUV'
    WHEN sizegroup IN ('LARGE TRUCK','SMALL TRUCK') THEN 'TRUCK'
    ELSE 'UNKNOWN' END AS SIZEGROUP2
    ,case when sizegroup2 = 'SUV' and sizegroup='MEDIUM SUV' and KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K','14K-16K') then 'SUV-MediumSUVSize-0K-16K KBB'
    when sizegroup2 = 'SUV' and (sizegroup= 'SMALL SUV' or sizegroup = 'CROSSOVER') and KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K') then 'SUV-SmallSUVSize-0K-14K KBB'
    when sizegroup2 = 'SUV' and (sizegroup= 'SMALL SUV' or sizegroup = 'CROSSOVER') and kbb_group in ('14K-16K','16K-18K','18K-20K','20K-22K','22K-99K') then 'SUV-SmallSUVSize-14K-99K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group in ('16K-18K','18K-20K','20K-22K') then 'SUV-MediumSUVSize-16K-22K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group in ('22K-99K') then 'SUV-MediumSUVSize-22K-99K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group is null then 'SUV-MediumSUVSize-22K-99K KBB'
    when (sizegroup2= 'CAR' and sizegroup= 'MEDIUM' OR sizegroup = 'EURO' OR SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN') and KBB_group in ('12K-14K','14K-16K','16K-18K') then 'CAR-AnySize-12K-18K KBB'
    when (sizegroup2= 'CAR' and sizegroup= 'MEDIUM' OR sizegroup = 'EURO' OR SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN') and KBB_group in ('18K-20K') then 'CAR-AnySize-18K-20K KBB'
    when (sizegroup2= 'CAR' and sizegroup= 'MEDIUM' OR sizegroup = 'EURO' OR SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN') and KBB_group in ('20K-22K','22K-99K') then 'CAR-AnySize-20K-99K KBB'
    when (sizegroup2= 'CAR' OR SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and KBB_group in ('0K-8K','8K-10K','10K-12K') then 'CAR-AnySize-0K-12K KBB'
    when (sizegroup2= 'CAR' OR SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and KBB_group in ('12K-14K','14K-16K','16K-18K') then 'CAR-AnySize-12K-18K KBB'
    when (sizegroup2= 'CAR' OR SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and KBB_group in ('20K-22K','22K-99K') then 'CAR-AnySize-20K-99K KBB'
    when (sizegroup2= 'CAR' OR SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and KBB_group in ('18K-20K') then 'CAR-AnySize-18K-20K KBB'
    when (sizegroup2= 'SUV' or sizegroup='VAN' or sizegroup='LARGE SUV') then 'SUV-LargeSUV-0K-99K KBB'
    when sizegroup2= 'TRUCK' then 'TRUCK-TruckSize-0K-99K KBB'
    when sizegroup2= 'SUV' and KBB_group is null then 'SUV-LargeSUV-0K-99K KBB'
    WHEN sizegroup2= 'CAR' AND KBB_GROUP IS NULL THEN 'CAR-AnySize-20K-99K KBB'
    when sizegroup = 'VAN' AND KBB_GROUP IS NULL THEN 'SUV-LargeSUV-0K-99K KBB'
    WHEN SIZEGROUP='COMPACT' AND KBB_GROUP IS NULL THEN 'CAR-AnySize-20K-99K KBB'
    WHEN SIZEGROUP2= 'UNKNOWN' THEN 'CAR-AnySize-20K-99K KBB'
    when sizegroup2='SPECIALTY' and kbb_group is null then 'CAR-AnySize-20K-99K KBB'
    end as DistroGroups
FROM STOCKS S
where acquisition_week >= '2025-01-01'
),

layaways as (
select distinct st.stocknumber
from INVENTORY.VEHICLE.STOCKTREND st
left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
    on st.currentcostcenterid=childcostcenterid
left join INVENTORY.TITLE.INFO_AVAILABILITY_TREND t
    on st.stocknumber=t.stock_number
    and st.asofdate= upload_date
where in_process_desc in ('Dealer','Holding Lot','Lot Repair')
and title_distro_ready='Unavailable'
and title_location <> 'Dealership-Shipped'
and status_code= 'LA'
and st.asofdate between '{start_date}' and '{end_date}'
),

website_stock as (
SELECT distinct fv.stock_number as website_stocks
,upper(trim(ccd.PARENTCOSTCENTERDESC)) as ParentCostCenterDesc
,TO_DATE(E.event_date_time) as AsOfDate
from risk.affordability.ga2_pos_affordability E
LEFT JOIN risk.affordability.ga2_pos_affordability_financed_vehicle FV
    ON E.business_event_id = FV.business_event_id
left join INVENTORY.VEHICLE.STOCKTODAYACTIVE st on st.stknbr= fv.stock_number
left join inventory_sandbox.admdev.dbo_tblccdmapping ccd on ccd.crllt= st.clot
where E.event_name in ('ga2Affordability','posAffordability')
AND FV.stock_number NOT LIKE '2%%'
and TO_DATE(E.event_date_time) between '{start_date}' and '{end_date}'
),

trendedfrontlines as (
select distinct st.stocknumber, st.asofdate, ccd.parentcostcenterdesc, ccd.sourcingregion, in_process_desc
,a.classmake, a.classmodel, distrogroups
,coalesce(mm.commonmodel, mm2.commonmodel, CONCAT('OTHER_', case when a.sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' else a.sizegroup end)) as commonmodel
,case when t.stock_number is not null and in_process_desc ilike 'Dealer' then 1 else 0 end as Frontline
,case when ws.website_stocks is not null then 1 else 0 end as websiteunit
from INVENTORY.VEHICLE.STOCKTREND st
left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
    on st.currentcostcenterid=childcostcenterid
left join
(select stock_number, min(upload_date) as upload_date
from INVENTORY.TITLE.INFO_AVAILABILITY_TREND t
where title_distro_ready ilike 'AVAILABLE'
group by stock_number) t
    on st.stocknumber=t.stock_number
    and st.asofdate::date >= upload_date::date
left join website_stock ws
    on st.stocknumber=ws.website_stocks
    and st.asofdate=ws.asofdate
left join adpfinal a
    on st.stocknumber=a.stocknumber
left join
(select * from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX) mm
    on COALESCE(upper(a.commonmodel),UPPER(SPLIT_PART(A.CLASSMODEL, ' ', 1)),CONCAT('OTHER_',case when a.sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' else a.sizegroup end))=upper(mm.commonmodel)
    AND st.asofdate::date between mm.begindate::date and ifnull(mm.enddate::date, current_date)
    AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'
        when MM.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else
        upper(MM.crlld) end=upper(ccd.parentcostcenterdesc)
left join
(select * from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX) mm2
    on CONCAT('OTHER_',case when a.sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE a.SIZEGROUP END)=upper(mm2.commonmodel)
    AND st.asofdate::date between mm2.begindate::date and ifnull(mm2.enddate::date, current_date)
    AND case when MM2.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'
        when MM2.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else
        upper(MM2.crlld) end=upper(ccd.parentcostcenterdesc)
where st.stocknumber < 1990000000
and st.stocknumber not in (select stocknumber from layaways)
and st.asofdate between '{start_date}' and '{end_date}'
and ccd.parentcostcenterdesc is not null
),

store_frontline as (
    select asofdate, parentcostcenterdesc, sourcingregion,
        count(distinct case when in_process_desc ilike 'Dealer' and frontline >= 1 then stocknumber end) as frontline_count,
        count(distinct case when in_process_desc = 'Lot Repair' then stocknumber end) as lotrepair_count,
        count(distinct case when in_process_desc ilike 'Dealer' and frontline >= 1 and websiteunit >= 1 then stocknumber end) as website_units
    from trendedfrontlines
    group by asofdate, parentcostcenterdesc, sourcingregion
),

model_detail as (
    select asofdate, parentcostcenterdesc, commonmodel,
        count(distinct stocknumber) as model_count
    from trendedfrontlines
    where in_process_desc ilike 'Dealer' and frontline >= 1
        and commonmodel is not null
    group by asofdate, parentcostcenterdesc, commonmodel
),

store_totals as (
    select asofdate, parentcostcenterdesc, sum(model_count) as total_frontline
    from model_detail
    group by asofdate, parentcostcenterdesc
),

duplicates as (
    select asofdate, parentcostcenterdesc, sum(model_count - 1) as duplicate_units
    from model_detail
    where model_count > 1
    group by asofdate, parentcostcenterdesc
),

merch_dev as (
    select st.asofdate, st.parentcostcenterdesc,
        sum(abs(ifnull(md.model_count, 0) * 100.0 / nullif(st.total_frontline, 0) - mm.finalmerchmix * 100)) / 2 as total_deviation
    from store_totals st
    cross join (select * from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX where finalmerchmix > 0) mm
    left join model_detail md
        on md.asofdate = st.asofdate
        and md.parentcostcenterdesc = st.parentcostcenterdesc
        and upper(md.commonmodel) = upper(mm.commonmodel)
    where case when mm.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'
            when mm.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD'
            else upper(mm.crlld) end = upper(st.parentcostcenterdesc)
        and st.asofdate::date between mm.begindate::date and ifnull(mm.enddate::date, current_date)
    group by st.asofdate, st.parentcostcenterdesc
),

dealeroptimums as (
    select ccd.parentcostcenterdesc, high as dealeroptimum, effectivedate, enddate
    from INVENTORY_SANDBOX.SUPPLYCHAIN.DEALERSHIPLOTOPTIMUMS
    left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
        on costcenter_id=ccd.childcostcenterid
    where open_location = 'Y'
),

allsales as (
    SELECT STOCKNUMBER, SALEDATE, 1 AS NETSALEID, parentcostcenterdesc
    FROM RETAIL.SALE.CENTRALIZEDSALE
    left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
        on salelocationnumber=crllt
    where open_location = 'Y'
    and saledate between '{start_date}' and '{end_date}'

    UNION ALL

    SELECT STOCKNUMBER, BACKOUTDATE AS SALEDATE, -1 AS NETSALEID, parentcostcenterdesc
    FROM RETAIL.SALE.CENTRALIZEDSALE
    left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
        on salelocationnumber=crllt
    WHERE SALETYPE = 'Backed Out Sale'
    and open_location = 'Y'
    and backoutdate between '{start_date}' and '{end_date}'
),

daily_sales as (
    select saledate as calendardate, parentcostcenterdesc, sum(netsaleid) as day_sales
    from allsales
    where stocknumber < 1990000000
    group by saledate, parentcostcenterdesc
)

select
    sf.asofdate as calendardate,
    sf.parentcostcenterdesc,
    sf.sourcingregion,
    sf.frontline_count as frontline,
    do.dealeroptimum,
    sf.lotrepair_count as lotrepair,
    coalesce(ds.day_sales, 0) as sales,
    sf.website_units,
    coalesce(dup.duplicate_units, 0) as duplicate_units,
    mdev.total_deviation as merch_deviation
from store_frontline sf
left join dealeroptimums do
    on sf.parentcostcenterdesc = do.parentcostcenterdesc
    and sf.asofdate between do.effectivedate and do.enddate
left join daily_sales ds
    on sf.asofdate = ds.calendardate
    and sf.parentcostcenterdesc = ds.parentcostcenterdesc
left join duplicates dup
    on sf.asofdate = dup.asofdate
    and sf.parentcostcenterdesc = dup.parentcostcenterdesc
left join merch_dev mdev
    on sf.asofdate = mdev.asofdate
    and sf.parentcostcenterdesc = mdev.parentcostcenterdesc
order by sf.asofdate, sf.parentcostcenterdesc
"""


DUPES_SQL = """
with  

sizes as (
select distinct 
size
,MAKE
,MODEL
from  REPLICATED.BUY.DBO_TBLMMRVEHICLEDESCRIPTION  mmr
LEFT JOIN inventory.vehicle.stock s
    On s.MMR_MID = TRY_TO_NUMBER(mmr.mmr_mid)
left join INVENTORY.BUY.FACTVEHICLE v
    on s.stocknumber=v.stocknumber
),

STOCKS AS (
SELECT
    SDD.WEEK_ENDING_SUNDAY AS ACQUISITION_WEEK
    , ST.STOCKNUMBER
    , SG.SIZE_GROUPS_EURO AS SIZEGROUP
    ,st.classmake
    ,st.classmodel
    ,siz.size
    , KG.KBB_GROUP
    ,mmr.commonmodel
FROM INVENTORY.VEHICLE.STOCK ST
LEFT JOIN SHARED.DIMENSION.DATE SDD
    ON SDD.CALENDAR_DATE = ST.ACQUISITIONDATE
LEFT JOIN INVENTORY.BUY.FACTVEHICLE FV
    ON FV.STOCKNUMBER = ST.STOCKNUMBER
LEFT JOIN INVENTORY.BUY.VEHICLE BV
    ON FV.BUYONIC_BUY_AUCTION_VEHICLE_ID = BV.BUYAUCTIONVEHICLEID
LEFT JOIN REPLICATED.BUY.DBO_TBLMMRVEHICLEDESCRIPTION mmr 
    ON ST.MMR_MID=MMR.MMR_MID
left join sizes siz
    on st.classmake=siz.make
    and st.classmodel=siz.model
LEFT JOIN RISK_SANDBOX.OROCKWOOD.SIZE_GROUPS SG
    ON coalesce(UPPER(REGEXP_REPLACE(BV.SIZE,'SALMON ','')),MMR.size,siz.size) = SG.Size
LEFT JOIN Inventory_Sandbox.Public.Incremental_BuyBox BB
    ON ST.StockNumber = BB.StockNumber
LEFT JOIN INVENTORY_SANDBOX.PI7CALC_REFERENCE.STATES_SUPER_REGIONS_REF STATE
    ON BV.PICKUPLOCATIONSTATE = STATE.STATE
LEFT JOIN INVENTORY_SANDBOX.PI7CALC_REFERENCE.SUPER_REGIONS SR
    ON STATE.SUPER_REGION_ID = SR.SUPER_REGION_ID
LEFT JOIN INVENTORY_SANDBOX.STETSON_SANDBOX.KBB_GROUPS KG
    ON ifnull(BV.KBBVALUE,fv.kbb_value) BETWEEN KG.KBB_MIN AND KG.KBB_MAX
WHERE ST.STOCKNUMBER NOT ILIKE '2%%'
),

adpfinal as (
SELECT distinct
    S.*
    ,CASE WHEN sizegroup IN ('COMPACT','LARGE','MEDIUM') THEN 'CAR'
    WHEN sizegroup IN ('EURO','SPECIALTY','SPORTS') THEN 'SPECIALTY'
    WHEN sizegroup IN ('CROSSOVER','LARGE SUV','MEDIUM SUV','SMALL SUV','VAN') THEN 'SUV'
    WHEN sizegroup IN ('LARGE TRUCK','SMALL TRUCK') THEN 'TRUCK'  
    ELSE 'UNKNOWN' END AS SIZEGROUP2
    ,case when sizegroup2 = 'SUV' and sizegroup='MEDIUM SUV' and KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K','14K-16K') then 'SUV-MediumSUVSize-0K-16K KBB'
    when sizegroup2 = 'SUV' and (sizegroup= 'SMALL SUV' or sizegroup = 'CROSSOVER') and KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K') then 'SUV-SmallSUVSize-0K-14K KBB'
    when sizegroup2 = 'SUV' and (sizegroup= 'SMALL SUV' or sizegroup = 'CROSSOVER') and kbb_group in ('14K-16K','16K-18K','18K-20K','20K-22K','22K-99K') then 'SUV-SmallSUVSize-14K-99K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group in ('16K-18K','18K-20K','20K-22K') then 'SUV-MediumSUVSize-16K-22K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group in ('22K-99K') then 'SUV-MediumSUVSize-22K-99K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group is null then 'SUV-MediumSUVSize-22K-99K KBB'
    when (sizegroup2= 'CAR' and sizegroup= 'MEDIUM' OR sizegroup = 'EURO' OR SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN') and KBB_group in ('12K-14K','14K-16K','16K-18K') then 'CAR-AnySize-12K-18K KBB'
    when (sizegroup2= 'CAR' and sizegroup= 'MEDIUM' OR sizegroup = 'EURO' OR SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN') and KBB_group in ('18K-20K') then 'CAR-AnySize-18K-20K KBB'
    when (sizegroup2= 'CAR' and sizegroup= 'MEDIUM' OR sizegroup = 'EURO' OR SIZEGROUP='SPORTS-SPECIALTY' OR SIZEGROUP2='UNKNOWN') and KBB_group in ('20K-22K','22K-99K') then 'CAR-AnySize-20K-99K KBB'
    when (sizegroup2= 'CAR' OR SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and KBB_group in ('0K-8K','8K-10K','10K-12K') then 'CAR-AnySize-0K-12K KBB'
    when (sizegroup2= 'CAR' OR SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and KBB_group in ('12K-14K','14K-16K','16K-18K') then 'CAR-AnySize-12K-18K KBB'
    when (sizegroup2= 'CAR' OR SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and KBB_group in ('20K-22K','22K-99K') then 'CAR-AnySize-20K-99K KBB'
    when (sizegroup2= 'CAR' OR SIZEGROUP2='UNKNOWN' or SIZEGROUP2= 'SPECIALTY') and KBB_group in ('18K-20K') then 'CAR-AnySize-18K-20K KBB'
    when (sizegroup2= 'SUV' or sizegroup='VAN' or sizegroup='LARGE SUV') then 'SUV-LargeSUV-0K-99K KBB'
    when sizegroup2= 'TRUCK' then 'TRUCK-TruckSize-0K-99K KBB'
    when sizegroup2= 'SUV' and KBB_group is null then 'SUV-LargeSUV-0K-99K KBB'
    WHEN sizegroup2= 'CAR' AND KBB_GROUP IS NULL THEN 'CAR-AnySize-20K-99K KBB'
    when sizegroup = 'VAN' AND KBB_GROUP IS NULL THEN 'SUV-LargeSUV-0K-99K KBB'
    WHEN SIZEGROUP='COMPACT' AND KBB_GROUP IS NULL THEN 'CAR-AnySize-20K-99K KBB'
    WHEN SIZEGROUP2= 'UNKNOWN' THEN 'CAR-AnySize-20K-99K KBB'
    when sizegroup2='SPECIALTY' and kbb_group is null then 'CAR-AnySize-20K-99K KBB'
    end as DistroGroups
FROM STOCKS S
where acquisition_week >= '2025-01-01'
),

layaways as (
select distinct st.stocknumber
from INVENTORY.VEHICLE.STOCKTREND st
left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
    on st.currentcostcenterid=childcostcenterid
left join INVENTORY.TITLE.INFO_AVAILABILITY_TREND t
    on st.stocknumber=t.stock_number
    and st.asofdate= upload_date
where in_process_desc in ('Dealer','Holding Lot','Lot Repair')
and title_distro_ready='Unavailable' 
and title_location <> 'Dealership-Shipped'
and status_code= 'LA'
),

website_stock as (
SELECT distinct fv.stock_number as website_stocks
,upper(trim(ccd.PARENTCOSTCENTERDESC)) as ParentCostCenterDesc
,stat
,TO_DATE(E.event_date_time) as AsOfDate
from risk.affordability.ga2_pos_affordability E
LEFT JOIN risk.affordability.ga2_pos_affordability_financed_vehicle FV
    ON E.business_event_id = FV.business_event_id
left join INVENTORY.VEHICLE.STOCKTODAYACTIVE st on st.stknbr= fv.stock_number
left join inventory_sandbox.admdev.dbo_tblccdmapping ccd on ccd.crllt= st.clot
and E.event_name = 'ga2Affordability'
AND FV.stock_number NOT LIKE '2%%'
and stat= 'AV'

union all

SELECT distinct fv.stock_number as website_stocks
,upper(trim(ccd.PARENTCOSTCENTERDESC)) as ParentCostCenterDesc
,stat
,TO_DATE(E.event_date_time) as AsOfDate
from risk.affordability.ga2_pos_affordability E
LEFT JOIN risk.affordability.ga2_pos_affordability_financed_vehicle FV
    ON E.business_event_id = FV.business_event_id
left join INVENTORY.VEHICLE.STOCKTODAYACTIVE st on st.stknbr= fv.stock_number
left join inventory_sandbox.admdev.dbo_tblccdmapping ccd on ccd.crllt= st.clot
and E.event_name = 'posAffordability'
AND FV.stock_number NOT LIKE '2%%'
and childcostcenterdesc in ('MONTCLAIR', 'RIVERSIDE')
and stat= 'AV'
),

stocknextdate as (
    select stocknumber, asofdate,
        ifnull(lead(asofdate) over (partition by stocknumber order by asofdate), current_date()) as nextdate
    from (select distinct stocknumber, asofdate from INVENTORY.VEHICLE.STOCKTREND where stocknumber < 1990000000)
),

trendedfrontlines as (
select distinct st.stocknumber, st.asofdate, ccd.childcostcenterid, ccd.childcostcenterdesc, in_process_desc, ccd.parentcostcenterdesc
,snd.nextdate
,a.classmake, a.classmodel, distrogroups, SIZEGROUP, sourcingregion
,ifnull(mm.commonmodel,mm2.commonmodel) as commonmodel
,case when t.stock_number is not null and in_process_desc ilike 'Dealer' then 1 else 0 end as Frontline
,case when ws.website_stocks is not null then 1 else 0 end as websiteunit
,activedealerdays
,case when st.odometer < 40000 then '0-40000'
    when st.odometer between 40000 and 60000 then '40000-60000'
    when st.odometer between 60001 and 80000 then '60000-80000'
    when st.odometer between 80001 and 100000 then '80000-100000'
    when st.odometer between 100001 and 120000 then '100000-120000'
    when st.odometer between 120001 and 140000 then '120000-140000'
    when st.odometer between 140001 and 160000 then '140000-160000'
    when st.odometer > 160000 then '160000+'
    else 'UNKNOWN' end as Mileagebucket
from INVENTORY.VEHICLE.STOCKTREND st
inner join stocknextdate snd
    on st.stocknumber = snd.stocknumber
    and st.asofdate = snd.asofdate
left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
    on st.currentcostcenterid=childcostcenterid
left join 
(select stock_number, min(upload_date) as upload_Date
from INVENTORY.TITLE.INFO_AVAILABILITY_TREND t
where title_distro_ready ilike 'AVAILABLE'
group by stock_number) t
    on st.stocknumber=t.stock_number
    and st.asofdate::Date>=upload_date::Date
left join website_stock ws
    on st.stocknumber=ws.website_stocks
    and st.asofdate=ws.asofdate
left join adpfinal a
    on st.stocknumber=a.stocknumber
left join 
(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm
where iscurrent=1) mm
   on COALESCE(upper(a.commonmodel),UPPER(SPLIT_PART(A.CLASSMODEL, ' ', 1)),CONCAT('OTHER_',sizegroup))=upper(mm.commonmodel)
  AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'
    when MM.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else
    upper(MM.crlld) end=upper(ccd.parentcostcenterdesc)
left join 
(select* from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX mm
where iscurrent=1) mm2
   on CONCAT('OTHER_',case when sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE SIZEGROUP END)=upper(mm2.commonmodel)
  AND case when MM2.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'
    when MM2.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else
    upper(MM2.crlld) end=upper(ccd.parentcostcenterdesc)
left join RISK_SANDBOX.MKOURYADHOC.STOCKLEVELADP sl
    on st.stocknumber=sl.stocknumber
where st.stocknumber <1990000000
and st.stocknumber not in (select stocknumber from layaways)
and st.asofdate >= '2025-01-01'
)

select asofdate, parentcostcenterdesc, sourcingregion, commonmodel, Mileagebucket, DistroGroups, count(distinct stocknumber) as totaldupes
from trendedfrontlines
where in_process_desc ilike 'Dealer'
and Frontline >= 1
and asofdate = '{target_date}'
group by asofdate, parentcostcenterdesc, sourcingregion, commonmodel, Mileagebucket, DistroGroups
having count(distinct stocknumber) > 1
order by totaldupes desc
"""


@st.cache_data
def load_snapshot(target_date: str):
    meta = pd.read_parquet(os.path.join(DATA_DIR, "metadata.parquet"))
    meta_dict = dict(zip(meta["key"], meta["value"]))
    if target_date == meta_dict.get("prev_date"):
        return pd.read_parquet(os.path.join(DATA_DIR, "snapshot_prev.parquet"))
    return pd.read_parquet(os.path.join(DATA_DIR, "snapshot.parquet"))


@st.cache_data
def load_trends(start_date: str, end_date: str):
    return pd.read_parquet(os.path.join(DATA_DIR, "trends.parquet"))


@st.cache_data
def load_dupes(target_date: str):
    return pd.read_parquet(os.path.join(DATA_DIR, "dupes.parquet"))


DUPES_TREND_SQL = """
with  

sizes as (
select distinct 
size
,MAKE
,MODEL
from  REPLICATED.BUY.DBO_TBLMMRVEHICLEDESCRIPTION  mmr
LEFT JOIN inventory.vehicle.stock s
    On s.MMR_MID = TRY_TO_NUMBER(mmr.mmr_mid)
left join INVENTORY.BUY.FACTVEHICLE v
    on s.stocknumber=v.stocknumber
),

STOCKS AS (
SELECT
    SDD.WEEK_ENDING_SUNDAY AS ACQUISITION_WEEK
    , ST.STOCKNUMBER
    , SG.SIZE_GROUPS_EURO AS SIZEGROUP
    ,st.classmake
    ,st.classmodel
    ,siz.size
    , KG.KBB_GROUP
    ,mmr.commonmodel
FROM INVENTORY.VEHICLE.STOCK ST
LEFT JOIN SHARED.DIMENSION.DATE SDD
    ON SDD.CALENDAR_DATE = ST.ACQUISITIONDATE
LEFT JOIN INVENTORY.BUY.FACTVEHICLE FV
    ON FV.STOCKNUMBER = ST.STOCKNUMBER
LEFT JOIN INVENTORY.BUY.VEHICLE BV
    ON FV.BUYONIC_BUY_AUCTION_VEHICLE_ID = BV.BUYAUCTIONVEHICLEID
LEFT JOIN REPLICATED.BUY.DBO_TBLMMRVEHICLEDESCRIPTION mmr 
    ON ST.MMR_MID=MMR.MMR_MID
left join sizes siz
    on st.classmake=siz.make
    and st.classmodel=siz.model
LEFT JOIN RISK_SANDBOX.OROCKWOOD.SIZE_GROUPS SG
    ON coalesce(UPPER(REGEXP_REPLACE(BV.SIZE,'SALMON ','')),MMR.size,siz.size) = SG.Size
LEFT JOIN Inventory_Sandbox.Public.Incremental_BuyBox BB
    ON ST.StockNumber = BB.StockNumber
LEFT JOIN INVENTORY_SANDBOX.PI7CALC_REFERENCE.STATES_SUPER_REGIONS_REF STATE
    ON BV.PICKUPLOCATIONSTATE = STATE.STATE
LEFT JOIN INVENTORY_SANDBOX.PI7CALC_REFERENCE.SUPER_REGIONS SR
    ON STATE.SUPER_REGION_ID = SR.SUPER_REGION_ID
LEFT JOIN INVENTORY_SANDBOX.STETSON_SANDBOX.KBB_GROUPS KG
    ON ifnull(BV.KBBVALUE,fv.kbb_value) BETWEEN KG.KBB_MIN AND KG.KBB_MAX
WHERE ST.STOCKNUMBER NOT ILIKE '2%%'
),

adpfinal as (
SELECT distinct
    S.*
    ,CASE WHEN sizegroup IN ('COMPACT','LARGE','MEDIUM') THEN 'CAR'
    WHEN sizegroup IN ('EURO','SPECIALTY','SPORTS') THEN 'SPECIALTY'
    WHEN sizegroup IN ('CROSSOVER','LARGE SUV','MEDIUM SUV','SMALL SUV','VAN') THEN 'SUV'
    WHEN sizegroup IN ('LARGE TRUCK','SMALL TRUCK') THEN 'TRUCK'  
    ELSE 'UNKNOWN' END AS SIZEGROUP2
    ,case when sizegroup2 = 'SUV' and sizegroup='MEDIUM SUV' and KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K','14K-16K') then 'SUV-MediumSUVSize-0K-16K KBB'
    when sizegroup2 = 'SUV' and (sizegroup= 'SMALL SUV' or sizegroup = 'CROSSOVER') and KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K') then 'SUV-SmallSUVSize-0K-14K KBB'
    when sizegroup2 = 'SUV' and (sizegroup= 'SMALL SUV' or sizegroup = 'CROSSOVER') and kbb_group in ('14K-16K','16K-18K','18K-20K','20K-22K','22K-99K') then 'SUV-SmallSUVSize-14K-99K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group in ('16K-18K','18K-20K','20K-22K') then 'SUV-MediumSUVSize-16K-22K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group in ('22K-99K') then 'SUV-MediumSUVSize-22K-99K KBB'
    when sizegroup2= 'SUV' and sizegroup= 'MEDIUM SUV' and KBB_group is null then 'SUV-MediumSUVSize-22K-99K KBB'
    when sizegroup2= 'SUV' and sizegroup in ('LARGE SUV','VAN') then 'SUV-LargeSUVSize'
    when sizegroup2= 'SUV' and sizegroup= 'SMALL SUV' and KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K') then 'SUV-SmallSUVSize-0K-14K KBB'
    when sizegroup2= 'TRUCK' and sizegroup in ('SMALL TRUCK') then 'TRUCK-SmallTruckSize'
    when sizegroup2= 'TRUCK' and sizegroup in ('LARGE TRUCK') and KBB_group in ('0K-8K','8K-10K','10K-12K','12K-14K','14K-16K','16K-18K','18K-20K','20K-22K') then 'TRUCK-LargeTruckSize-0K-22K KBB'
    when sizegroup2= 'TRUCK' and sizegroup in ('LARGE TRUCK') and KBB_group in ('22K-99K') then 'TRUCK-LargeTruckSize-22K-99K KBB'
    when sizegroup2= 'TRUCK' and sizegroup in ('LARGE TRUCK') and KBB_group is null then 'TRUCK-LargeTruckSize-22K-99K KBB'
    when sizegroup2= 'CAR' and sizegroup in ('COMPACT') then 'CAR-CompactSize'
    when sizegroup2= 'CAR' and sizegroup in ('MEDIUM','LARGE') then 'CAR-MedLargeSize'
    when sizegroup2= 'SPECIALTY' then 'SPECIALTY'
    else 'UNKNOWN' end as distrogroups
FROM STOCKS S
where acquisition_week >= '2025-01-01'
),

trendedfrontlines as (
select distinct st.stocknumber, st.asofdate, ccd.parentcostcenterdesc
,sourcingregion
,a.classmake, a.classmodel, a.distrogroups
,ifnull(a.commonmodel, SPLIT_PART(a.classmodel, ' ', 1)) as commonmodel
,case when t.stock_number is not null and in_process_desc ilike 'Dealer' then 1 else 0 end as Frontline
,case when st.odometer < 40000 then '0-40000'
    when st.odometer between 40000 and 60000 then '40000-60000'
    when st.odometer between 60001 and 80000 then '60000-80000'
    when st.odometer between 80001 and 100000 then '80000-100000'
    when st.odometer between 100001 and 120000 then '100000-120000'
    when st.odometer between 120001 and 140000 then '120000-140000'
    when st.odometer between 140001 and 160000 then '140000-160000'
    when st.odometer > 160000 then '160000+'
    else 'UNKNOWN' end as Mileagebucket
from INVENTORY.VEHICLE.STOCKTREND st
left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
    on st.currentcostcenterid=childcostcenterid
left join 
(select stock_number, min(upload_date) as upload_Date
from INVENTORY.TITLE.INFO_AVAILABILITY_TREND t
where title_distro_ready ilike 'AVAILABLE'
group by stock_number) t
    on st.stocknumber=t.stock_number
    and st.asofdate::Date>=upload_date::Date
left join adpfinal a
    on st.stocknumber=a.stocknumber
where st.stocknumber < 1990000000
and st.asofdate between '{start_date}' and '{end_date}'
and upper(trim(ccd.parentcostcenterdesc)) = '{store}'
)

select asofdate, parentcostcenterdesc, sourcingregion, commonmodel, Mileagebucket, DistroGroups, count(distinct stocknumber) as totaldupes
from trendedfrontlines
where Frontline >= 1
and commonmodel = '{model}'
and Mileagebucket = '{mileage}'
and DistroGroups = '{distro}'
group by asofdate, parentcostcenterdesc, sourcingregion, commonmodel, Mileagebucket, DistroGroups
order by asofdate
"""


@st.cache_data
def load_dupes_trend(start_date: str, end_date: str, store: str, model: str, mileage: str, distro: str):
    # Load saved trend data (only available for pre-saved combinations)
    path = os.path.join(DATA_DIR, "dupes_trend.parquet")
    if os.path.exists(path):
        df = pd.read_parquet(path)
        if not df.empty:
            df.columns = [c.lower() for c in df.columns]
            # Filter to the requested combination
            mask = (
                (df["parentcostcenterdesc"] == store) &
                (df["commonmodel"] == model) &
                (df["mileagebucket"] == mileage) &
                (df["distrogroups"] == distro)
            )
            return df[mask]
    return pd.DataFrame()


def main():
    st.title("Frontline Health Dashboard")

    # --- Sidebar ---
    st.sidebar.header("Filters")
    st.sidebar.info("📊 Presentation Mode — using saved data")

    if st.sidebar.button("Clear Cache & Reload"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            if key.startswith("processed_df_"):
                del st.session_state[key]
        st.rerun()

    # Load metadata for frozen dates
    meta = pd.read_parquet(os.path.join(DATA_DIR, "metadata.parquet"))
    meta_dict = dict(zip(meta["key"], meta["value"]))
    target_date_str = meta_dict["snapshot_date"]
    prev_date_str = meta_dict["prev_date"]
    snapshot_date = pd.to_datetime(target_date_str).date()
    prev_date = pd.to_datetime(prev_date_str).date()

    st.sidebar.text(f"Snapshot Date: {target_date_str}")

    # Load from local files
    df = load_snapshot(target_date_str)

    if df.empty:
        st.warning("No data returned for the selected date. Try a different date.")
        return

    show_deltas = st.sidebar.checkbox(f"Show vs Prior Week deltas ({prev_date.strftime('%m/%d')})", value=False)
    if show_deltas:
        df_prev = load_snapshot(prev_date_str)
    else:
        df_prev = pd.DataFrame()

    # Lowercase columns and deduplicate (SQL has finalmerchmix twice)
    df.columns = [c.lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    # Preprocess previous week data
    if not df_prev.empty:
        df_prev.columns = [c.lower() for c in df_prev.columns]
        df_prev = df_prev.loc[:, ~df_prev.columns.duplicated()]
        closed_prev = ["COLUMBIA MISSOURI", "COLUMBIA-MISSOURI", "ESCONDIDO", "FT PIERCE", "NEW CIRCLE ROAD", "VAN NUYS"]
        df_prev = df_prev[~df_prev["parentcostcenterdesc"].str.upper().str.strip().isin(closed_prev)]
        for col in ["frontline", "websiteunit", "lotrepair", "holdinglot", "layaway", "allocations", "last7dayssales", "dealeroptimum"]:
            if col in df_prev.columns:
                df_prev[col] = pd.to_numeric(df_prev[col], errors="coerce")

    # Preprocess full dataframe (cached in session_state to avoid recomputing on filter change)
    closed_stores = ["COLUMBIA MISSOURI", "COLUMBIA-MISSOURI", "ESCONDIDO", "FT PIERCE", "NEW CIRCLE ROAD", "VAN NUYS"]
    cache_key = f"processed_df_{target_date_str}"
    if cache_key not in st.session_state:
        # Exclude closed stores
        df = df[~df["parentcostcenterdesc"].str.upper().str.strip().isin(closed_stores)]

        # Numeric columns - coerce
        numeric_cols = [
            "frontline", "websiteunit", "last7daysfrontline", "last7daysfresh", "holdinglot", "allocations",
            "lotrepair", "layaway", "today", "day1", "day2", "day3", "day4",
            "day5", "day6", "dealeroptimum", "holdingoptimum", "dealercapacity",
            "holdinglotcapacity", "lts", "lts_budget",
            "sales", "last7dayssales", "storetotalfrontlineinventory", "avgdealerdays",
            "prefrontlineprocess", "prefrontlineprocessstock", "finalmerchmix",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        st.session_state[cache_key] = df
    else:
        df = st.session_state[cache_key]

    # --- Sidebar Filters ---
    regions = sorted(df["sourcingregion"].dropna().unique())
    selected_region = st.sidebar.selectbox("Sourcing Region", ["All"] + regions)

    if selected_region == "All":
        stores_df = df
    else:
        stores_df = df[df["sourcingregion"] == selected_region]

    stores = sorted(stores_df["parentcostcenterdesc"].dropna().unique())
    selected_store = st.sidebar.selectbox("Store (Parent Cost Center)", ["All"] + stores)

    # Apply filters
    df_filtered = df.copy()
    if selected_region != "All":
        df_filtered = df_filtered[df_filtered["sourcingregion"] == selected_region]
    if selected_store != "All":
        df_filtered = df_filtered[df_filtered["parentcostcenterdesc"] == selected_store]

    # Compute prior week deltas using the SAME filters
    prev_totals = {}
    if not df_prev.empty:
        df_prev_filtered = df_prev.copy()
        if selected_region != "All":
            df_prev_filtered = df_prev_filtered[df_prev_filtered["sourcingregion"] == selected_region]
        if selected_store != "All":
            df_prev_filtered = df_prev_filtered[df_prev_filtered["parentcostcenterdesc"] == selected_store]
        for col in ["frontline", "websiteunit", "lotrepair", "holdinglot", "layaway", "allocations", "last7dayssales", "dealeroptimum"]:
            if col in df_prev_filtered.columns:
                prev_totals[col] = df_prev_filtered[col].sum()

    # Ensure expected columns exist (some may be removed from SQL)
    for col in ["last7daysfresh", "lts", "lts_budget"]:
        if col not in df_filtered.columns:
            df_filtered[col] = pd.NA

    # --- Aggregate store-level metrics ---
    # Get store optimums from full df (they only exist on specific rows, may be lost when filtering)
    store_optimums = (
        df.groupby("parentcostcenterdesc")
        .agg(
            dealeroptimum=("dealeroptimum", "max"),
            holdingoptimum=("holdingoptimum", "max"),
            dealercapacity=("dealercapacity", "max"),
            holdinglotcapacity=("holdinglotcapacity", "max"),
        )
        .reset_index()
    )

    # Sum directly per store - matches SELECT SUM(col) ... GROUP BY parentcostcenterdesc in Snowflake
    store_summary = (
        df_filtered.groupby("parentcostcenterdesc")
        .agg(
            sourcingregion=("sourcingregion", "first"),
            frontline=("frontline", "sum"),
            websiteunit=("websiteunit", "sum"),
            last7daysfrontline=("last7daysfrontline", "sum"),
            last7daysfresh=("last7daysfresh", "sum"),
            holdinglot=("holdinglot", "sum"),
            allocations=("allocations", "sum"),
            lotrepair=("lotrepair", "sum"),
            layaway=("layaway", "sum"),
            lts=("lts", "mean"),
            lts_budget=("lts_budget", "mean"),
            sales=("sales", "max"),
            last7dayssales=("last7dayssales", "sum"),
            avgdealerdays=("avgdealerdays", "mean"),
            prefrontlineprocess=("prefrontlineprocess", "max"),
            prefrontlineprocessstock=("prefrontlineprocessstock", "sum"),
            prefrontlineprocessextrarepair=("prefrontlineprocessextrarepair", "sum"),
            emissionsreup=("emissionsreup", "sum"),
            storetotalfrontlineinventory=("storetotalfrontlineinventory", "max"),
            today=("today", "sum"),
            day1=("day1", "sum"),
            day2=("day2", "sum"),
            day3=("day3", "sum"),
            day4=("day4", "sum"),
            day5=("day5", "sum"),
            day6=("day6", "sum"),
        )
        .reset_index()
    )
    # Merge optimums from full dataset
    store_summary = store_summary.merge(store_optimums, on="parentcostcenterdesc", how="left")

    # Ensure numeric types after aggregation
    for col in ["frontline", "dealeroptimum", "holdingoptimum", "lotrepair", "last7dayssales", "layaway", "storetotalfrontlineinventory"]:
        if col in store_summary.columns:
            store_summary[col] = pd.to_numeric(store_summary[col], errors="coerce")

    # 7-day forecast sales sum
    forecast_cols = ["today", "day1", "day2", "day3", "day4", "day5", "day6"]
    store_summary["forecast_7d_sales"] = store_summary[forecast_cols].sum(axis=1)

    # Derived metrics
    store_summary["pct_optimum"] = store_summary.apply(
        lambda r: (
            (r["frontline"] + r["holdinglot"] + r["lotrepair"] + r["layaway"])
            / ((r["dealeroptimum"] + r["holdingoptimum"]) or pd.NA) * 100
        ) if r["prefrontlineprocess"] == 1 else (
            (r["frontline"] + r["lotrepair"] + r["layaway"])
            / (r["dealeroptimum"] or pd.NA) * 100
        ) if r["dealeroptimum"] > 0 else 0,
        axis=1
    ).fillna(0).astype(float)

    store_summary["pct_lot_sold_7d"] = pd.to_numeric(
        store_summary["last7dayssales"] / store_summary["last7daysfrontline"].replace(0, pd.NA) * 100,
        errors="coerce"
    )

    store_summary["pct_fresh_7d"] = pd.to_numeric(
        store_summary["last7daysfresh"] / store_summary["last7daysfrontline"].replace(0, pd.NA) * 100,
        errors="coerce"
    )

    store_summary["pct_lot_repair"] = pd.to_numeric(
        (store_summary["lotrepair"] - store_summary["prefrontlineprocessstock"].fillna(0)) / (store_summary["frontline"] + store_summary["lotrepair"]).replace(0, pd.NA) * 100,
        errors="coerce"
    )

    # Distinct models (only where frontline > 0, exclude nulls)
    models_data = (
        df_filtered[(df_filtered["frontline"] > 0) & (df_filtered["commonmodel"].notna())]
        .groupby("parentcostcenterdesc")["commonmodel"]
        .nunique()
        .reset_index()
        .rename(columns={"commonmodel": "distinct_models"})
    )
    store_summary = store_summary.merge(models_data, on="parentcostcenterdesc", how="left")
    store_summary["distinct_models"] = store_summary["distinct_models"].fillna(0).astype(int)
    store_summary["pct_model_diversity"] = store_summary.apply(
        lambda r: (r["distinct_models"] / r["frontline"] * 100) if r["frontline"] > 0 else 0, axis=1
    )

    # Distinct distro groups (categories) per store
    categories_data = (
        df_filtered[(df_filtered["frontline"] > 0)]
        .groupby("parentcostcenterdesc")
        .agg(distinct_categories=("commonmodel", "nunique"))
        .reset_index()
    )
    store_summary = store_summary.merge(categories_data, on="parentcostcenterdesc", how="left")
    store_summary["distinct_categories"] = store_summary["distinct_categories"].fillna(0).astype(int)

    # Network-wide unique models
    network_unique_models = df_filtered[
        (df_filtered["frontline"] > 0) & (df_filtered["commonmodel"].notna())
    ]["commonmodel"].nunique()

    # =====================================================================
    # TOP SECTION: Yesterday's Information (Network KPIs)
    # =====================================================================
    st.header(f"Yesterday's Snapshot - {snapshot_date.strftime('%B %d, %Y')}")

    total_dealer_optimum = store_summary["dealeroptimum"].fillna(0).sum()
    total_lotrepair = df_filtered["lotrepair"].sum()
    # 7d sales: one value per store from the daily_sales UNION - deduplicate before summing
    sales_by_store = df_filtered[df_filtered["last7dayssales"].notna()].drop_duplicates(subset=["parentcostcenterdesc"])[["parentcostcenterdesc", "last7dayssales"]]
    total_7d_sales = sales_by_store["last7dayssales"].sum()
    total_7d_frontline = store_summary["last7daysfrontline"].sum()
    pct_lot_sold_7d = (total_7d_sales / total_7d_frontline * 100) if total_7d_frontline > 0 else 0
    avg_dealer_days = store_summary["avgdealerdays"].mean()

    total_website = df_filtered["websiteunit"].sum()
    total_holdinglot = int(store_summary["holdinglot"].fillna(0).sum())
    total_layaway = int(store_summary["layaway"].fillna(0).sum())
    total_allocations = int(store_summary["allocations"].fillna(0).sum())
    total_frontline = total_website + total_lotrepair + total_layaway
    overall_pct_optimum = (total_frontline / total_dealer_optimum * 100) if total_dealer_optimum > 0 else 0
    overall_pct_lot_repair = (total_lotrepair / (total_frontline + total_lotrepair) * 100) if (total_frontline + total_lotrepair) > 0 else 0

    # Optimum calculations
    website_optimum = (total_dealer_optimum / 35) * 30
    lotrepair_optimum = (total_dealer_optimum / 35) * 4
    holdinglot_optimum = int(store_summary["holdingoptimum"].fillna(0).sum()) if "holdingoptimum" in store_summary.columns else 0
    layaway_optimum = (total_dealer_optimum / 35) * 1

    # % to optimum for each category
    pct_website_optimum = (total_website / website_optimum * 100) if website_optimum > 0 else 0
    pct_lotrepair_optimum = (total_lotrepair / lotrepair_optimum * 100) if lotrepair_optimum > 0 else 0
    pct_holdinglot_optimum = (total_holdinglot / holdinglot_optimum * 100) if holdinglot_optimum > 0 else 0
    pct_layaway_optimum = (total_layaway / layaway_optimum * 100) if layaway_optimum > 0 else 0

    # Compute deltas vs previous day
    prev_website = prev_totals.get("websiteunit", 0)
    prev_lotrepair = prev_totals.get("lotrepair", 0)
    prev_holdinglot = prev_totals.get("holdinglot", 0)
    prev_layaway = prev_totals.get("layaway", 0)
    prev_frontline = prev_website + prev_lotrepair + prev_layaway
    prev_dealer_optimum = prev_totals.get("dealeroptimum", 0)

    delta_frontline = int(total_frontline - prev_frontline) if prev_frontline else None
    delta_website = int(total_website - prev_website) if prev_website else None
    delta_lotrepair = int(total_lotrepair - prev_lotrepair) if prev_lotrepair else None
    delta_holdinglot = int(total_holdinglot - prev_holdinglot) if prev_holdinglot else None
    delta_layaway = int(total_layaway - prev_layaway) if prev_layaway else None

    # Row 1: Frontline / Delta / Dealer Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Total Frontline Units", f"{int(total_frontline):,}")
    c2.metric("vs Prior Week", f"{delta_frontline:+,}" if delta_frontline is not None else "N/A", delta=f"{delta_frontline:+,}" if delta_frontline is not None else None)
    c3.metric("Total Dealer Optimum", f"{int(total_dealer_optimum):,}")
    c4.metric("% to Optimum", f"{overall_pct_optimum:.1f}%")

    # Row 2: Website / Delta / Website Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Website Units", f"{int(total_website):,}")
    c2.metric("vs Prior Week", f"{delta_website:+,}" if delta_website is not None else "N/A", delta=f"{delta_website:+,}" if delta_website is not None else None)
    c3.metric("Website Optimum", f"{int(website_optimum):,}")
    c4.metric("% to Optimum", f"{pct_website_optimum:.1f}%")

    # Row 3: Lot Repair / Delta / LR Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Lot Repair Units", f"{int(total_lotrepair):,}")
    c2.metric("vs Prior Week", f"{delta_lotrepair:+,}" if delta_lotrepair is not None else "N/A", delta=f"{delta_lotrepair:+,}" if delta_lotrepair is not None else None, delta_color="inverse")
    c3.metric("Lot Repair Optimum", f"{int(lotrepair_optimum):,}")
    c4.metric("% to Optimum", f"{pct_lotrepair_optimum:.1f}%")

    # Row 4: Layaways / Delta / Layaway Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Layaways", f"{int(total_layaway):,}")
    c2.metric("vs Prior Week", f"{delta_layaway:+,}" if delta_layaway is not None else "N/A", delta=f"{delta_layaway:+,}" if delta_layaway is not None else None)
    c3.metric("Layaway Optimum", f"{int(layaway_optimum):,}")
    c4.metric("% to Optimum", f"{pct_layaway_optimum:.1f}%")

    # Row 5: Holding Lot / Delta
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Holding Lot Units", f"{int(total_holdinglot):,}")
    c2.metric("vs Prior Week", f"{delta_holdinglot:+,}" if delta_holdinglot is not None else "N/A", delta=f"{delta_holdinglot:+,}" if delta_holdinglot is not None else None, delta_color="inverse")
    c3.write("")
    c4.write("")

    # Row 6: Allocations / Delta
    prev_allocations = prev_totals.get("allocations", 0)
    delta_allocations = int(total_allocations - prev_allocations) if prev_allocations else None
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Allocations", f"{int(total_allocations):,}")
    c2.metric("vs Prior Week", f"{delta_allocations:+,}" if delta_allocations is not None else "N/A", delta=f"{delta_allocations:+,}" if delta_allocations is not None else None)
    c3.write("")
    c4.write("")

    st.divider()

    # Frontline Turn Metrics
    st.subheader("Frontline Turn Metrics")
    c1, c2, c3 = st.columns(3)
    c1.metric("% Lot Sold (7d)", f"{pct_lot_sold_7d:.1f}%")
    c2.metric("Avg Dealer Days", f"{avg_dealer_days:.1f}" if pd.notna(avg_dealer_days) else "N/A")
    c3.metric("7-Day Net Sales", f"{int(total_7d_sales):,}")

    st.divider()

    # =====================================================================
    # STORE RANKINGS - Top 10 Needing Most Work
    # =====================================================================
    st.header("Top 10 Stores Needing Attention")

    pfp_filter = st.selectbox(
        "Store Type",
        ["All", "Prefrontline Process", "Non-Prefrontline Process"],
        key="pfp_filter",
    )
    if pfp_filter == "Prefrontline Process":
        ranking_df = store_summary[store_summary["prefrontlineprocess"] == 1]
    elif pfp_filter == "Non-Prefrontline Process":
        ranking_df = store_summary[store_summary["prefrontlineprocess"] != 1]
    else:
        ranking_df = store_summary.copy()

    tab_view = st.radio("View", ["Frontline Health", "Frontline Saturation"], horizontal=True)

    if tab_view == "Frontline Health":
        tab1, tab2, tab5, tab4, tab6 = st.tabs([
            "Lowest % to Optimum",
            "Lowest Website Units",
            "Lowest % Lot Sold (7d)",
            "Highest % Lot Repair",
            "Highest Avg Dealer Days",
        ])
        tab8 = tab3 = tab10 = tab9 = None
    else:
        tab3, tab8, tab10, tab9 = st.tabs([
            "Least Model Diversity",
            "Store/Model Detail",
            "Store Deviation",
            "Top Model by Store",
        ])
        tab1 = tab2 = tab5 = tab4 = tab6 = None

    if tab1:
      with tab1:
        st.caption("Stores with the lowest frontline inventory relative to their dealer optimum target — these need the most units.")
        worst_optimum = (
            ranking_df[ranking_df["dealeroptimum"] > 0]
            .nsmallest(10, "pct_optimum")[
                ["parentcostcenterdesc", "sourcingregion", "prefrontlineprocess", "frontline", "websiteunit", "holdinglot", "lotrepair", "layaway", "allocations", "dealeroptimum", "holdingoptimum", "pct_optimum"]
            ]
            .reset_index(drop=True)
        )
        worst_optimum.index += 1
        worst_optimum.columns = ["Store", "Region", "PFP", "Frontline", "Website Units", "Holding Lot", "Lot Repair", "Layaway", "Allocations", "Dealer Optimum", "Holding Lot Optimum", "% to Optimum"]
        worst_optimum["PFP"] = worst_optimum["PFP"].fillna(0).astype(int)
        worst_optimum["Allocations"] = worst_optimum["Allocations"].fillna(0).astype(int)
        worst_optimum["% to Optimum"] = worst_optimum["% to Optimum"].round(1)
        st.dataframe(worst_optimum, use_container_width=True, column_config={"% to Optimum": st.column_config.NumberColumn(format="%.1f%%")})
        # Region aggregates
        region_agg = ranking_df.groupby("sourcingregion").agg(
            frontline=("frontline", "sum"), websiteunit=("websiteunit", "sum"),
            holdinglot=("holdinglot", "sum"), lotrepair=("lotrepair", "sum"),
            layaway=("layaway", "sum"), allocations=("allocations", "sum"),
            dealeroptimum=("dealeroptimum", "sum"),
            holdingoptimum=("holdingoptimum", "sum")
        ).reset_index()
        region_agg["pct_optimum"] = ((region_agg["frontline"] + region_agg["holdinglot"] + region_agg["lotrepair"] + region_agg["layaway"]) / region_agg["dealeroptimum"].replace(0, pd.NA) * 100).fillna(0)
        region_display = pd.DataFrame({
            "Region": region_agg["sourcingregion"],
            "Frontline": region_agg["frontline"].astype(int), "Website Units": region_agg["websiteunit"].astype(int),
            "Holding Lot": region_agg["holdinglot"].astype(int), "Lot Repair": region_agg["lotrepair"].astype(int),
            "Layaway": region_agg["layaway"].astype(int), "Allocations": region_agg["allocations"].fillna(0).astype(int),
            "Dealer Optimum": region_agg["dealeroptimum"].astype(int),
            "Holding Lot Optimum": region_agg["holdingoptimum"].astype(int),
            "% to Optimum": region_agg["pct_optimum"].round(1)
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True, column_config={"% to Optimum": st.column_config.NumberColumn(format="%.1f%%")})

    if tab3:
      with tab3:
        st.caption("Stores with the fewest distinct models on the frontline relative to their total frontline count.")
        least_diverse = (
            ranking_df[ranking_df["frontline"] > 0]
            .nsmallest(10, "pct_model_diversity")[
                ["parentcostcenterdesc", "sourcingregion", "prefrontlineprocess", "distinct_models", "frontline", "pct_model_diversity"]
            ]
            .reset_index(drop=True)
        )
        least_diverse.index += 1
        least_diverse.columns = ["Store", "Region", "PFP", "Distinct Models", "Frontline", "% Model Diversity"]
        least_diverse["PFP"] = least_diverse["PFP"].fillna(0).astype(int)
        least_diverse["% Model Diversity"] = least_diverse["% Model Diversity"].round(1)
        st.dataframe(least_diverse, use_container_width=True, column_config={"% Model Diversity": st.column_config.NumberColumn(format="%.1f%%")})
        # Region aggregates
        region_models = df_filtered[(df_filtered["frontline"] > 0) & (df_filtered["commonmodel"].notna())].groupby("sourcingregion")["commonmodel"].nunique().reset_index(name="distinct_models")
        region_fl = ranking_df.groupby("sourcingregion")["frontline"].sum().reset_index()
        region_div = region_models.merge(region_fl, on="sourcingregion")
        region_div["pct"] = (region_div["distinct_models"] / region_div["frontline"].replace(0, pd.NA) * 100).fillna(0)
        region_display = pd.DataFrame({
            "Region": region_div["sourcingregion"],
            "Distinct Models": region_div["distinct_models"].astype(int),
            "Frontline": region_div["frontline"].astype(int),
            "% Model Diversity": region_div["pct"].round(1)
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True, column_config={"% Model Diversity": st.column_config.NumberColumn(format="%.1f%%")})

    if tab4:
      with tab4:
        st.caption("Stores with the highest percentage of inventory in lot repair vs total frontline + lot repair.")
        worst_repair = (
            ranking_df[ranking_df["pct_lot_repair"].notna()]
            .nlargest(10, "pct_lot_repair")[
                ["parentcostcenterdesc", "sourcingregion", "lotrepair", "prefrontlineprocessstock", "prefrontlineprocessextrarepair", "emissionsreup", "frontline", "pct_lot_repair"]
            ]
            .reset_index(drop=True)
        )
        worst_repair.index += 1
        worst_repair.columns = ["Store", "Region", "Lot Repair", "PFP Stock", "PFP Extra Repair", "Emissions ReUp", "Frontline", "% in Lot Repair"]
        worst_repair["PFP Stock"] = worst_repair["PFP Stock"].fillna(0).astype(int)
        worst_repair["PFP Extra Repair"] = worst_repair["PFP Extra Repair"].fillna(0).astype(int)
        worst_repair["Emissions ReUp"] = worst_repair["Emissions ReUp"].fillna(0).astype(int)
        worst_repair["Lot Repair"] = worst_repair["Lot Repair"].fillna(0).astype(int)
        worst_repair["VehicleRepair"] = worst_repair["Lot Repair"] - worst_repair["PFP Stock"] - worst_repair["PFP Extra Repair"] - worst_repair["Emissions ReUp"]
        worst_repair["% in Lot Repair"] = worst_repair["% in Lot Repair"].round(1)
        worst_repair = worst_repair[["Store", "Region", "Lot Repair", "PFP Stock", "PFP Extra Repair", "Emissions ReUp", "VehicleRepair", "Frontline", "% in Lot Repair"]]
        st.dataframe(worst_repair, use_container_width=True, column_config={"% in Lot Repair": st.column_config.NumberColumn(format="%.1f%%")})
        # Company aggregate
        co_lr = ranking_df["lotrepair"].sum()
        co_pfp = ranking_df["prefrontlineprocessstock"].fillna(0).sum()
        co_fl = ranking_df["frontline"].sum()
        co_lr_adj = co_lr - co_pfp
        co_pct_lr = (co_lr_adj / (co_fl + co_lr) * 100) if (co_fl + co_lr) > 0 else 0
        company_row = pd.DataFrame([{
            "Store": "COMPANY TOTAL", "Region": "", "PFP": "",
            "Lot Repair Units": int(co_lr_adj), "Emissions Stock": int(co_pfp),
            "Frontline": int(co_fl), "% in Lot Repair": f"{co_pct_lr:.1f}%"
        }])
        st.dataframe(company_row, use_container_width=True, hide_index=True)
        # Region aggregates
        region_lr = ranking_df.groupby("sourcingregion").agg(
            lotrepair=("lotrepair", "sum"), prefrontlineprocessstock=("prefrontlineprocessstock", "sum"),
            frontline=("frontline", "sum")
        ).reset_index()
        region_lr["prefrontlineprocessstock"] = region_lr["prefrontlineprocessstock"].fillna(0)
        region_lr["lr_adj"] = region_lr["lotrepair"] - region_lr["prefrontlineprocessstock"]
        region_lr["pct"] = (region_lr["lr_adj"] / (region_lr["frontline"] + region_lr["lotrepair"]).replace(0, pd.NA) * 100).fillna(0)
        region_display = pd.DataFrame({
            "Region": region_lr["sourcingregion"],
            "Lot Repair Units": region_lr["lr_adj"].astype(int),
            "Emissions Stock": region_lr["prefrontlineprocessstock"].astype(int),
            "Frontline": region_lr["frontline"].astype(int),
            "% in Lot Repair": region_lr["pct"].round(1)
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True, column_config={"% in Lot Repair": st.column_config.NumberColumn(format="%.1f%%")})

    if tab5:
      with tab5:
        st.caption("Stores with the lowest percentage of their frontline inventory sold over the last 7 days.")
        worst_sold = (
            ranking_df[ranking_df["frontline"] > 0]
            .nsmallest(10, "pct_lot_sold_7d")[
                ["parentcostcenterdesc", "sourcingregion", "prefrontlineprocess", "last7dayssales", "last7daysfrontline", "pct_lot_sold_7d"]
            ]
            .reset_index(drop=True)
        )
        worst_sold.index += 1
        worst_sold.columns = ["Store", "Region", "PFP", "7d Net Sales", "Frontline Last 7 Days", "% Lot Sold (7d)"]
        worst_sold["PFP"] = worst_sold["PFP"].fillna(0).astype(int)
        worst_sold["% Lot Sold (7d)"] = worst_sold["% Lot Sold (7d)"].round(1)
        st.dataframe(worst_sold, use_container_width=True, column_config={"% Lot Sold (7d)": st.column_config.NumberColumn(format="%.1f%%")})
        # Company aggregate
        co_sales = ranking_df["last7dayssales"].sum()
        co_fl7 = ranking_df["last7daysfrontline"].sum()
        co_pct_sold = (co_sales / co_fl7 * 100) if co_fl7 > 0 else 0
        company_row = pd.DataFrame([{
            "Store": "COMPANY TOTAL", "Region": "", "PFP": "",
            "7d Net Sales": int(co_sales), "Frontline Last 7 Days": int(co_fl7),
            "% Lot Sold (7d)": f"{co_pct_sold:.1f}%"
        }])
        st.dataframe(company_row, use_container_width=True, hide_index=True)
        # Region aggregates
        region_sold = ranking_df.groupby("sourcingregion").agg(
            last7dayssales=("last7dayssales", "sum"), last7daysfrontline=("last7daysfrontline", "sum")
        ).reset_index()
        region_sold["pct_sold"] = (region_sold["last7dayssales"] / region_sold["last7daysfrontline"].replace(0, pd.NA) * 100).fillna(0)
        region_display = pd.DataFrame({
            "Region": region_sold["sourcingregion"],
            "7d Net Sales": region_sold["last7dayssales"].astype(int),
            "Frontline Last 7 Days": region_sold["last7daysfrontline"].astype(int),
            "% Lot Sold (7d)": region_sold["pct_sold"].round(1)
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True, column_config={"% Lot Sold (7d)": st.column_config.NumberColumn(format="%.1f%%")})

    if tab6:
      with tab6:
        st.caption("Stores where frontline vehicles have been sitting the longest on average (highest average active dealer days).")
        highest_days = (
            ranking_df[ranking_df["avgdealerdays"].notna() & (ranking_df["frontline"] > 0)]
            .nlargest(10, "avgdealerdays")[
                ["parentcostcenterdesc", "sourcingregion", "prefrontlineprocess", "avgdealerdays", "frontline"]
            ]
            .reset_index(drop=True)
        )
        highest_days.index += 1
        highest_days.columns = ["Store", "Region", "PFP", "Avg Dealer Days", "Frontline"]
        highest_days["PFP"] = highest_days["PFP"].fillna(0).astype(int)
        highest_days["Avg Dealer Days"] = highest_days["Avg Dealer Days"].round(1)
        st.dataframe(highest_days, use_container_width=True)
        # Company aggregate
        co_avg_days = ranking_df.loc[ranking_df["frontline"] > 0, "avgdealerdays"].mean()
        co_fl = ranking_df["frontline"].sum()
        company_row = pd.DataFrame([{
            "Store": "COMPANY AVG", "Region": "", "PFP": "",
            "Avg Dealer Days": round(co_avg_days, 1), "Frontline": int(co_fl)
        }])
        st.dataframe(company_row, use_container_width=True, hide_index=True)
        # Region aggregates
        region_days = ranking_df[ranking_df["frontline"] > 0].groupby("sourcingregion").agg(
            avgdealerdays=("avgdealerdays", "mean"), frontline=("frontline", "sum")
        ).reset_index()
        region_display = pd.DataFrame({
            "Region": region_days["sourcingregion"],
            "Avg Dealer Days": region_days["avgdealerdays"].round(1),
            "Frontline": region_days["frontline"].astype(int)
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True)

    if tab2:
      with tab2:
        st.caption("Stores with the fewest units currently listed and available on the website.")
        lowest_website = (
            ranking_df.nsmallest(10, "websiteunit")[
                ["parentcostcenterdesc", "sourcingregion", "prefrontlineprocess", "websiteunit"]
            ]
            .reset_index(drop=True)
        )
        lowest_website.index += 1
        lowest_website.columns = ["Store", "Region", "PFP", "Website Units"]
        lowest_website["PFP"] = lowest_website["PFP"].fillna(0).astype(int)
        st.dataframe(lowest_website, use_container_width=True)
        # Company aggregate
        co_ws = ranking_df["websiteunit"].sum()
        company_row = pd.DataFrame([{
            "Store": "COMPANY TOTAL", "Region": "", "PFP": "",
            "Website Units": int(co_ws)
        }])
        st.dataframe(company_row, use_container_width=True, hide_index=True)
        # Region aggregates
        region_ws = ranking_df.groupby("sourcingregion")["websiteunit"].sum().reset_index()
        region_display = pd.DataFrame({
            "Region": region_ws["sourcingregion"],
            "Website Units": region_ws["websiteunit"].astype(int)
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True)

    if tab8:
      with tab8:
        st.caption("Every store/model combination with frontline count, % of store frontline, merch mix target, and over/under vs target. Includes 0-unit models with targets.")
        model_detail = (
            df_filtered[
                (df_filtered["frontline"] > 0)
                | (df_filtered["finalmerchmix"].notna() & (pd.to_numeric(df_filtered["finalmerchmix"], errors="coerce") > 0))
            ]
            .groupby(["parentcostcenterdesc", "commonmodel"])
            .agg(
                sourcingregion=("sourcingregion", "first"),
                frontline=("frontline", "sum"),
                finalmerchmix=("finalmerchmix", "first"),
            )
            .reset_index()
            .sort_values(["parentcostcenterdesc", "commonmodel"])
            .reset_index(drop=True)
        )
        model_detail["frontline"] = model_detail["frontline"].fillna(0)
        # Remove rows where both frontline is 0 and target is 0
        model_detail["finalmerchmix_num"] = pd.to_numeric(model_detail["finalmerchmix"], errors="coerce")
        model_detail = model_detail[~((model_detail["frontline"] == 0) & (model_detail["finalmerchmix_num"] == 0))]
        model_detail = model_detail.drop(columns=["finalmerchmix_num"])
        # Add store total frontline and % of frontline
        store_totals = model_detail.groupby("parentcostcenterdesc")["frontline"].transform("sum")
        model_detail["store_total_frontline"] = store_totals
        model_detail["pct_of_frontline"] = (model_detail["frontline"] / store_totals * 100).round(1)
        model_detail["finalmerchmix_pct"] = pd.to_numeric(model_detail["finalmerchmix"], errors="coerce") * 100
        model_detail["over_under"] = (model_detail["pct_of_frontline"] - model_detail["finalmerchmix_pct"]).round(1)
        model_detail = model_detail.sort_values("pct_of_frontline", ascending=False).reset_index(drop=True)
        model_detail_display = model_detail[["parentcostcenterdesc", "commonmodel", "frontline", "store_total_frontline", "pct_of_frontline", "finalmerchmix_pct", "over_under"]].copy()
        model_detail_display.index += 1
        model_detail_display.columns = ["Store", "Model", "Frontline", "Store Total", "% of Frontline", "Merch Mix Target", "Over/Under (FL)"]

        # Summary: instances over 10% vs total
        total_instances = len(model_detail)
        over_10_instances = (model_detail["pct_of_frontline"] > 10).sum()
        over_15_instances = (model_detail["pct_of_frontline"] > 15).sum()
        over_20_instances = (model_detail["pct_of_frontline"] > 20).sum()
        over_mix_10 = (model_detail["pct_of_frontline"] > (model_detail["finalmerchmix_pct"] + 10)).sum()
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Store/Model Combos", f"{total_instances:,}")
        c2.metric("Over 10%", f"{over_10_instances:,}")
        c3.metric("Over 15%", f"{over_15_instances:,}")
        c4.metric("Over 20%", f"{over_20_instances:,}")
        c5.metric("FL Mix > Target+10%", f"{over_mix_10:,}")

        st.dataframe(model_detail_display, use_container_width=True, column_config={
            "% of Frontline": st.column_config.NumberColumn(format="%.1f%%"),
            "Merch Mix Target": st.column_config.NumberColumn(format="%.1f%%"),
            "Over/Under (FL)": st.column_config.NumberColumn(format="%+.1f%%"),
        })

        # Company total: all models and their % of total frontline
        st.subheader("Company Total by Model")
        company_total_fl = model_detail["frontline"].sum()
        company_model = model_detail.groupby("commonmodel").agg(frontline=("frontline", "sum")).reset_index()
        company_model["pct_of_frontline"] = (company_model["frontline"] / company_total_fl * 100).round(1)
        company_model = company_model.sort_values("pct_of_frontline", ascending=False).reset_index(drop=True)
        company_model.index += 1
        company_model.columns = ["Model", "Frontline", "% of Total Frontline"]
        st.dataframe(company_model, use_container_width=True, column_config={"% of Total Frontline": st.column_config.NumberColumn(format="%.1f%%")})

    if tab9:
      with tab9:
        st.caption("Each store's single most concentrated model — the one model making up the largest share of that store's frontline.")
        # For each store, find the model with the highest % of frontline
        store_model_pct = (
            df_filtered[df_filtered["frontline"] > 0]
            .groupby(["parentcostcenterdesc", "sourcingregion", "commonmodel"])
            .agg(frontline=("frontline", "sum"))
            .reset_index()
        )
        store_model_pct["store_total"] = store_model_pct.groupby("parentcostcenterdesc")["frontline"].transform("sum")
        store_model_pct["pct_of_frontline"] = (store_model_pct["frontline"] / store_model_pct["store_total"] * 100).round(1)
        top_model = store_model_pct.loc[store_model_pct.groupby("parentcostcenterdesc")["pct_of_frontline"].idxmax()].reset_index(drop=True)
        top_model = top_model.sort_values("pct_of_frontline", ascending=False).reset_index(drop=True)
        top_model.index += 1
        top_model = top_model[["parentcostcenterdesc", "sourcingregion", "commonmodel", "frontline", "store_total", "pct_of_frontline"]]
        top_model.columns = ["Store", "Region", "Top Model", "Model Frontline", "Store Total Frontline", "% of Frontline"]
        st.dataframe(top_model, use_container_width=True, column_config={"% of Frontline": st.column_config.NumberColumn(format="%.1f%%")})

    if tab10:
      with tab10:
        st.caption("Total absolute deviation between each store's actual model mix and their merch mix targets — higher = more misaligned.")
        # Store-level deviation: includes 0-unit models with a target
        deviation_data = (
            df_filtered[
                ((df_filtered["frontline"] > 0) | (pd.to_numeric(df_filtered["finalmerchmix"], errors="coerce") > 0))
                & (df_filtered["finalmerchmix"].notna())
            ]
            .groupby(["parentcostcenterdesc", "commonmodel"])
            .agg(
                sourcingregion=("sourcingregion", "first"),
                frontline=("frontline", "sum"),
                finalmerchmix=("finalmerchmix", "first"),
            )
            .reset_index()
        )
        deviation_data["frontline"] = deviation_data["frontline"].fillna(0)
        dev_store_totals = deviation_data.groupby("parentcostcenterdesc")["frontline"].transform("sum")
        deviation_data["pct_of_frontline"] = deviation_data["frontline"] / dev_store_totals.replace(0, pd.NA) * 100
        deviation_data["pct_of_frontline"] = deviation_data["pct_of_frontline"].fillna(0)
        deviation_data["finalmerchmix_pct"] = pd.to_numeric(deviation_data["finalmerchmix"], errors="coerce") * 100
        deviation_data["over_under"] = (deviation_data["pct_of_frontline"] - deviation_data["finalmerchmix_pct"])
        store_deviation = (
            deviation_data[deviation_data["over_under"].notna()]
            .groupby(["parentcostcenterdesc", "sourcingregion"])
            .agg(total_deviation=("over_under", lambda x: x.abs().sum() / 2))
            .reset_index()
            .sort_values("total_deviation", ascending=False)
            .reset_index(drop=True)
        )
        store_deviation.index += 1
        store_deviation.columns = ["Store", "Sourcing Region", "Total Deviation"]
        store_deviation["Total Deviation"] = store_deviation["Total Deviation"].round(1)
        st.dataframe(store_deviation, use_container_width=True, column_config={"Total Deviation": st.column_config.NumberColumn(format="%.1f%%")})

    st.divider()

    # =====================================================================
    # MERCH MIX DEVIATION
    # =====================================================================
    st.header("Model Mix by Region")
    st.caption("Each model's share of frontline units within each sourcing region")

    if "commonmodel" in df_filtered.columns:
        region_model_df = (
            df_filtered[
                (df_filtered["frontline"] > 0)
                & (df_filtered["commonmodel"].notna())
            ]
            .groupby(["sourcingregion", "commonmodel"])
            .agg(frontline=("frontline", "sum"))
            .reset_index()
        )
        all_models = sorted(region_model_df["commonmodel"].unique())
        selected_model = st.selectbox("Filter by Model", ["All"] + all_models, key="model_mix_filter")
        region_totals = region_model_df.groupby("sourcingregion")["frontline"].transform("sum")
        region_model_df["pct_of_frontline"] = (region_model_df["frontline"] / region_totals.replace(0, pd.NA) * 100).fillna(0)
        region_model_df = region_model_df.sort_values(["sourcingregion", "pct_of_frontline"], ascending=[True, False]).reset_index(drop=True)
        region_model_df.columns = ["Sourcing Region", "Model", "Frontline Units", "% of Frontline"]
        if selected_model != "All":
            region_model_df = region_model_df[region_model_df["Model"] == selected_model]
        region_model_df["% of Frontline"] = region_model_df["% of Frontline"].round(1)
        st.dataframe(region_model_df, use_container_width=True, hide_index=True, column_config={"% of Frontline": st.column_config.NumberColumn(format="%.1f%%")})
    else:
        st.info("No model data available for the current filter.")

    st.divider()

    # =====================================================================
    # INVENTORY DUPLICATES - Same model/mileage bucket/distro group at a store
    # =====================================================================
    st.header("Inventory Duplicates")
    st.caption("Stores with multiple units sharing the same model, mileage bucket, and distro group on the frontline")

    if st.button("Load Duplicates Data"):
        with st.spinner("Loading duplicates data..."):
            st.session_state["df_dupes"] = load_dupes(target_date_str)

    if "df_dupes" in st.session_state and not st.session_state["df_dupes"].empty:
        df_dupes = st.session_state["df_dupes"].copy()
        df_dupes.columns = [c.lower() for c in df_dupes.columns]
        # Exclude closed stores
        df_dupes = df_dupes[~df_dupes["parentcostcenterdesc"].str.upper().str.strip().isin(closed_stores)]

        if selected_region != "All":
            df_dupes = df_dupes[df_dupes["sourcingregion"] == selected_region]
        if selected_store != "All":
            df_dupes = df_dupes[df_dupes["parentcostcenterdesc"] == selected_store]

        if not df_dupes.empty:
            # Store-level summary: total duplicate units
            store_dupes = (
                df_dupes.groupby(["parentcostcenterdesc", "sourcingregion"])
                .agg(dupe_combinations=("totaldupes", "count"), total_dupe_units=("totaldupes", "sum"))
                .reset_index()
                .sort_values("total_dupe_units", ascending=False)
            )
            store_dupes.columns = ["Store", "Region", "# Dupe Combinations", "Total Duplicate Units"]

            st.subheader("Stores with Most Duplicate Inventory")
            st.dataframe(store_dupes[["Store", "Region", "# Dupe Combinations", "Total Duplicate Units"]].reset_index(drop=True), use_container_width=True, hide_index=True)

            # Detail table
            st.subheader("Duplicate Detail")
            dupes_display = df_dupes[["parentcostcenterdesc", "sourcingregion", "commonmodel", "mileagebucket", "distrogroups", "totaldupes"]].copy()
            dupes_display.columns = ["Store", "Region", "Model", "Mileage Bucket", "Distro Group", "# Units"]
            dupes_display = dupes_display.sort_values("# Units", ascending=False).reset_index(drop=True)
            st.dataframe(dupes_display.head(50), use_container_width=True, hide_index=True)

            # Trend a specific duplicate combination
            st.subheader("Trend Duplicate Over Time")
            st.caption("Select a store/model/mileage/distro combination to see how the count has changed over the last 90 days.")
            tc1, tc2 = st.columns(2)
            with tc1:
                trend_store_options = sorted(df_dupes["parentcostcenterdesc"].unique())
                trend_store = st.selectbox("Store", trend_store_options, key="dupes_trend_store")
            with tc2:
                store_dupes_filtered = df_dupes[df_dupes["parentcostcenterdesc"] == trend_store] if trend_store else df_dupes
                trend_model_options = sorted(store_dupes_filtered["commonmodel"].dropna().unique())
                trend_model = st.selectbox("Model", trend_model_options, key="dupes_trend_model")
            tc3, tc4 = st.columns(2)
            with tc3:
                model_filtered = store_dupes_filtered[store_dupes_filtered["commonmodel"] == trend_model] if trend_model else store_dupes_filtered
                trend_mileage_options = sorted(model_filtered["mileagebucket"].dropna().unique())
                trend_mileage = st.selectbox("Mileage Bucket", trend_mileage_options, key="dupes_trend_mileage")
            with tc4:
                mileage_filtered = model_filtered[model_filtered["mileagebucket"] == trend_mileage] if trend_mileage else model_filtered
                trend_distro_options = sorted(mileage_filtered["distrogroups"].dropna().unique())
                trend_distro = st.selectbox("Distro Group", trend_distro_options, key="dupes_trend_distro")

            if st.button("Load Duplicate Trend", key="load_dupes_trend_btn"):
                if trend_store and trend_model and trend_mileage and trend_distro:
                    trend_start = (snapshot_date - timedelta(days=90)).strftime("%Y-%m-%d")
                    with st.spinner("Loading duplicate trend..."):
                        dupes_trend_df = load_dupes_trend(trend_start, target_date_str, trend_store, trend_model, trend_mileage, trend_distro)
                    if not dupes_trend_df.empty:
                        dupes_trend_df.columns = [c.lower() for c in dupes_trend_df.columns]
                        dupes_trend_df["asofdate"] = pd.to_datetime(dupes_trend_df["asofdate"]).dt.date
                        dupes_trend_df = dupes_trend_df.sort_values("asofdate")
                        st.session_state["dupes_trend_result"] = dupes_trend_df
                    else:
                        st.session_state["dupes_trend_result"] = None
                        st.info("No trend data found — this combination may not have had duplicates in the last 90 days.")
                else:
                    st.warning("Please select all filters above.")

            if "dupes_trend_result" in st.session_state and st.session_state["dupes_trend_result"] is not None:
                trend_chart = st.session_state["dupes_trend_result"].copy()
                trend_chart["asofdate"] = pd.to_datetime(trend_chart["asofdate"]).dt.strftime("%m/%d/%y")
                st.line_chart(trend_chart, x="asofdate", y="totaldupes")
        else:
            st.info("No duplicate inventory found for the selected filters.")

    st.divider()

    # =====================================================================
    # TREND CHARTS - Company Wide
    # =====================================================================
    st.header("Trends Over Time")
    st.caption("Company-wide view with optional store/region filters")

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        default_start = date.today() - timedelta(days=30)
        trend_range = st.date_input(
            "Date range",
            value=(default_start, date.today() - timedelta(days=1)),
            max_value=date.today() - timedelta(days=1),
        )
    with col_t2:
        all_regions = sorted(df_filtered["sourcingregion"].dropna().unique())
        trend_regions = st.multiselect("Filter by Region", all_regions, default=[])
    with col_t3:
        all_stores = sorted(df_filtered["parentcostcenterdesc"].dropna().unique())
        trend_stores = st.multiselect("Filter by Store", all_stores, default=[])

    if len(trend_range) == 2:
        start_str = trend_range[0].strftime("%Y-%m-%d")
        end_str = trend_range[1].strftime("%Y-%m-%d")

        with st.spinner("Loading company-wide trends..."):
            df_trend = load_trends(start_str, end_str)

        if not df_trend.empty:
            df_trend.columns = [c.lower() for c in df_trend.columns]
            df_trend["calendardate"] = pd.to_datetime(df_trend["calendardate"])

            # Exclude closed stores
            closed_stores = ["COLUMBIA MISSOURI", "COLUMBIA-MISSOURI", "ESCONDIDO", "FT PIERCE", "NEW CIRCLE ROAD", "VAN NUYS"]
            df_trend = df_trend[~df_trend["parentcostcenterdesc"].str.upper().str.strip().isin(closed_stores)]

            # Apply filters
            if trend_regions:
                df_trend = df_trend[df_trend["sourcingregion"].isin(trend_regions)]
            if trend_stores:
                df_trend = df_trend[df_trend["parentcostcenterdesc"].isin(trend_stores)]

            for c in ["frontline", "dealeroptimum", "lotrepair", "sales", "website_units", "duplicate_units"]:
                if c in df_trend.columns:
                    df_trend[c] = pd.to_numeric(df_trend[c], errors="coerce").fillna(0)
            if "merch_deviation" in df_trend.columns:
                df_trend["merch_deviation"] = pd.to_numeric(df_trend["merch_deviation"], errors="coerce")

            # Aggregate to daily totals (company or filtered)
            daily = df_trend.groupby("calendardate").agg(
                frontline=("frontline", "sum"),
                dealeroptimum=("dealeroptimum", "sum"),
                lotrepair=("lotrepair", "sum"),
                sales=("sales", "sum"),
                website_units=("website_units", "sum"),
                duplicate_units=("duplicate_units", "sum"),
                merch_deviation=("merch_deviation", "mean"),
            ).reset_index()

            daily["pct_to_optimum"] = (daily["frontline"] / daily["dealeroptimum"].replace(0, pd.NA) * 100).fillna(0).round(1)
            daily["pct_lot_repair"] = (daily["lotrepair"] / (daily["lotrepair"] + daily["frontline"]).replace(0, pd.NA) * 100).fillna(0).round(1)
            daily["pct_frontline_sold"] = (daily["sales"] / daily["frontline"].replace(0, pd.NA) * 100).fillna(0).round(2)

            # Ensure calendardate is proper date for chart x-axis
            daily["calendardate"] = pd.to_datetime(daily["calendardate"])
            daily = daily.sort_values("calendardate")
            # Filter out Sundays for sales charts
            daily_no_sun = daily[daily["calendardate"].dt.dayofweek != 6].copy()
            daily["calendardate"] = daily["calendardate"].dt.strftime("%m/%d/%y")
            daily_no_sun["calendardate"] = daily_no_sun["calendardate"].dt.strftime("%m/%d/%y")

            # --- Charts in 2-column layout ---
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("Frontline vs Optimum")
                chart1 = daily[["calendardate", "frontline", "dealeroptimum"]].set_index("calendardate")
                chart1.columns = ["Frontline", "Optimum"]
                st.line_chart(chart1)

            with col_right:
                st.subheader("% to Optimum")
                chart2 = daily[["calendardate", "pct_to_optimum"]].set_index("calendardate")
                chart2.columns = ["% to Optimum"]
                st.line_chart(chart2, y_label="%")

            col_left2, col_right2 = st.columns(2)

            with col_left2:
                st.subheader("Daily Sales")
                chart3 = daily_no_sun[["calendardate", "sales"]].set_index("calendardate")
                chart3.columns = ["Sales"]
                st.line_chart(chart3)

            with col_right2:
                st.subheader("% Lot Repair")
                chart4 = daily[["calendardate", "pct_lot_repair"]].set_index("calendardate")
                chart4.columns = ["% Lot Repair"]
                st.line_chart(chart4, y_label="%")

            col_left3, col_right3 = st.columns(2)

            with col_left3:
                st.subheader("Merch Mix Deviation %")
                chart5 = daily[["calendardate", "merch_deviation"]].set_index("calendardate")
                chart5.columns = ["Avg Deviation %"]
                st.line_chart(chart5, y_label="%")

            with col_right3:
                st.subheader("Duplicate Model Instances")
                chart6 = daily[["calendardate", "duplicate_units"]].set_index("calendardate")
                chart6.columns = ["Duplicate Units"]
                st.line_chart(chart6)

            col_left4, col_right4 = st.columns(2)

            with col_left4:
                st.subheader("Website Units")
                chart7 = daily[["calendardate", "website_units"]].set_index("calendardate")
                chart7.columns = ["Website Units"]
                st.line_chart(chart7)

            with col_right4:
                st.subheader("% of Frontline Sold")
                chart8 = daily_no_sun[["calendardate", "pct_frontline_sold"]].set_index("calendardate")
                chart8.columns = ["% Sold"]
                st.line_chart(chart8, y_label="%")
        else:
            st.info("No trend data returned for this date range.")

    st.divider()

    # =====================================================================
    # FULL STORE DETAIL TABLE
    # =====================================================================
    st.header("Full Store Detail")
    display_cols = [
        "parentcostcenterdesc", "storetotalfrontlineinventory", "distinct_models", "dealeroptimum",
        "pct_optimum", "pct_lot_sold_7d", "pct_lot_repair", "holdinglot",
        "allocations", "lotrepair", "layaway", "last7dayssales", "avgdealerdays",
    ]
    display_df = store_summary[[c for c in display_cols if c in store_summary.columns]].copy()
    col_names = [
        "Store", "Frontline", "Distinct Models", "Dealer Optimum",
        "% to Optimum", "% Lot Sold (7d)", "% Lot Repair", "Holding Lot",
        "Allocations", "Lot Repair", "Layaways", "7d Net Sales", "Avg Dealer Days",
    ][:len(display_df.columns)]
    display_df.columns = col_names
    for col in ["% to Optimum", "% Lot Sold (7d)", "% Lot Repair", "Avg Dealer Days"]:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(1)
    st.dataframe(
        display_df.sort_values("% to Optimum", ascending=True).reset_index(drop=True),
        use_container_width=True,
    )

    st.divider()

    # =====================================================================
    # AI CHAT ASSISTANT
    # =====================================================================
    st.header("Ask the Dashboard")

    if not HAS_OPENAI and not HAS_ANTHROPIC:
        st.info("Install `pip install openai` or `pip install anthropic` to enable the chat assistant.")
    else:
        # Provider + API key in sidebar
        providers = []
        if HAS_ANTHROPIC:
            providers.append("Claude (Anthropic)")
        if HAS_OPENAI:
            providers.append("GPT (OpenAI)")
        ai_provider = st.sidebar.selectbox("AI Provider", providers)
        api_key = st.sidebar.text_input("API Key", type="password", help="Enter your API key for the selected provider")

        if not api_key:
            st.info("Enter your API key in the sidebar to enable the chat assistant.")
        else:
            # Build context summary from current data
            total_frontline = int(pd.to_numeric(store_summary.get("storetotalfrontlineinventory", pd.Series()), errors="coerce").sum())
            total_optimum = int(pd.to_numeric(store_summary.get("dealeroptimum", pd.Series()), errors="coerce").sum())
            total_lotrepair = int(pd.to_numeric(store_summary.get("lotrepair", pd.Series()), errors="coerce").sum())
            total_sales_7d = int(pd.to_numeric(store_summary.get("last7dayssales", pd.Series()), errors="coerce").sum())
            num_stores = len(store_summary)

            # Top/bottom stores
            if "pct_optimum" in store_summary.columns:
                ss = store_summary.copy()
                ss["pct_optimum"] = pd.to_numeric(ss["pct_optimum"], errors="coerce")
                worst_5 = ss.nsmallest(5, "pct_optimum")[["parentcostcenterdesc", "pct_optimum"]].to_string(index=False)
                best_5 = ss.nlargest(5, "pct_optimum")[["parentcostcenterdesc", "pct_optimum"]].to_string(index=False)
            else:
                worst_5 = best_5 = "N/A"

            system_prompt = f"""You are an AI assistant for the Frontline Health Dashboard at DriveTime.
You help users understand inventory health metrics across dealership stores.

Current snapshot date: {target_date_str}
Total stores: {num_stores}
Company total frontline: {total_frontline}
Company total optimum: {total_optimum}
Company % to optimum: {round(total_frontline / max(total_optimum, 1) * 100, 1)}%
Total lot repair: {total_lotrepair}
7-day net sales: {total_sales_7d}

Worst 5 stores by % to optimum:
{worst_5}

Best 5 stores by % to optimum:
{best_5}

Key metrics tracked: Frontline vs Optimum, Website Units, Model Diversity, % Lot Repair,
% Lot Sold (7d), Avg Dealer Days, LTS vs Budget, Merch Mix Deviation, Inventory Duplicates.

Answer questions concisely. If asked about data you don't have, say so."""

            # Session state for chat history
            if "chat_messages" not in st.session_state:
                st.session_state.chat_messages = []

            # Display chat history
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Chat input
            if prompt := st.chat_input("Ask a question about the dashboard..."):
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            if ai_provider == "Claude (Anthropic)":
                                client = Anthropic(api_key=api_key)
                                messages = []
                                for m in st.session_state.chat_messages[-10:]:
                                    messages.append({"role": m["role"], "content": m["content"]})
                                response = client.messages.create(
                                    model="claude-sonnet-4-20250514",
                                    max_tokens=500,
                                    system=system_prompt,
                                    messages=messages,
                                )
                                reply = response.content[0].text
                            else:
                                client = OpenAI(api_key=api_key)
                                messages = [{"role": "system", "content": system_prompt}]
                                for m in st.session_state.chat_messages[-10:]:
                                    messages.append({"role": m["role"], "content": m["content"]})
                                response = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=messages,
                                    max_tokens=500,
                                    temperature=0.3,
                                )
                                reply = response.choices[0].message.content
                        except Exception as e:
                            reply = f"Error: {e}"
                    st.markdown(reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
