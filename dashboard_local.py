# Local Streamlit version of the Frontline Health Dashboard
# Run with: streamlit run dashboard_local.py

import streamlit as st
import pandas as pd
import snowflake.connector
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


def get_connection():
    return snowflake.connector.connect(
        account="drivetime-drivetime_azure_westus2",
        user="alexa.bozzano@drivetime.com",
        authenticator="externalbrowser",
        warehouse="ADHOC_LARGE",
        database="INVENTORY_SANDBOX",
        schema="PUBLIC",
        role="SF-SUPPLY-CHAIN-ANALYTICS",
    )


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
    where ST.STOCKNUMBER NOT ILIKE '2%'
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
FROM STOCKS S
where acquisition_week >= '2025-01-01'
),


layaway_stocknumbers as (
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

layaways as (
select distinct asofdate,st.stocknumber,ccd.childcostcenterdesc,ccd.parentcostcenterdesc,classmake,classmodel,distrogroups, mm.commonmodel,sourcingregion
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
    on a.commonmodel=mm.commonmodel
where in_process_desc in ('Dealer','Holding Lot','Lot Repair')
and title_distro_ready='Unavailable' 
and title_location <> 'Dealership-Shipped'
and status_code= 'LA'
and ccd.program='DT'
and ccd.in_process_desc ilike 'Dealer'
and st.asofdate = '{target_date}'
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
left join inventory_sandbox.admdev.dbo_tblccdmapping ccd on ccd.crllt= st.clot
and E.event_name = 'ga2Affordability'
AND FV.stock_number NOT LIKE '2%'
and stat= 'AV'

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
and E.event_name = 'posAffordability'
AND FV.stock_number NOT LIKE '2%'
and childcostcenterdesc in ('MONTCLAIR', 'RIVERSIDE')
and stat= 'AV'
),


stocknextdate as (
    select stocknumber, asofdate,
        ifnull(lead(asofdate) over (partition by stocknumber order by asofdate), current_date()) as nextdate
    from (select distinct stocknumber, asofdate from INVENTORY.VEHICLE.STOCKTREND where stocknumber < 1990000000)
),

trendedfrontlines as (
select distinct st.stocknumber,st.asofdate, ccd.childcostcenterid,ccd.childcostcenterdesc,in_process_desc,ccd.parentcostcenterdesc
,snd.nextdate
,a.classmake,a.classmodel,distrogroups,SIZEGROUP,sourcingregion
,ifnull(mm.commonmodel,mm2.commonmodel) as commonmodel
,case when t.stock_number is not null and in_process_desc ilike 'Dealer' then 1 else 0 end as Frontline
,case when ws.website_stocks is not null then 1 else 0 end as websiteunit
,activedealerdays
from INVENTORY.VEHICLE.STOCKTREND st
inner join stocknextdate snd
    on st.stocknumber=snd.stocknumber
    and st.asofdate=snd.asofdate
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
and st.stocknumber not in (select stocknumber from layaway_stocknumbers )
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
           and (description ilike '%%emis%%' or description ilike '%%inspec%%') then 1 else 0 end =1
           OR
           case when claim_reason='EMMS'
           and (description ilike '%%emis%%' or description ilike '%%inspec%%') then 1 else 0 end =1 OR
            description ILIKE 'EMMS' or
            description ILIKE '%%Emi%%' OR
            description ILIKE '%%emm%%' or
            description ILIKE '%%insp%%' OR 
            description ILIKE '%%msi%%' OR 
            description ILIKE '%%ncsi%%' OR 
            description ILIKE '%%safety insp%%' or
            description ILIKE '%%safely insp%%' or
            description ILIKE '%%state in%%' or
            description ILIKE '%%state is%%' or
             description ILIKE '%%states em%%' or
            description ILIKE '%%state em%%' OR
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
and description not in ('Emissions Test','State Inspection','Inspection Fee - Pending','Used Car Inspection / MPI')
and minr.stock_number is not null
and status not in ('Denied')
),

lotrepairstore as (
select distinct ch.stock_number,parentcostcenterdesc,ch.created_date
,case when ts.stock_number is not null then 1 else 0 end as EmissionsExtraRepair
,case when minr.stock_number is not null then 1 else 0 end as PreFrontlineProcessCar
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
where ch.repair_facility_name not ilike '%Unwinds%'
and ch.created_date>= '2026-01-01'
),

lotrepair as (
select asofdate,stocknumber,childcostcenterdesc,lr.parentcostcenterdesc,classmake,classmodel,distrogroups,sourcingregion,in_process_desc,tf.commonmodel
,EmissionsExtraRepair,PreFrontlineProcessCar
from trendedfrontlines tf
left join lotrepairstore lr
    on tf.stocknumber=lr.stock_number
    and asofdate between lr.created_date and nextdate
where in_process_desc = 'Lot Repair'
and asofdate = '{target_date}'
),


allocations as (
SELECT distinct
       t.stocknumber,
        t.allocationdate::date AS allocationdate,
        ccd.parentcostcenterdesc,
        ccd2.sourcingregion AS RC
        ,classmake,classmodel,distrogroups
        ,case when allocationstatustypedescription in ('Removed','Completed','Unfulfilled') then maxchangedate::date else current_date() end as enddate
        ,ifnull(mm.commonmodel,mm2.commonmodel) as commonmodel
        ,ccd.sourcingregion
    FROM 
        INVENTORY.TRANSPORT.TRANSFERALLOCATIONTREND t
        inner join  (    select stocknumber,allocationdate, max(lastchangeddatetime::date) as maxchangedate
        from  INVENTORY.TRANSPORT.TRANSFERALLOCATIONTREND
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
    where (ccd.in_process_desc ilike 'Dealer' or ccd.in_process_desc ilike 'Holding Lot')
    order by allocationdate desc
),

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
and d.calendardate = '{target_date}'
),


dealeroptimums as (
select costcenter_id,childcostcenterdesc,low,high,effectivedate,enddate,parentcostcenterdesc,capacity
from INVENTORY_SANDBOX.SUPPLYCHAIN.DEALERSHIPLOTOPTIMUMS
left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
    on costcenter_id=ccd.childcostcenterid
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
inner join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
On df.costcenter_id = ccd.ChildCostCenterID
    WHERE ccd.Program = 'DT'
    and df.calendar_date = '{target_date}'
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

    SALES AS (
        SELECT
            AD.CRLLD,
            DATE_TRUNC(DAY, SALEDATE) AS DAY,
            YEAR(SALEDATE) AS YEAR,
            MONTH(SALEDATE) AS MONTH,
            COUNT(SALEID) AS SALES,
            DIRECTOR,
            AD,
            AD.REPORTINGREGIONDESCRIPTION AS REGION
        FROM RETAIL.SALE.CENTRALIZEDSALE CS
        LEFT JOIN RETAIL_SANDBOX.RETAIL.AD_DIRECTOR_MAPPING_STATIC AD
            ON AD.CRLLT = CS.SALELOCATIONNUMBER
        WHERE COMPANY = 'DriveTime'
            AND SALEDATE = '{target_date}'
        GROUP BY ALL
    ),

    BACKOUTS AS (
        SELECT
            AD.CRLLD,
            DATE_TRUNC(DAY, BACKOUTDATE) AS DAY,
            YEAR(BACKOUTDATE) AS YEAR,
            MONTH(BACKOUTDATE) AS MONTH,
            COUNT(BACKOUTDATE) AS BACKOUTS,
            DIRECTOR,
            AD
        FROM RETAIL.SALE.CENTRALIZEDSALE CS
        LEFT JOIN RETAIL_SANDBOX.RETAIL.AD_DIRECTOR_MAPPING_STATIC AD
            ON AD.CRLLT = CS.SALELOCATIONNUMBER
        WHERE COMPANY = 'DriveTime'
            AND BACKOUTDATE = '{target_date}'
        GROUP BY ALL
    ),

    LEADS AS (
        SELECT
            YEAR(CLS.LIFECYCLESTARTDATE) AS YEAR,
            MONTH(CLS.LIFECYCLESTARTDATE) AS MONTH,
            DATE_TRUNC(DAY, LIFECYCLESTARTDATE) AS DAY,
            AD.CRLLD,
            COUNT(CLS.LIFECYCLESTARTDATE) AS LEADS,
            DIRECTOR,
            AD,
            AD.REPORTINGREGIONDESCRIPTION AS REGION
        FROM MARKETING.LEAD.CENTRALIZEDLEADSOURCE CLS
        LEFT JOIN RETAIL_SANDBOX.RETAIL.AD_DIRECTOR_MAPPING_STATIC AD
            ON AD.CRLLT = CLS.ASSIGNEDSTOREDESKIT
        WHERE CLS.LIFECYCLESTARTDATE = '{target_date}'
            AND AD.CRLLD IS NOT NULL
            AND CLS.LIFECYCLEID NOT IN (SELECT LIFECYCLEID FROM RETAIL_SANDBOX.TIMMY.BOT_LEADS)
        GROUP BY ALL
    ),

    BUDGET AS (
        SELECT
            AD.CRLLD,
            YEAR(CALENDAR_DATE) AS YEAR,
            MONTH(CALENDAR_DATE) AS MONTH,
            DATE_TRUNC(DAY, CALENDAR_DATE) AS DAY,
            SUM(CBD.UNITS) AS SALES_BUDGET,
            SUM(CBD.LEADBUDGET) AS LEADS_BUDGET
        FROM RETAIL_SANDBOX.ADMDEV.TBLSALES_BUDGET_CUSTYPE_BYDAY CBD
        LEFT JOIN RETAIL_SANDBOX.RETAIL.AD_DIRECTOR_MAPPING_STATIC AD
            ON AD.CRLLT = CBD.LOT
        WHERE CALENDAR_DATE = '{target_date}'
        GROUP BY ALL
    ),

    LTSFINAL as (
    SELECT
        LEADS.CRLLD,
        LEADS.REGION,
        LEADS.YEAR,
        LEADS.MONTH,
        LEADS.DAY,
        ZEROIFNULL(SALES) AS SALES,
        ZEROIFNULL(BACKOUTS) AS BACKOUTS,
        ZEROIFNULL(SALES) - ZEROIFNULL(BACKOUTS) AS NETSALES,
        LEADS,
        ZEROIFNULL(SALES_BUDGET) AS SALES_BUDGET,
        LEADS_BUDGET,
        NETSALES/LEADS AS LTS,
        SALES_BUDGET/LEADS_BUDGET AS LTS_BUDGET,
        LEADS.AD,
        LEADS.DIRECTOR
    FROM LEADS
    LEFT JOIN BACKOUTS BO
        ON LEADS.CRLLD = BO.CRLLD
        AND LEADS.DAY = BO.DAY
    LEFT JOIN SALES
        ON SALES.CRLLD = LEADS.CRLLD
        AND SALES.DAY = LEADS.DAY
    LEFT JOIN BUDGET
        ON LEADS.CRLLD = BUDGET.CRLLD
        AND LEADS.DAY = BUDGET.DAY
    ORDER BY DAY
 ),
 
 allsales as (
SELECT STOCKNUMBER, SALEDATE, SALETIMEOFDAY, 1 AS NETSALEID, 'Sale' as SALETYPE, BACKOUTDATE,parentcostcenterdesc,sourcingregion
FROM RETAIL.SALE.CENTRALIZEDSALE
left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
    on salelocationnumber=crllt
WHERE SALEDATE >= dateadd(day, -8, '{target_date}')

UNION 

SELECT STOCKNUMBER, BACKOUTDATE AS SALEDATE, SALETIMEOFDAY, -1 AS NETSALEID, SALETYPE, NULL AS BACKOUTDATE,parentcostcenterdesc,sourcingregion
FROM RETAIL.SALE.CENTRALIZEDSALE
left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
    on salelocationnumber=crllt
WHERE SALETYPE = 'Backed Out Sale'
AND BACKOUTDATE >= dateadd(day, -8, '{target_date}')
),

finalallsales as (
select stocknumber, sum(netsaleid) as netsaleid,saledate,parentcostcenterdesc,sourcingregion
from allsales
where saledate >= dateadd(day, -8, '{target_date}')
and stocknumber < 1990000000
group by stocknumber,saledate,parentcostcenterdesc,sourcingregion
)
 
 
, daily_sales as (
    select d.calendardate, ccd.parentcostcenterdesc, ifnull(sum(netsaleid),0) as day_sales,ccd.sourcingregion
    from SHARED.DIMENSION.DIMDATE d
    left join INVENTORY_SANDBOX.ADMDEV.DBO_TBLCCDMAPPING ccd
        on 1=1
        and ccd.in_process_desc ilike 'dealer'
        and program='DT'
        and open_location='Y'
    left join finalallsales s
        on s.saledate = d.calendardate
        and s.parentcostcenterdesc=ccd.parentcostcenterdesc
    where calendardate between dateadd(day, -7, '{target_date}') and '{target_date}'
    group by d.calendardate, ccd.parentcostcenterdesc,ccd.sourcingregion
)

, daily_sales_7d as (
    select parentcostcenterdesc, sourcingregion, sum(day_sales) as last7dayssales
    from daily_sales
    group by parentcostcenterdesc, sourcingregion
)

select
datekey
,src.parentcostcenterdesc
,src.sourcingregion
,src.commonmodel
,avg(src.activedealerdays) as avgdealerdays
,count(distinct case when src.in_process_desc ilike 'Dealer' and src.frontline>=1 then src.stocknumber end) as Frontline
,count(distinct case when websiteunit>=1 then src.stocknumber end) as WebsiteUnit
,count(distinct case when f2.in_process_desc ilike 'Dealer' and f2.frontline>= 1 then f2.stocknumber end) as Last7DaysFrontline
,count(distinct case when f2.in_process_desc ilike 'Dealer' and f2.frontline>= 1 and f2.activedealerdays <= 7 then f2.stocknumber end) as Last7DaysFresh
,totalstocks as StoreTotalFrontlineInventory
,count(distinct case when src.in_process_desc ilike 'Holding Lot' then src.stocknumber end) as  HoldingLot
,count(distinct case when src.in_process_desc ilike 'Allocation' then src.stocknumber end) as  Allocations
,count(distinct case when src.in_process_desc ilike 'Lot Repair' then src.stocknumber end) as  LotRepair
,count(distinct case when src.PreFrontlineProcessCar>=1 and  EmissionsExtraRepair=0 then src.stocknumber end) as PreFrontlineProcessStock
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
,LTS
,LTS_BUDGET
,imm.finalmerchmix
,null as sales
,null as last7dayssales
from (
    SELECT stocknumber, distrogroups, parentcostcenterdesc,classmake,commonmodel, asofdate AS datekey,in_process_desc,sourcingregion,activedealerdays,frontline,websiteunit,null as EmissionsExtraRepair,null as PreFrontlineProcessCar FROM trendedfrontlines
    where in_process_desc in ('Dealer','Holding Lot')
    UNION all
    
    SELECT stocknumber, distrogroups, parentcostcenterdesc,classmake,commonmodel, calendardate as datekey,'Allocation' as in_process_desc,sourcingregion,null as activedealerdays,null as frontline,null as websiteunit,null as EmissionsExtraRepair,null as PreFrontlineProcessCar FROM finalallocations
    UNION all
    
    SELECT stocknumber, distrogroups, parentcostcenterdesc,classmake,commonmodel, asofdate as datekey, in_process_desc,sourcingregion,null as activedealerdays,null as frontline,null as websiteunit,EmissionsExtraRepair,PreFrontlineProcessCar FROM lotrepair

    union all 
    
    SELECT stocknumber, distrogroups, parentcostcenterdesc,classmake,commonmodel, asofdate as datekey,'Layaway' as in_process_desc,sourcingregion,null as activedealerdays,null as frontline,null as websiteunit,null as EmissionsExtraRepair,null as PreFrontlineProcessCar FROM layaways
) src
left join
(select distinct asofdate,stocknumber,parentcostcenterdesc,childcostcenterdesc,in_process_desc,classmake,classmodel,distrogroups,commonmodel,activedealerdays,Frontline
from trendedfrontlines f
where (in_process_desc ilike 'Dealer'
or in_process_desc ilike 'Holding Lot')
and f.asofdate >= dateadd(day,-7, '{target_date}')
) f2
    on f2.parentcostcenterdesc=src.parentcostcenterdesc
    and f2.asofdate::date>=dateadd(day,-7,datekey::date)
    and src.distrogroups=f2.distrogroups
    and src.commonmodel=f2.commonmodel
left join (
select distinct asofdate,count(distinct stocknumber) as totalstocks,parentcostcenterdesc,childcostcenterdesc
from trendedfrontlines f
where in_process_desc ilike 'Dealer'
group by asofdate,parentcostcenterdesc,childcostcenterdesc
) f3
 on f3.parentcostcenterdesc=src.parentcostcenterdesc
    and f3.asofdate::date=datekey::date
left join distrorequirements dr
    on src.parentcostcenterdesc=dr.parentcostcenterdesc
left join  (select*
 from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX) imm
     on upper(imm.commonmodel)= src.commonmodel
    and 
    case when imm.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'
    when imm.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else
    upper(imm.crlld) end=upper(src.parentcostcenterdesc)
    and src.datekey between imm.begindate and ifnull(imm.enddate,current_date())
left join LTSFINAL lts
    on upper(src.parentcostcenterdesc)=upper(lts.crlld)
    and lts.day = '{target_date}'
where datekey = '{target_date}'
group by datekey
,src.parentcostcenterdesc
,src.sourcingregion
,src.commonmodel
,totalstocks
,finalmerchmix
,dr.parentcostcenterdesc
,LTS
,LTS_BUDGET


UNION ALL

SELECT DISTINCT
d.calendardate as datekey
,do.parentcostcenterdesc as parentcostcenterdesc
,null as sourcingregion
,null as commonmodel
,null as avgdealerdays
,null as Frontline
,null as WebsiteUnit
,null as Last7DaysFrontline
,null as Last7DaysFresh
,null as StoreTotalFrontlineInventory
,null as  HoldingLot
,null AS ALLOCATIONS 
,null AS LOTREPAIR
,null as PreFrontlineProcessStock
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
,null as lts
,null as LTS_BUDGET
,null as finalmerchmix
,null as sales
,null as last7dayssales
FROM SHARED.DIMENSION.DIMDATE d
left join dealeroptimums do 
    ON d.calendardate between do.effectivedate and do.enddate 
left join holdingoptimum ho
     on DO.parentcostcenterdesc=ho.parentcostcenterdesc
    AND d.calendardate between ho.effective_date and ho.end_date 
left join dailysales s
    on do.parentcostcenterdesc=s.parentcostcenterdesc
    and d.calendardate::date=s.calendar_date::date
where d.calendardate = '{target_date}'

union all

 select d1.calendardate as datekey
,d1.parentcostcenterdesc as parentcostcenterdesc
,d1.sourcingregion as sourcingregion
,null as commonmodel
,null as avgdealerdays
,null as Frontline
,null as WebsiteUnit
,null as Last7DaysFrontline
,null as Last7DaysFresh
,null as StoreTotalFrontlineInventory
,null as  HoldingLot
,null AS ALLOCATIONS 
,null AS LOTREPAIR
,null as PreFrontlineProcessStock
,null AS LAYAWAYS
,NULL AS today
,NULL AS  day1
,NULL AS day2
,NULL AS day3
,NULL AS day4
,NULL AS day5
,NULL AS day6
,null  as PrefrontlineProcess
,null as DealerOptimum
,null as HoldingOptimum
,null as DealerCapacity
,null as HoldingLotCapacity
,null as lts
,null as LTS_BUDGET
,null as finalmerchmix
, coalesce(day_sales, 0) as sales
, d7.last7dayssales
from daily_sales d1
left join daily_sales_7d d7
    on d1.parentcostcenterdesc = d7.parentcostcenterdesc
    and d1.sourcingregion = d7.sourcingregion
where d1.calendardate = '{target_date}'
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
,ifnull(mm.commonmodel, mm2.commonmodel) as commonmodel
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
(select * from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX where iscurrent=1) mm
    on COALESCE(upper(a.commonmodel),UPPER(SPLIT_PART(A.CLASSMODEL, ' ', 1)))=upper(mm.commonmodel)
    AND case when MM.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'
        when MM.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD' else
        upper(MM.crlld) end=upper(ccd.parentcostcenterdesc)
left join
(select * from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX where iscurrent=1) mm2
    on CONCAT('OTHER_',case when a.sizegroup ilike 'SPORTS-SPECIALTY' then 'SPECIALTY' ELSE a.SIZEGROUP END)=upper(mm2.commonmodel)
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
    select md.asofdate, md.parentcostcenterdesc,
        sum(abs(md.model_count * 100.0 / nullif(stot.total_frontline, 0) - ifnull(mm.finalmerchmix, 0))) as total_deviation
    from model_detail md
    join store_totals stot on md.asofdate = stot.asofdate and md.parentcostcenterdesc = stot.parentcostcenterdesc
    left join (select * from RISK_SANDBOX.IVAN.MODEL_MERCH_MIX where iscurrent = 1) mm
        on upper(md.commonmodel) = upper(mm.commonmodel)
        and case when mm.crlld ilike 'CHICAGO - MIDLOTHIAN' then 'CHICAGO-MIDLOTHIAN'
            when mm.crlld ilike 'CHICAGO - LOMBARD' then 'CHICAGO-LOMBARD'
            else upper(mm.crlld) end = upper(md.parentcostcenterdesc)
    group by md.asofdate, md.parentcostcenterdesc
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
    coalesce(mdev.total_deviation, 0) as merch_deviation
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


@st.cache_data(ttl=1800)
def load_snapshot(target_date: str):
    sql = SNAPSHOT_SQL.replace("{target_date}", target_date)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("ALTER SESSION SET USE_CACHED_RESULT = TRUE")
        cur.execute(sql)
        df = cur.fetch_pandas_all()
    finally:
        conn.close()
    return df


@st.cache_data(ttl=1800)
def load_trends(start_date: str, end_date: str):
    sql = TRENDS_SQL.replace("{start_date}", start_date)
    sql = sql.replace("{end_date}", end_date)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("ALTER SESSION SET USE_CACHED_RESULT = TRUE")
        cur.execute(sql)
        df = cur.fetch_pandas_all()
    finally:
        conn.close()
    return df


@st.cache_data(ttl=1800)
def load_dupes(target_date: str):
    sql = DUPES_SQL.replace("{target_date}", target_date)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        df = cur.fetch_pandas_all()
    finally:
        conn.close()
    return df


def main():
    st.title("Frontline Health Dashboard")

    # --- Sidebar ---
    st.sidebar.header("Filters")

    if st.sidebar.button("Clear Cache & Reload"):
        st.cache_data.clear()
        st.rerun()

    yesterday = date.today() - timedelta(days=1)
    snapshot_date = st.sidebar.date_input("Snapshot Date", value=yesterday)
    target_date_str = snapshot_date.strftime("%Y-%m-%d")

    # Previous week (same day last week) for delta comparison
    prev_date = snapshot_date - timedelta(days=7)
    prev_date_str = prev_date.strftime("%Y-%m-%d")

    # Load current day first, then previous week
    with st.spinner("Loading snapshot data from Snowflake..."):
        df = load_snapshot(target_date_str)

    if df.empty:
        st.warning("No data returned for the selected date. Try a different date.")
        return

    # Load previous week (cached after first run) - skip on cold load for speed
    show_deltas = st.sidebar.checkbox(f"Show vs Prior Week deltas ({prev_date.strftime('%m/%d')})", value=True)
    if show_deltas:
        df_prev = load_snapshot(prev_date_str)
    else:
        df_prev = pd.DataFrame()

    # Lowercase columns
    df.columns = [c.lower() for c in df.columns]

    # Process previous day data for deltas
    prev_totals = {}
    if not df_prev.empty:
        df_prev.columns = [c.lower() for c in df_prev.columns]
        df_prev = df_prev[~df_prev["parentcostcenterdesc"].str.upper().str.strip().isin(
            ["COLUMBIA MISSOURI", "COLUMBIA-MISSOURI", "ESCONDIDO", "FT PIERCE"]
        )]
        for col in ["frontline", "websiteunit", "lotrepair", "holdinglot", "layaway", "allocations", "last7dayssales", "dealeroptimum"]:
            if col in df_prev.columns:
                prev_totals[col] = pd.to_numeric(df_prev[col], errors="coerce").sum()

    # Exclude closed stores
    closed_stores = ["COLUMBIA MISSOURI", "COLUMBIA-MISSOURI", "ESCONDIDO", "FT PIERCE", "NEW CIRCLE ROAD", "VAN NUYS"]
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

    # --- Aggregate store-level metrics ---
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
            dealeroptimum=("dealeroptimum", "max"),
            holdingoptimum=("holdingoptimum", "max"),
            dealercapacity=("dealercapacity", "max"),
            holdinglotcapacity=("holdinglotcapacity", "max"),
            lts=("lts", "mean"),
            lts_budget=("lts_budget", "mean"),
            sales=("sales", "max"),
            last7dayssales=("last7dayssales", "sum"),
            avgdealerdays=("avgdealerdays", "mean"),
            prefrontlineprocess=("prefrontlineprocess", "max"),
            prefrontlineprocessstock=("prefrontlineprocessstock", "sum"),
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

    total_dealer_optimum = store_summary["dealeroptimum"].sum()
    total_lotrepair = df_filtered["lotrepair"].sum()
    # 7d sales: one value per store from the daily_sales UNION - deduplicate before summing
    sales_by_store = df_filtered[df_filtered["last7dayssales"].notna()].drop_duplicates(subset=["parentcostcenterdesc"])[["parentcostcenterdesc", "last7dayssales"]]
    total_7d_sales = sales_by_store["last7dayssales"].sum()
    total_7d_frontline = store_summary["last7daysfrontline"].sum()
    pct_lot_sold_7d = (total_7d_sales / total_7d_frontline * 100) if total_7d_frontline > 0 else 0
    avg_dealer_days = store_summary["avgdealerdays"].mean()

    total_website = df_filtered["websiteunit"].sum()
    total_holdinglot = int(store_summary["holdinglot"].sum())
    total_layaway = int(store_summary["layaway"].sum())
    total_allocations = int(store_summary["allocations"].sum())
    total_frontline = total_website + total_lotrepair + total_layaway + total_allocations
    overall_pct_optimum = (total_frontline / total_dealer_optimum * 100) if total_dealer_optimum > 0 else 0
    overall_pct_lot_repair = (total_lotrepair / (total_frontline + total_lotrepair) * 100) if (total_frontline + total_lotrepair) > 0 else 0

    # Optimum calculations
    website_optimum = (total_dealer_optimum / 35) * 30
    lotrepair_optimum = (total_dealer_optimum / 35) * 4
    holdinglot_optimum = int(store_summary["holdingoptimum"].sum()) if "holdingoptimum" in store_summary.columns else 0
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
    prev_frontline = prev_website + prev_lotrepair + prev_layaway + prev_totals.get("allocations", 0)
    prev_dealer_optimum = prev_totals.get("dealeroptimum", 0)

    delta_frontline = int(total_frontline - prev_frontline) if prev_frontline else None
    delta_website = int(total_website - prev_website) if prev_website else None
    delta_lotrepair = int(total_lotrepair - prev_lotrepair) if prev_lotrepair else None
    delta_holdinglot = int(total_holdinglot - prev_holdinglot) if prev_holdinglot else None
    delta_layaway = int(total_layaway - prev_layaway) if prev_layaway else None

    # Row 1: Frontline / Delta / Dealer Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Total Frontline Units", f"{int(total_frontline):,}")
    c2.metric("vs Prior Day", f"{delta_frontline:+,}" if delta_frontline is not None else "N/A", delta=f"{delta_frontline:+,}" if delta_frontline is not None else None)
    c3.metric("Total Dealer Optimum", f"{int(total_dealer_optimum):,}")
    c4.metric("% to Optimum", f"{overall_pct_optimum:.1f}%")

    # Row 2: Website / Delta / Website Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Website Units", f"{int(total_website):,}")
    c2.metric("vs Prior Day", f"{delta_website:+,}" if delta_website is not None else "N/A", delta=f"{delta_website:+,}" if delta_website is not None else None)
    c3.metric("Website Optimum", f"{int(website_optimum):,}")
    c4.metric("% to Optimum", f"{pct_website_optimum:.1f}%")

    # Row 3: Lot Repair / Delta / LR Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Lot Repair Units", f"{int(total_lotrepair):,}")
    c2.metric("vs Prior Day", f"{delta_lotrepair:+,}" if delta_lotrepair is not None else "N/A", delta=f"{delta_lotrepair:+,}" if delta_lotrepair is not None else None, delta_color="inverse")
    c3.metric("Lot Repair Optimum", f"{int(lotrepair_optimum):,}")
    c4.metric("% to Optimum", f"{pct_lotrepair_optimum:.1f}%")

    # Row 4: Holding Lot / Delta / HL Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Holding Lot Units", f"{int(total_holdinglot):,}")
    c2.metric("vs Prior Day", f"{delta_holdinglot:+,}" if delta_holdinglot is not None else "N/A", delta=f"{delta_holdinglot:+,}" if delta_holdinglot is not None else None, delta_color="inverse")
    c3.metric("Holding Lot Optimum", f"{int(holdinglot_optimum):,}")
    c4.metric("% to Optimum", f"{pct_holdinglot_optimum:.1f}%")

    # Row 5: Layaways / Delta / Layaway Optimum / % to Optimum
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Layaways", f"{int(total_layaway):,}")
    c2.metric("vs Prior Day", f"{delta_layaway:+,}" if delta_layaway is not None else "N/A", delta=f"{delta_layaway:+,}" if delta_layaway is not None else None)
    c3.metric("Layaway Optimum", f"{int(layaway_optimum):,}")
    c4.metric("% to Optimum", f"{pct_layaway_optimum:.1f}%")

    # Row 6: Allocations / Delta
    prev_allocations = prev_totals.get("allocations", 0)
    delta_allocations = int(total_allocations - prev_allocations) if prev_allocations else None
    c1, c2, c3, c4 = st.columns([3, 2, 3, 3])
    c1.metric("Allocations", f"{int(total_allocations):,}")
    c2.metric("vs Prior Day", f"{delta_allocations:+,}" if delta_allocations is not None else "N/A", delta=f"{delta_allocations:+,}" if delta_allocations is not None else None)
    c3.write("")
    c4.write("")

    st.divider()

    # Frontline Turn Metrics
    st.subheader("Frontline Turn Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distinct Models", f"{network_unique_models}")
    c2.metric("% Lot Sold (7d)", f"{pct_lot_sold_7d:.1f}%")
    c3.metric("Avg Dealer Days", f"{avg_dealer_days:.1f}" if pd.notna(avg_dealer_days) else "N/A")
    c4.metric("7-Day Net Sales", f"{int(total_7d_sales):,}")

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

    tab8, tab1, tab2, tab3, tab10, tab9, tab5, tab4, tab6 = st.tabs([
        "Store/Model Detail",
        "Lowest % to Optimum",
        "Lowest Website Units",
        "Least Model Diversity",
        "Store Deviation",
        "Top Model by Store",
        "Lowest % Lot Sold (7d)",
        "Highest % Lot Repair",
        "Highest Avg Dealer Days",
    ])

    with tab1:
        worst_optimum = (
            ranking_df[ranking_df["dealeroptimum"] > 0]
            .nsmallest(10, "pct_optimum")[
                ["parentcostcenterdesc", "sourcingregion", "prefrontlineprocess", "frontline", "websiteunit", "holdinglot", "lotrepair", "layaway", "dealeroptimum", "holdingoptimum", "pct_optimum"]
            ]
            .reset_index(drop=True)
        )
        worst_optimum.index += 1
        worst_optimum.columns = ["Store", "Region", "PFP", "Frontline", "Website Units", "Holding Lot", "Lot Repair", "Layaway", "Dealer Optimum", "Holding Lot Optimum", "% to Optimum"]
        worst_optimum["PFP"] = worst_optimum["PFP"].fillna(0).astype(int)
        worst_optimum["% to Optimum"] = worst_optimum["% to Optimum"].round(1).astype(str) + "%"
        st.dataframe(worst_optimum, use_container_width=True)
        # Company aggregate
        total_fl = ranking_df["frontline"].sum()
        total_ws = ranking_df["websiteunit"].sum()
        total_hl = ranking_df["holdinglot"].sum()
        total_lr = ranking_df["lotrepair"].sum()
        total_ly = ranking_df["layaway"].sum()
        total_do = ranking_df["dealeroptimum"].sum()
        total_ho = ranking_df["holdingoptimum"].sum()
        co_pct = ((total_fl + total_hl + total_lr + total_ly) / total_do * 100) if total_do > 0 else 0
        company_row = pd.DataFrame([{
            "Store": "COMPANY TOTAL", "Region": "", "PFP": "",
            "Frontline": int(total_fl), "Website Units": int(total_ws),
            "Holding Lot": int(total_hl), "Lot Repair": int(total_lr),
            "Layaway": int(total_ly), "Dealer Optimum": int(total_do),
            "Holding Lot Optimum": int(total_ho), "% to Optimum": f"{co_pct:.1f}%"
        }])
        st.dataframe(company_row, use_container_width=True, hide_index=True)
        # Region aggregates
        region_agg = ranking_df.groupby("sourcingregion").agg(
            frontline=("frontline", "sum"), websiteunit=("websiteunit", "sum"),
            holdinglot=("holdinglot", "sum"), lotrepair=("lotrepair", "sum"),
            layaway=("layaway", "sum"), dealeroptimum=("dealeroptimum", "sum"),
            holdingoptimum=("holdingoptimum", "sum")
        ).reset_index()
        region_agg["pct_optimum"] = ((region_agg["frontline"] + region_agg["holdinglot"] + region_agg["lotrepair"] + region_agg["layaway"]) / region_agg["dealeroptimum"].replace(0, pd.NA) * 100).fillna(0)
        region_display = pd.DataFrame({
            "Region": region_agg["sourcingregion"],
            "Frontline": region_agg["frontline"].astype(int), "Website Units": region_agg["websiteunit"].astype(int),
            "Holding Lot": region_agg["holdinglot"].astype(int), "Lot Repair": region_agg["lotrepair"].astype(int),
            "Layaway": region_agg["layaway"].astype(int), "Dealer Optimum": region_agg["dealeroptimum"].astype(int),
            "Holding Lot Optimum": region_agg["holdingoptimum"].astype(int),
            "% to Optimum": region_agg["pct_optimum"].round(1).astype(str) + "%"
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True)

    with tab3:
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
        least_diverse["% Model Diversity"] = least_diverse["% Model Diversity"].round(1).astype(str) + "%"
        st.dataframe(least_diverse, use_container_width=True)
        # Company aggregate
        co_models = df_filtered[(df_filtered["frontline"] > 0) & (df_filtered["commonmodel"].notna())]["commonmodel"].nunique()
        co_fl = ranking_df["frontline"].sum()
        co_div = (co_models / co_fl * 100) if co_fl > 0 else 0
        company_row = pd.DataFrame([{
            "Store": "COMPANY TOTAL", "Region": "", "PFP": "",
            "Distinct Models": int(co_models), "Frontline": int(co_fl),
            "% Model Diversity": f"{co_div:.1f}%"
        }])
        st.dataframe(company_row, use_container_width=True, hide_index=True)
        # Region aggregates
        region_models = df_filtered[(df_filtered["frontline"] > 0) & (df_filtered["commonmodel"].notna())].groupby("sourcingregion")["commonmodel"].nunique().reset_index(name="distinct_models")
        region_fl = ranking_df.groupby("sourcingregion")["frontline"].sum().reset_index()
        region_div = region_models.merge(region_fl, on="sourcingregion")
        region_div["pct"] = (region_div["distinct_models"] / region_div["frontline"].replace(0, pd.NA) * 100).fillna(0)
        region_display = pd.DataFrame({
            "Region": region_div["sourcingregion"],
            "Distinct Models": region_div["distinct_models"].astype(int),
            "Frontline": region_div["frontline"].astype(int),
            "% Model Diversity": region_div["pct"].round(1).astype(str) + "%"
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True)

    with tab4:
        worst_repair = (
            ranking_df[ranking_df["pct_lot_repair"].notna()]
            .nlargest(10, "pct_lot_repair")[
                ["parentcostcenterdesc", "sourcingregion", "prefrontlineprocess", "lotrepair", "prefrontlineprocessstock", "frontline", "pct_lot_repair"]
            ]
            .reset_index(drop=True)
        )
        worst_repair.index += 1
        worst_repair.columns = ["Store", "Region", "PFP", "Lot Repair Units", "Emissions Stock", "Frontline", "% in Lot Repair"]
        worst_repair["PFP"] = worst_repair["PFP"].fillna(0).astype(int)
        worst_repair["Emissions Stock"] = worst_repair["Emissions Stock"].fillna(0).astype(int)
        worst_repair["Lot Repair Units"] = worst_repair["Lot Repair Units"] - worst_repair["Emissions Stock"]
        worst_repair["% in Lot Repair"] = worst_repair["% in Lot Repair"].round(1).astype(str) + "%"
        st.dataframe(worst_repair, use_container_width=True)
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
            "% in Lot Repair": region_lr["pct"].round(1).astype(str) + "%"
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True)

    with tab5:
        worst_sold = (
            ranking_df[ranking_df["frontline"] > 0]
            .nsmallest(10, "pct_lot_sold_7d")[
                ["parentcostcenterdesc", "sourcingregion", "prefrontlineprocess", "last7dayssales", "last7daysfrontline", "last7daysfresh", "pct_lot_sold_7d", "pct_fresh_7d"]
            ]
            .reset_index(drop=True)
        )
        worst_sold.index += 1
        worst_sold.columns = ["Store", "Region", "PFP", "7d Net Sales", "Frontline Last 7 Days", "Fresh (<=7 Days)", "% Lot Sold (7d)", "% Fresh (<=7d)"]
        worst_sold["PFP"] = worst_sold["PFP"].fillna(0).astype(int)
        worst_sold["% Lot Sold (7d)"] = worst_sold["% Lot Sold (7d)"].round(1).astype(str) + "%"
        worst_sold["% Fresh (<=7d)"] = worst_sold["% Fresh (<=7d)"].round(1).astype(str) + "%"
        st.dataframe(worst_sold, use_container_width=True)
        # Company aggregate
        co_sales = ranking_df["last7dayssales"].sum()
        co_fl7 = ranking_df["last7daysfrontline"].sum()
        co_fresh = ranking_df["last7daysfresh"].sum()
        co_pct_sold = (co_sales / co_fl7 * 100) if co_fl7 > 0 else 0
        co_pct_fresh = (co_fresh / co_fl7 * 100) if co_fl7 > 0 else 0
        company_row = pd.DataFrame([{
            "Store": "COMPANY TOTAL", "Region": "", "PFP": "",
            "7d Net Sales": int(co_sales), "Frontline Last 7 Days": int(co_fl7),
            "Fresh (<=7 Days)": int(co_fresh),
            "% Lot Sold (7d)": f"{co_pct_sold:.1f}%",
            "% Fresh (<=7d)": f"{co_pct_fresh:.1f}%"
        }])
        st.dataframe(company_row, use_container_width=True, hide_index=True)
        # Region aggregates
        region_sold = ranking_df.groupby("sourcingregion").agg(
            last7dayssales=("last7dayssales", "sum"), last7daysfrontline=("last7daysfrontline", "sum"),
            last7daysfresh=("last7daysfresh", "sum")
        ).reset_index()
        region_sold["pct_sold"] = (region_sold["last7dayssales"] / region_sold["last7daysfrontline"].replace(0, pd.NA) * 100).fillna(0)
        region_sold["pct_fresh"] = (region_sold["last7daysfresh"] / region_sold["last7daysfrontline"].replace(0, pd.NA) * 100).fillna(0)
        region_display = pd.DataFrame({
            "Region": region_sold["sourcingregion"],
            "7d Net Sales": region_sold["last7dayssales"].astype(int),
            "Frontline Last 7 Days": region_sold["last7daysfrontline"].astype(int),
            "Fresh (<=7 Days)": region_sold["last7daysfresh"].astype(int),
            "% Lot Sold (7d)": region_sold["pct_sold"].round(1).astype(str) + "%",
            "% Fresh (<=7d)": region_sold["pct_fresh"].round(1).astype(str) + "%"
        })
        st.dataframe(region_display, use_container_width=True, hide_index=True)

    with tab6:
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

    with tab2:
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

    with tab8:
        model_detail = (
            df_filtered[df_filtered["frontline"] > 0]
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
        # Add store total frontline and % of frontline
        store_totals = model_detail.groupby("parentcostcenterdesc")["frontline"].transform("sum")
        model_detail["store_total_frontline"] = store_totals
        model_detail["pct_of_frontline"] = (model_detail["frontline"] / store_totals * 100).round(1)
        model_detail["finalmerchmix_pct"] = pd.to_numeric(model_detail["finalmerchmix"], errors="coerce") * 100
        model_detail["over_under"] = (model_detail["pct_of_frontline"] - model_detail["finalmerchmix_pct"]).round(1)
        model_detail = model_detail.sort_values("pct_of_frontline", ascending=False).reset_index(drop=True)
        model_detail_display = model_detail[["parentcostcenterdesc", "commonmodel", "frontline", "store_total_frontline", "pct_of_frontline", "finalmerchmix_pct", "over_under"]].copy()
        model_detail_display.index += 1
        model_detail_display.columns = ["Store", "Model", "Frontline", "Store Total Frontline", "% of Frontline", "Final Merch Mix", "Over/Under"]

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

        model_detail_display["% of Frontline"] = model_detail_display["% of Frontline"].astype(str) + "%"
        model_detail_display["Final Merch Mix"] = model_detail_display["Final Merch Mix"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        model_detail_display["Over/Under"] = model_detail_display["Over/Under"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A")
        st.dataframe(model_detail_display, use_container_width=True)

    with tab9:
        # For each store, find the model with the highest % of frontline
        store_model_pct = (
            df_filtered[df_filtered["frontline"] > 0]
            .groupby(["parentcostcenterdesc", "commonmodel"])
            .agg(frontline=("frontline", "sum"))
            .reset_index()
        )
        store_model_pct["store_total"] = store_model_pct.groupby("parentcostcenterdesc")["frontline"].transform("sum")
        store_model_pct["pct_of_frontline"] = (store_model_pct["frontline"] / store_model_pct["store_total"] * 100).round(1)
        top_model = store_model_pct.loc[store_model_pct.groupby("parentcostcenterdesc")["pct_of_frontline"].idxmax()].reset_index(drop=True)
        top_model = top_model.sort_values("pct_of_frontline", ascending=False).reset_index(drop=True)
        top_model.index += 1
        top_model = top_model[["parentcostcenterdesc", "commonmodel", "frontline", "store_total", "pct_of_frontline"]]
        top_model.columns = ["Store", "Top Model", "Model Frontline", "Store Total Frontline", "% of Frontline"]
        top_model["% of Frontline"] = top_model["% of Frontline"].astype(str) + "%"
        st.dataframe(top_model, use_container_width=True)

    with tab10:
        # Store-level deviation: sum of absolute over/under
        deviation_data = (
            df_filtered[df_filtered["frontline"] > 0]
            .groupby(["parentcostcenterdesc", "commonmodel"])
            .agg(
                sourcingregion=("sourcingregion", "first"),
                frontline=("frontline", "sum"),
                finalmerchmix=("finalmerchmix", "first"),
            )
            .reset_index()
        )
        dev_store_totals = deviation_data.groupby("parentcostcenterdesc")["frontline"].transform("sum")
        deviation_data["pct_of_frontline"] = (deviation_data["frontline"] / dev_store_totals * 100)
        deviation_data["finalmerchmix_pct"] = pd.to_numeric(deviation_data["finalmerchmix"], errors="coerce") * 100
        deviation_data["over_under"] = (deviation_data["pct_of_frontline"] - deviation_data["finalmerchmix_pct"])
        store_deviation = (
            deviation_data[deviation_data["over_under"].notna()]
            .groupby(["parentcostcenterdesc", "sourcingregion"])
            .agg(total_deviation=("over_under", lambda x: x.abs().sum()))
            .reset_index()
            .sort_values("total_deviation", ascending=False)
            .reset_index(drop=True)
        )
        store_deviation.index += 1
        store_deviation.columns = ["Store", "Sourcing Region", "Total Deviation"]
        store_deviation["Total Deviation"] = store_deviation["Total Deviation"].round(1).astype(str) + "%"
        st.dataframe(store_deviation, use_container_width=True)

    st.divider()

    # =====================================================================
    # INVENTORY DUPLICATES - Same model/mileage bucket/distro group at a store
    # =====================================================================
    st.header("Inventory Duplicates")
    st.caption("Stores with multiple units sharing the same model, mileage bucket, and distro group on the frontline")

    if st.button("Load Duplicates Data"):
        with st.spinner("Loading duplicates data..."):
            df_dupes = load_dupes(target_date_str)

        if not df_dupes.empty:
            df_dupes.columns = [c.lower() for c in df_dupes.columns]
            # Exclude closed stores
            df_dupes = df_dupes[~df_dupes["parentcostcenterdesc"].str.upper().str.strip().isin(closed_stores)]

            if selected_region != "All":
                df_dupes = df_dupes[df_dupes["sourcingregion"] == selected_region]
            if selected_store != "All":
                df_dupes = df_dupes[df_dupes["parentcostcenterdesc"] == selected_store]

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
        else:
            st.info("No duplicate inventory found for the selected date/filter.")

    st.divider()

    # =====================================================================
    # LTS SECTION
    # =====================================================================
    st.header("Lead-to-Sale (LTS) Info")
    lts_data = (
        store_summary[store_summary["lts"].notna()]
        .sort_values("lts", ascending=False)
        .head(20)[["parentcostcenterdesc", "lts", "lts_budget", "frontline", "pct_optimum"]]
        .copy()
    )
    if not lts_data.empty:
        lts_data["lts_pct"] = lts_data["lts"].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
        lts_data["lts_budget_pct"] = lts_data["lts_budget"].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
        lts_display = lts_data[["parentcostcenterdesc", "lts_pct", "lts_budget_pct", "frontline", "pct_optimum"]].copy()
        lts_display.columns = ["Store", "LTS (Actual)", "LTS (Budget)", "Frontline", "% to Optimum"]
        lts_display["% to Optimum"] = lts_display["% to Optimum"].round(1)
        st.dataframe(lts_display.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No LTS data available for the selected date/filter.")

    st.divider()

    # =====================================================================
    # MERCH MIX DEVIATION
    # =====================================================================
    st.header("Merch Mix Deviation (Actual vs Target)")
    st.caption("Each store/model's actual % of frontline vs target merch mix, sorted by largest absolute deviation")

    if "finalmerchmix" in df_filtered.columns:
        mix_df = (
            df_filtered[
                (df_filtered["frontline"] > 0)
                & (df_filtered["commonmodel"].notna())
                & (df_filtered["finalmerchmix"].notna())
            ]
            .groupby(["parentcostcenterdesc", "sourcingregion", "commonmodel"])
            .agg(
                frontline=("frontline", "sum"),
                finalmerchmix=("finalmerchmix", "first"),
            )
            .reset_index()
        )
        store_totals = mix_df.groupby("parentcostcenterdesc")["frontline"].transform("sum")
        mix_df["pct_of_frontline"] = (mix_df["frontline"] / store_totals * 100)
        mix_df["target_pct"] = pd.to_numeric(mix_df["finalmerchmix"], errors="coerce") * 100
        mix_df["deviation"] = mix_df["pct_of_frontline"] - mix_df["target_pct"]

        mix_display = (
            mix_df[["parentcostcenterdesc", "sourcingregion", "commonmodel", "pct_of_frontline", "target_pct", "deviation"]]
            .sort_values("deviation", key=abs, ascending=False)
            .reset_index(drop=True)
        )
        mix_display.columns = ["Store", "Sourcing Region", "Model", "% of Frontline", "Final Merch Mix", "Deviation"]
        mix_display["% of Frontline"] = mix_display["% of Frontline"].round(1).astype(str) + "%"
        mix_display["Final Merch Mix"] = mix_display["Final Merch Mix"].round(1).astype(str) + "%"
        mix_display["Deviation"] = mix_display["Deviation"].round(1).astype(str) + "%"
        st.dataframe(mix_display, use_container_width=True, hide_index=True)
    else:
        st.info("No merch mix target data available for the current filter.")

    st.divider()

    # =====================================================================
    # 7-DAY SALES FORECAST
    # =====================================================================
    st.header("7-Day Sales Forecast")
    forecast_df = store_summary[store_summary["forecast_7d_sales"] > 0][
        ["parentcostcenterdesc", "today", "day1", "day2", "day3", "day4", "day5", "day6", "forecast_7d_sales", "frontline"]
    ].sort_values("forecast_7d_sales", ascending=False).head(20).copy()
    if not forecast_df.empty:
        forecast_df.columns = ["Store", "Today", "Day+1", "Day+2", "Day+3", "Day+4", "Day+5", "Day+6", "7d Total", "Frontline"]
        forecast_df = forecast_df.reset_index(drop=True)
        forecast_df.index += 1
        st.dataframe(forecast_df, use_container_width=True)

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

            for c in ["frontline", "dealeroptimum", "lotrepair", "sales", "website_units", "duplicate_units", "merch_deviation"]:
                if c in df_trend.columns:
                    df_trend[c] = pd.to_numeric(df_trend[c], errors="coerce").fillna(0)

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
                chart3 = daily[["calendardate", "sales"]].set_index("calendardate")
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
                chart8 = daily[["calendardate", "pct_frontline_sold"]].set_index("calendardate")
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
