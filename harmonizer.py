"""KÖZ Atlas: exploratory hotspot grouping, not validated fire-event inference."""
from io import StringIO
from urllib.parse import quote
import hashlib
import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree

R = 6371.0
SOURCES = ['MODIS_NRT', 'MODIS_SP', 'VIIRS_SNPP_NRT', 'VIIRS_SNPP_SP',
           'VIIRS_NOAA20_NRT', 'VIIRS_NOAA20_SP', 'VIIRS_NOAA21_NRT', 'VIIRS_NOAA21_SP']
PRESETS = {'Türkiye': (25.6,35.8,44.8,42.1), 'Batman ve Güneydoğu': (37,36.5,43,38.8),
           'Akdeniz ve Ege': (26,35.8,36.5,39.5)}


def haversine(lat1, lon1, lat2, lon2):
    a,b,c,d = map(np.radians, (lat1,lon1,lat2,lon2))
    h = np.sin((c-a)/2)**2 + np.cos(a)*np.cos(c)*np.sin((d-b)/2)**2
    return 2*R*np.arcsin(np.sqrt(np.clip(h,0,1)))


def xyz(frame):
    lat,lon = np.radians(frame[['latitude','longitude']].to_numpy()).T
    return np.c_[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]


def normalize(raw, minimum='nominal'):
    """Preserve sensor confidence semantics; categories are NOT probabilities."""
    d=raw.copy()
    d.columns=d.columns.str.strip().str.lower()
    required={'latitude','longitude','acq_date','acq_time','confidence','frp','instrument'}
    missing=required-set(d.columns)
    if missing: raise ValueError('Eksik sütunlar: '+', '.join(sorted(missing)))
    for c in ['latitude','longitude','frp']: d[c]=pd.to_numeric(d[c],errors='coerce')
    d['instrument']=d.instrument.astype(str).str.upper().str.strip()
    if 'satellite' not in d: d['satellite']='unknown'
    d['satellite']=d.satellite.fillna('unknown').astype(str)
    time=d.acq_time.astype(str).str.replace(r'\.0$','',regex=True).str.zfill(4)
    valid_time=time.str.fullmatch(r'\d{4}') & (pd.to_numeric(time.str[:2],errors='coerce')<24) & (pd.to_numeric(time.str[2:],errors='coerce')<60)
    d['utc_timestamp']=pd.to_datetime(d.acq_date.astype(str)+' '+time,format='%Y-%m-%d %H%M',errors='coerce',utc=True).where(valid_time)
    conf=d.confidence.astype(str).str.lower().str.strip()
    num=pd.to_numeric(conf,errors='coerce')
    ranks=pd.Series(np.nan,index=d.index)
    m=d.instrument.eq('MODIS') & num.between(0,100)
    ranks.loc[m]=np.select([num[m]<30,num[m]<80],[0,1],default=2)
    v=d.instrument.eq('VIIRS')
    ranks.loc[v]=conf[v].map({'l':0,'n':1,'h':2,'low':0,'nominal':1,'high':2})
    d['confidence_rank']=ranks
    valid=d.latitude.between(-90,90)&d.longitude.between(-180,180)&d.frp.ge(0)&d.utc_timestamp.notna()&ranks.notna()
    invalid=int((~valid).sum())
    d=d[valid].copy()
    before=len(d)
    # Only exact observation identities are deduplicated; satellites stay distinct.
    d=d.drop_duplicates(['latitude','longitude','utc_timestamp','satellite','instrument','frp'])
    duplicates=before-len(d)
    cutoff={'low':0,'nominal':1,'high':2}[minimum]
    low=int((d.confidence_rank<cutoff).sum())
    d=d[d.confidence_rank>=cutoff].sort_values(['utc_timestamp','instrument','latitude','longitude','satellite']).reset_index(drop=True)
    return d,{'input':len(raw),'invalid':invalid,'exact_duplicates':duplicates,'confidence_filtered':low,'accepted':len(d)}


def fetch_firms(key, source, bbox, start, end):
    if source not in SOURCES: raise ValueError('Desteklenmeyen FIRMS ürünü.')
    if not key.strip(): raise ValueError('NASA MAP_KEY gerekli.')
    west,south,east,north=map(float,bbox)
    if not (-180<=west<east<=180 and -90<=south<north<=90): raise ValueError('Koordinat kutusu geçersiz.')
    start,end=pd.Timestamp(start),pd.Timestamp(end)
    if end<start or (end-start).days>365: raise ValueError('API aralığı 1–366 gün olmalı.')
    frames=[]
    cursor=start
    while cursor<=end:
        days=min(5,(end-cursor).days+1)
        url=f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{quote(key.strip(),safe="")}/{source}/{west},{south},{east},{north}/{days}/{cursor:%Y-%m-%d}'
        try:
            response=requests.get(url,timeout=45)
            response.raise_for_status()
            frame=pd.read_csv(StringIO(response.text),dtype={'acq_time':str})
        except Exception:
            raise ValueError('FIRMS isteği başarısız. Anahtar, kota, bağlantı ve ürün tarih kapsamını kontrol edin.') from None
        if 'latitude' not in frame: raise ValueError('FIRMS CSV döndürmedi; anahtarı ve veri erişimini kontrol edin.')
        if 'instrument' not in frame: frame['instrument']='MODIS' if source.startswith('MODIS') else 'VIIRS'
        frame['source_product']=source
        frames.append(frame)
        cursor+=pd.Timedelta(days=days)
    return pd.concat(frames,ignore_index=True)


def harmonize(d, radius_km=1.2, minutes=60):
    """Deterministic complete-link groups: all pairs obey both limits; no chaining."""
    if radius_km<=0 or minutes<0: raise ValueError('Eşikler geçersiz.')
    columns=['hotspot_id','latitude','longitude','utc_timestamp','source','merged_pixel_count','modis_frp_mw','viirs_frp_mw','representative_frp_mw','member_ids']
    if d.empty: return pd.DataFrame(columns=columns)
    d=d.reset_index(drop=True)
    tree=cKDTree(xyz(d)); used=set(); rows=[]
    ts=d.utc_timestamp.astype('int64').to_numpy()/60e9
    for i in range(len(d)):
        if i in used: continue
        group=[i]; used.add(i)
        neighbors=tree.query_ball_point(xyz(d.iloc[[i]])[0],2*np.sin(radius_km/(2*R)))
        for j in sorted(neighbors):
            if j in used or abs(ts[j]-ts[i])>minutes: continue
            g=d.iloc[group]
            if np.all(np.abs(ts[group]-ts[j])<=minutes) and np.all(haversine(g.latitude.to_numpy(),g.longitude.to_numpy(),d.iloc[j].latitude,d.iloc[j].longitude)<=radius_km+1e-9):
                group.append(j); used.add(j)
        g=d.iloc[group]
        w=g.frp.to_numpy(); w=w if w.sum()>0 else np.ones(len(g))
        # Aggregate only within a sensor/satellite/exact acquisition; median across passes.
        passes=g.groupby(['instrument','satellite','utc_timestamp']).frp.sum()
        m=float(passes.loc['MODIS'].median()) if 'MODIS' in g.instrument.values else np.nan
        v=float(passes.loc['VIIRS'].median()) if 'VIIRS' in g.instrument.values else np.nan
        sensor='BOTH (MODIS+VIIRS)' if np.isfinite(m) and np.isfinite(v) else ('MODIS_ONLY' if np.isfinite(m) else 'VIIRS_CLUSTER_HARMONIZED')
        identity=g[['latitude','longitude','utc_timestamp','satellite','instrument']].to_csv(index=False)
        center=np.average(xyz(g),axis=0,weights=w)
        rows.append(dict(hotspot_id='KOZ-'+hashlib.sha256(identity.encode()).hexdigest()[:12],latitude=np.degrees(np.arctan2(center[2],np.hypot(center[0],center[1]))),longitude=np.degrees(np.arctan2(center[1],center[0])),utc_timestamp=g.utc_timestamp.min(),source=sensor,merged_pixel_count=len(g),modis_frp_mw=m,viirs_frp_mw=v,representative_frp_mw=m if np.isfinite(m) else v,member_ids=','.join(map(str,group))))
    return pd.DataFrame(rows)


def persistence(events, radius_km=1., minimum_days=5, minimum_months=3):
    """Recurrence is only a candidate flag, never industrial/biomass ground truth."""
    e=events.copy()
    e['persistent_days']=0; e['persistent_months']=0; e['is_static_candidate']=False
    if e.empty: return e
    coords=xyz(e); tree=cKDTree(coords)
    for i,point in enumerate(coords):
        ids=tree.query_ball_point(point,2*np.sin(radius_km/(2*R)))
        dates=e.iloc[ids].utc_timestamp
        days=dates.dt.date.nunique(); months=dates.dt.strftime('%Y-%m').nunique()
        e.loc[i,['persistent_days','persistent_months','is_static_candidate']]=[days,months,days>=minimum_days and months>=minimum_months]
    return e


def calibrate(events, enabled=False):
    """Experimental scale fit with chronological holdout; not a validated correction."""
    e=events.copy(); e['calibrated_frp_mw']=np.nan
    report={'status':'Uygulanmadı','pairs':0}
    if not enabled or e.empty: return e,report
    p=e[e.modis_frp_mw.gt(0)&e.viirs_frp_mw.gt(0)].sort_values('utc_timestamp')
    report['pairs']=len(p)
    days=sorted(p.utc_timestamp.dt.date.unique())
    if len(p)<20 or len(days)<5:
        report['status']='Yetersiz eşleşme: en az 20 çift ve 5 gün gerekli'
        return e,report
    cutoff=days[max(1,int(len(days)*.7))]
    train=p[p.utc_timestamp.dt.date<cutoff]; test=p[p.utc_timestamp.dt.date>=cutoff]
    x=train.viirs_frp_mw.to_numpy(); y=train.modis_frp_mw.to_numpy()
    scale=float(np.dot(x,y)/np.dot(x,x))
    pred=test.viirs_frp_mw*scale
    report.update(status='Deneysel; bağımsız bilimsel doğrulama değildir',scale=scale,train=len(train),test=len(test),holdout_mae_mw=float(np.abs(pred-test.modis_frp_mw).mean()),baseline_mae_mw=float(np.abs(test.viirs_frp_mw-test.modis_frp_mw).mean()))
    e['calibrated_frp_mw']=e.viirs_frp_mw*scale
    return e,report


def demo_data():
    """Deterministic synthetic observations. NEVER NASA observations."""
    rng=np.random.default_rng(42); rows=[]
    def add(lat,lon,t,instrument,frp,satellite):
        rows.append(dict(latitude=lat,longitude=lon,acq_date=t.strftime('%Y-%m-%d'),acq_time=t.strftime('%H%M'),satellite=satellite,instrument=instrument,confidence=85 if instrument=='MODIS' else 'n',frp=round(frp,3),scan=1 if instrument=='MODIS' else .375,track=1 if instrument=='MODIS' else .375,daynight='D',version='SYNTHETIC',provenance='SYNTHETIC_DEMO_NOT_NASA'))
    for year in [2023,2024,2025]:
        for month in range(1,13):
            for day in [5,15,25]:
                t=pd.Timestamp(year,month,day,10)
                centers=[(37.88,41.13)]
                centers += [(float(rng.uniform(36.3,38.5)),float(rng.choice([28.,30.,40.,41.]))+float(rng.uniform(-.1,.1))) for _ in range(3 if month in [6,7,8,9] else 1)]
                for lat,lon in centers:
                    frp=float(rng.uniform(4,45)); add(lat,lon,t,'MODIS',frp,'Terra')
                    for _ in range(3): add(lat+rng.normal(0,.001),lon+rng.normal(0,.001),t+pd.Timedelta(minutes=15),'VIIRS',frp/3*rng.uniform(.8,1.2),'N20')
    return pd.DataFrame(rows)
