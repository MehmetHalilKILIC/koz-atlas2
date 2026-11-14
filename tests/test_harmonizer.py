import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import pytest
from harmonizer import *

def sample():
    return pd.DataFrame([dict(latitude=37,longitude=41.0,acq_date='2025-01-01',acq_time='0030',instrument='MODIS',satellite='Terra',confidence='80',frp=10),dict(latitude=37.001,longitude=41.0,acq_date='2025-01-01',acq_time='0045',instrument='VIIRS',satellite='N20',confidence='n',frp=4)])

def test_haversine():
    assert haversine(0,0,0,0)==0
    assert haversine(0,0,0,1)==pytest.approx(111.195,rel=.0001)

def test_parse_and_rejection():
    r=sample(); r.loc[2]=r.loc[0]; r.loc[2,'acq_time']='2500'; r.loc[3]=r.loc[1]; r.loc[3,'confidence']='l'; r.loc[3,'latitude']=38
    d,a=normalize(r)
    assert len(d)==2 and a['invalid']==1 and a['confidence_filtered']==1
    assert d.utc_timestamp.iloc[0].hour==0 and d.utc_timestamp.iloc[0].minute==30

def test_exact_duplicates():
    r=sample(); r=pd.concat([r,r.iloc[[0]]]); d,a=normalize(r)
    assert a['exact_duplicates']==1 and len(d)==2

def test_match_no_sensor_double_sum():
    d,_=normalize(sample()); e=harmonize(d)
    assert len(e)==1 and e.iloc[0].merged_pixel_count==2
    assert e.iloc[0].representative_frp_mw==10
    assert e.iloc[0].viirs_frp_mw==4

def test_time_separation():
    r=sample(); r.loc[1,'acq_time']='0200'; d,_=normalize(r)
    assert len(harmonize(d))==2

def test_no_transitive_time_chain():
    r=sample(); r.loc[1,'acq_time']='0130'; r.loc[2]=r.loc[1]; r.loc[2,'acq_time']='0230'
    d,_=normalize(r); e=harmonize(d,minutes=60)
    assert len(e)==2 and e.merged_pixel_count.sum()==3

def test_no_transitive_spatial_chain():
    r=sample(); r.loc[0,'longitude']=41; r.loc[1,'longitude']=41.01; r.loc[2]=r.loc[1]; r.loc[2,'longitude']=41.02
    d,_=normalize(r); e=harmonize(d,radius_km=1.2)
    assert len(e)==2

def test_empty():
    d,_=normalize(sample().iloc[:0]); e=harmonize(d)
    assert persistence(e).empty and calibrate(e,True)[0].empty

def test_zero_frp_centroid():
    r=sample(); r.frp=0; d,_=normalize(r); e=harmonize(d)
    assert np.isfinite(e.latitude).all()

def test_demo_static_and_lineage():
    d,_=normalize(demo_data()); e=persistence(harmonize(d))
    assert e.is_static_candidate.any()
    members=[int(x) for s in e.member_ids for x in s.split(',')]
    assert sorted(members)==list(range(len(d)))
    assert e.hotspot_id.is_unique
    out,report=calibrate(e,True)
    assert report['pairs']>=20 and report['test']>0 and report['train']>0
    assert out.calibrated_frp_mw.notna().all()

def test_repetition_not_enough_in_one_month():
    e=pd.DataFrame(dict(latitude=[37]*6,longitude=[41]*6,utc_timestamp=pd.date_range('2025-01-01',periods=6,tz='UTC')))
    assert not persistence(e).is_static_candidate.any()

def test_api_chunking(monkeypatch):
    calls=[]
    class Response:
        text=sample().to_csv(index=False)
        def raise_for_status(self): return None
    def get(url,timeout): calls.append(url); return Response()
    monkeypatch.setattr(requests,'get',get)
    fetch_firms('test','MODIS_NRT',PRESETS['Türkiye'],'2025-01-01','2025-01-12')
    assert [u.split('/')[-2:] for u in calls]==[['5','2025-01-01'],['5','2025-01-06'],['2','2025-01-11']]

def test_api_error_never_exposes_key(monkeypatch):
    def get(*a,**k): raise RuntimeError('secret-key')
    monkeypatch.setattr(requests,'get',get)
    with pytest.raises(ValueError) as err: fetch_firms('secret-key','MODIS_NRT',PRESETS['Türkiye'],'2025-01-01','2025-01-02')
    assert 'secret-key' not in str(err.value)
