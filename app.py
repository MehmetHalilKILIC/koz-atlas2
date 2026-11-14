from datetime import date, timedelta
import json
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
from harmonizer import PRESETS,SOURCES,demo_data,fetch_firms,normalize,harmonize,persistence,calibrate

st.set_page_config(page_title='KÖZ Atlas | Kirvecanlar',page_icon='🔥',layout='wide')
st.markdown('''<style>.stApp{background:#0B0F19;color:#E2E8F0} [data-testid="stMetric"]{background:#1E293B;padding:18px;border-radius:12px;border-top:2px solid #FF5722} h1{letter-spacing:-2px} .eyebrow{color:#FF9800;font-size:13px;letter-spacing:3px} </style>''',unsafe_allow_html=True)
st.markdown('<div class="eyebrow">KİRVECANLAR / UYDU GÖZLEM LABORATUVARI</div>',unsafe_allow_html=True)
st.title('KÖZ Atlas')
st.write('MODIS ve VIIRS gözlemlerini ortak bir haritada, takvimde ve izlenebilir tabloda inceleyin.')
with st.sidebar:
    st.header('Gözlem ayarları')
    region=st.selectbox('Bölge',list(PRESETS)+['Özel koordinat kutusu'])
    bbox=PRESETS.get(region,PRESETS['Türkiye'])
    if region=='Özel koordinat kutusu':
        bbox=tuple(st.number_input(label,value=float(value)) for label,value in zip(['Batı','Güney','Doğu','Kuzey'],bbox))
    mode=st.radio('Veri kaynağı',['Sentetik demo','CSV yükle','NASA FIRMS API'])
    if mode=='Sentetik demo':
        st.caption('2023–2025 tarihli kurgusal test kayıtları; gerçek yangın verisi değildir.')
        raw=demo_data(); provenance='SYNTHETIC_DEMO_NOT_NASA'
    elif mode=='CSV yükle':
        uploads=st.file_uploader('NASA MODIS / VIIRS CSV dosyaları',type='csv',accept_multiple_files=True)
        if not uploads: st.info('Başlamak için CSV yükleyin.'); st.stop()
        try: raw=pd.concat([pd.read_csv(f,dtype={'acq_time':str}) for f in uploads],ignore_index=True)
        except Exception: st.error('CSV okunamadı. Dosya biçimini kontrol edin.'); st.stop()
        provenance='USER_UPLOADED_UNVERIFIED'
    else:
        key=st.text_input('NASA MAP_KEY',type='password')
        products=st.multiselect('FIRMS ürünleri',SOURCES,default=['MODIS_NRT','VIIRS_NOAA20_NRT'])
        start=st.date_input('Başlangıç',date.today()-timedelta(days=2))
        end=st.date_input('Bitiş',date.today())
        if st.button('NASA verilerini getir',type='primary'):
            if not products: st.error('En az bir ürün seçin.')
            else:
                try:
                    with st.spinner('FIRMS verileri alınıyor…'):
                        st.session_state['firms_data']=pd.concat([fetch_firms(key,s,bbox,start,end) for s in products],ignore_index=True)
                        st.session_state['firms_meta']={'products':products,'bbox':bbox,'start':str(start),'end':str(end)}
                except ValueError as exc: st.error(str(exc))
        if 'firms_data' not in st.session_state: st.info('Anahtar ve ürün seçerek verileri getirin.'); st.stop()
        raw=st.session_state['firms_data']; provenance='NASA_FIRMS_API'
        st.caption('Yüklü sorgu: '+json.dumps(st.session_state['firms_meta'],ensure_ascii=False))
    confidence=st.select_slider('Minimum güven sınıfı',['low','nominal','high'],value='nominal')
    radius=st.slider('Eşleştirme mesafesi (km)',.5,2.5,1.2,.1)
    minutes=st.slider('En büyük zaman farkı (dakika)',0,180,60,5)
    exclude=st.toggle('Kalıcı kaynak adaylarını gizle',False)
    experimental=st.toggle('Deneysel FRP ölçeklemesi',False)
    st.caption('Güven sınıfları olasılık değildir. Eşikler proje varsayımıdır.')
try:
    d,audit=normalize(raw,confidence)
    w,s,e,n=bbox
    if not (-180<=w<e<=180 and -90<=s<n<=90): raise ValueError('Koordinat kutusu geçersiz.')
    d=d[d.longitude.between(w,e)&d.latitude.between(s,n)].reset_index(drop=True)
except ValueError as exc: st.error(str(exc)); st.stop()
if d.empty: st.warning('Filtrelerden geçen kayıt yok.'); st.stop()
lo,hi=d.utc_timestamp.min().date(),d.utc_timestamp.max().date()
selected=st.date_input('Analiz tarih aralığı',value=(lo,hi),min_value=lo,max_value=hi)
if len(selected)!=2: st.info('Başlangıç ve bitiş tarihini seçin.'); st.stop()
d=d[d.utc_timestamp.dt.date.between(*selected)].reset_index(drop=True)
if d.empty: st.warning('Seçilen tarihlerde kayıt yok.'); st.stop()
with st.spinner('Gözlemler eşleştiriliyor…'):
    all_events=persistence(harmonize(d,radius,minutes))
    all_events,calibration=calibrate(all_events,experimental)
events=all_events[~all_events.is_static_candidate].copy() if exclude else all_events.copy()
st.caption('NASA Space Apps Challenge • Batman • Takımın bildirdiği etkinlik: 14–15 Kasım 2026')
if mode=='Sentetik demo': st.warning('SENTETİK DEMO — tüm sayılar algoritma gösterimi içindir; NASA ölçümü veya doğrulanmış performans sonucu değildir.')
st.info('Çıktılar gözlem kümeleridir; yangın adedi veya yanmış alan değildir. Kalıcılık, endüstriyel kaynak olduğunun kanıtı değildir.')
cols=st.columns(5)
for c,label,value in zip(cols,['Kabul edilen gözlem','Gözlem kümesi','Kayıt birleştirme','Kalıcı aday kümesi','Temsili FRP · MW'],[len(d),len(all_events),f'{100*(1-len(all_events)/len(d)):.1f}%',int(all_events.is_static_candidate.sum()),f'{events.representative_frp_mw.mean():.1f}' if len(events) else '—']): c.metric(label,value)
st.caption('Küme sayısı ve birleştirme oranı gizleme öncesidir. FRP görünür kümelerin ortalamasıdır; aynı olayı ölçen sensörler birbirine eklenmez.')
tabs=st.tabs(['01 / CBS Haritası','02 / Aktivite Takvimi','03 / Sensör Analitiği','04 / Veri İndirme'])
with tabs[0]:
    selected_layers=st.multiselect('Harita katmanları',['MODIS','VIIRS','Kümeler','Kalıcı adaylar'],default=['Kümeler','Kalıcı adaylar'])
    layers=[]
    for name,frame,color,size in [('MODIS',d[d.instrument.eq('MODIS')],[255,152,0],500),('VIIRS',d[d.instrument.eq('VIIRS')],[56,189,248],187.5),('Kümeler',events,[255,87,34],250),('Kalıcı adaylar',events[events.is_static_candidate],[192,132,252],400)]:
        if name not in selected_layers or frame.empty: continue
        view=frame.copy(); view['label']=name
        view['detail']=view.hotspot_id if 'hotspot_id' in view else view.instrument+' / '+view.satellite
        view['when']=view.utc_timestamp.astype(str)
        layers.append(pdk.Layer('ScatterplotLayer',data=view[['latitude','longitude','label','detail','when']],get_position='[longitude, latitude]',get_fill_color=color,get_radius=size,pickable=True,radius_min_pixels=3))
    st.pydeck_chart(pdk.Deck(layers=layers,initial_view_state=pdk.ViewState(latitude=float(d.latitude.mean()),longitude=float(d.longitude.mean()),zoom=5),map_style='https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',tooltip={'text':'{label}\n{detail}\n{when}'}))
    st.caption('Çemberler nominal çözünürlüğün sembolik gösterimidir; gerçek piksel ayak izi değildir. Altlık haritası internet gerektirir.')
with tabs[1]:
    if events.empty: st.info('Görünür küme yok.')
    else:
        z=events.assign(year=events.utc_timestamp.dt.year,month=events.utc_timestamp.dt.month)
        matrix=z.groupby(['year','month']).size().unstack().reindex(columns=range(1,13))
        st.plotly_chart(px.imshow(matrix,labels={'x':'Ay','y':'Yıl','color':'Küme'},color_continuous_scale='Oranges',aspect='auto'),width='stretch')
        daily=events.set_index('utc_timestamp').resample('D').size().rename('Küme').reset_index()
        st.plotly_chart(px.bar(daily,x='utc_timestamp',y='Küme',color_discrete_sequence=['#FF5722']),width='stretch')
        st.caption('Boş aylar veri kapsamı bilinmediği için 0 kabul edilmez. Günlük aradaki sıfırlar yalnızca yüklenen kayıtlarda tespit olmamasıdır.')
        coverage=st.checkbox('Karşılaştırılan tam ayların veri kapsamını dışarıdan doğruladım',False)
        if coverage:
            month=st.selectbox('Karşılaştırma ayı',sorted(z.month.unique()))
            counts=z[z.month.eq(month)].groupby('year').size()
            latest=int(z.year.max())
            if latest in counts and len(counts[counts.index<latest])>=3:
                med=float(counts[counts.index<latest].median()); current=int(counts.loc[latest])
                st.metric(f'{latest} / {month} — önceki yılların medyanına göre',f'{(current/med-1)*100:+.1f}%' if med else 'Tanımsız')
            else: st.info('Aynı ay için mevcut yıl ve en az üç önceki yıl gerekli.')
        else: st.caption('Tarihsel anomali, karşılaştırılabilir veri kapsamı onaylanmadan hesaplanmaz.')
with tabs[2]:
    raw_daily=d.groupby(d.utc_timestamp.dt.floor('D')).size().rename('Ham gözlem')
    clustered=all_events.groupby(all_events.utc_timestamp.dt.floor('D')).size().rename('Küme')
    st.plotly_chart(px.line(pd.concat([raw_daily,clustered],axis=1),color_discrete_sequence=['#38BDF8','#FF5722']),width='stretch')
    pairs=all_events.dropna(subset=['modis_frp_mw','viirs_frp_mw'])
    if len(pairs): st.plotly_chart(px.scatter(pairs,x='viirs_frp_mw',y='modis_frp_mw',color_discrete_sequence=['#FF9800']),width='stretch')
    st.write('FRP kalibrasyon durumu'); st.json(calibration)
    st.caption('Ham/küme farkı doğruluk kazancı değildir. FRP toplamı güçtür (MW), enerji değildir. 375 m/750 m VIIRS ürün yapısı nedeniyle toplama fiziksel doğrulama gerektirir.')
with tabs[3]:
    exported=events.assign(provenance=provenance,radius_km=radius,time_window_minutes=minutes)
    st.download_button('Küme CSV indir',exported.to_csv(index=False).encode('utf-8-sig'),'koz_atlas_harmonized_hotspots.csv','text/csv')
    st.download_button('Gözlem ve üye indeksi CSV indir',d.reset_index(names='member_id').to_csv(index=False).encode('utf-8-sig'),'koz_atlas_observations.csv','text/csv')
    meta={'provenance':provenance,'normalization_audit':audit,'bbox':bbox,'radius_km':radius,'minutes':minutes,'confidence':confidence,'calibration':calibration,'static_rule':'1 km; >=5 distinct days and >=3 distinct year-months','static_history_scope':'selected loaded date range only'}
    st.download_button('İşlem kaydı JSON indir',json.dumps(meta,ensure_ascii=False,indent=2).encode(),'koz_atlas_audit.json','application/json')
    st.dataframe(exported,width='stretch',hide_index=True)
st.divider()
st.caption('Kirvecanlar • Mehmet Halil KILIÇ — Veri mühendisliği | İbrahim Halil BİRLİK — Backend ve CBS | Mirze KARA — Analitik ve sunum')
st.markdown('[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) · [Veri tanımları](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html)')
