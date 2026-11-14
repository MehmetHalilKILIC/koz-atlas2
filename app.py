with tab3:
    c_map, c_proof = st.columns([1.45, 1])
    with c_map:
        # Harita Üst Kontrol Çubuğu
        m_ctrl1, m_ctrl2, m_ctrl3 = st.columns([1.3, 1.1, 1.1])
        with m_ctrl1:
            base_choice = st.selectbox(
                "🗺️ Harita Altlığı",
                [
                    "🛰️ Esri Uydu + Hibrit Etiketler (Önerilen)",
                    "🌑 NASA Karanlık Görev Kontrol (Carto Dark)",
                    "🏔️ Arazi & Topografya (Esri World Topo)"
                ],
                key="tab3_base"
            )
        with m_ctrl2:
            heat_radius = st.slider("🔥 Isı Yayılım Çapı", 10, 35, 20, key="tab3_hrad")
        with m_ctrl3:
            max_pts = st.slider("📍 Maks. Nokta Sayısı", 100, 1000, 350, step=50, key="tab3_pts")

        # Merkez koordinatı dinamik belirle
        if not pairs_df.empty:
            center_lat, center_lon = float(pairs_df["latitude"].mean()), float(pairs_df["longitude"].mean())
        elif not modis_df.empty:
            center_lat, center_lon = float(modis_df["latitude"].mean()), float(modis_df["longitude"].mean())
        else:
            center_lat, center_lon = 37.88, 41.15

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles=None,
            control_scale=True,
            prefer_canvas=True
        )

        # 1. Altlık Katmanları (Seçime göre varsayılan açılır)
        show_sat = "Uydu" in base_choice
        show_dark = "Karanlık" in base_choice
        show_topo = "Topografya" in base_choice

        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery",
            name="🛰️ Uydu Görüntüsü (Esri HD)",
            max_zoom=19,
            show=show_sat
        ).add_to(m)

        folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attr="CartoDB Dark Matter",
            name="🌑 Karanlık Mod (Carto Dark)",
            max_zoom=19,
            show=show_dark
        ).add_to(m)

        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Topo",
            name="🏔️ Topografik Arazi Haritası",
            max_zoom=19,
            show=show_topo
        ).add_to(m)

        # Uydu üzerinde il/ilçe sınırları ve yolların okunması için Hibrit Etiket Katmanı
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Boundaries & Places",
            name="🏷️ İl/İlçe Sınırları ve Yer İsimleri (Hibrit)",
            overlay=True,
            show=show_sat
        ).add_to(m)

        folium.TileLayer(
            tiles="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2026-11-01/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
            attr="NASA EOSDIS GIBS",
            name="🌍 NASA GIBS TrueColor (Zoom ≤ 9)",
            max_native_zoom=9,
            max_zoom=18,
            overlay=True,
            show=False
        ).add_to(m)

        # 2. FRP Ağırlıklı Termal Isı Haritası (HeatMap) Katmanı
        fg_heat = folium.FeatureGroup(name="🔥 FRP Ağırlıklı Termal Isı Haritası", show=True)
        heat_source = pairs_df if not pairs_df.empty else pd.concat([modis_df, viirs_df], ignore_index=True)
        if not heat_source.empty:
            w_col = "aqua_frp" if "aqua_frp" in heat_source.columns else "frp"
            heat_pts = (
                heat_source[["latitude", "longitude", w_col]]
                .dropna()
                .tail(1500)
                .values.tolist()
            )
            if heat_pts:
                HeatMap(
                    heat_pts,
                    radius=heat_radius,
                    blur=15,
                    max_zoom=13,
                    min_opacity=0.35,
                    gradient={0.2: "#38bdf8", 0.45: "#facc15", 0.7: "#f97316", 1.0: "#dc2626"}
                ).add_to(fg_heat)
        fg_heat.add_to(m)

        # 3. Eşleşen Geçişler & Sensör Nokta Katmanları
        if not pairs_df.empty:
            fg_pairs = folium.FeatureGroup(name="🟢 Eşleşen Aqua MODIS + VIIRS Çiftleri", show=True)
            for _, r in pairs_df.tail(max_pts).iterrows():
                cal_str = f"{r['calibrated_frp']:.1f} MW" if "calibrated_frp" in r else "Hesaplanmadı"
                # Dış Termal Hale (Glow efekti)
                folium.CircleMarker(
                    location=[r["latitude"], r["longitude"]],
                    radius=float(np.clip(np.sqrt(r["aqua_frp"]) * 1.8, 8, 22)),
                    color="#22c55e",
                    weight=1,
                    fill=True,
                    fill_color="#22c55e",
                    fill_opacity=0.22
                ).add_to(fg_pairs)

                # Merkez Çekirdek Noktası
                popup_html = f"""
                <div style="font-family:'Inter',sans-serif; font-size:12px; width:220px; color:#0f172a;">
                    <div style="background:#16a34a; color:white; padding:4px 8px; border-radius:4px; font-weight:700; margin-bottom:6px;">
                        🛰️ EŞLEŞEN UYDU GEÇİŞİ
                    </div>
                    <b>📅 Tarih:</b> {r['date_str']}<br>
                    <b>🔥 Aqua MODIS FRP:</b> {r['aqua_frp']:.1f} MW<br>
                    <b>⚡ VIIRS Toplam FRP:</b> {r['viirs_frp_sum']:.1f} MW<br>
                    <b>🎯 Kalibre FRP:</b> {cal_str}<br>
                    <b>⏱️ Zaman Farkı:</b> {r['median_time_diff_min']:.1f} dk<br>
                    <b>📍 Koordinat:</b> {r['latitude']:.4f}, {r['longitude']:.4f}
                </div>
                """
                folium.CircleMarker(
                    location=[r["latitude"], r["longitude"]],
                    radius=5,
                    color="#ffffff",
                    weight=1.5,
                    fill=True,
                    fill_color="#22c55e",
                    fill_opacity=0.95,
                    tooltip=f"🔥 Eşleşen | {r['date_str']} | Aqua: {r['aqua_frp']:.1f} MW",
                    popup=folium.Popup(popup_html, max_width=250)
                ).add_to(fg_pairs)
            fg_pairs.add_to(m)

        # Ham MODIS ve VIIRS Noktaları (İsteğe bağlı katman kontrolünden açılıp kapatılabilir)
        fg_modis = folium.FeatureGroup(name="🔵 MODIS Ham Gözlemler (1 km)", show=pairs_df.empty)
        for _, r in modis_df.tail(max_pts // 2).iterrows():
            folium.CircleMarker(
                location=[r["latitude"], r["longitude"]],
                radius=5,
                color="#38bdf8",
                weight=1.2,
                fill=True,
                fill_color="#0284c7",
                fill_opacity=0.8,
                tooltip=f"🛰️ MODIS ({r.get('satellite', 'M')}) | {r['frp']:.1f} MW | {r['date_str']}"
            ).add_to(fg_modis)
        fg_modis.add_to(m)

        fg_viirs = folium.FeatureGroup(name="🟠 VIIRS 375m Ham Gözlemler", show=pairs_df.empty)
        for _, r in viirs_df.tail(max_pts // 2).iterrows():
            folium.CircleMarker(
                location=[r["latitude"], r["longitude"]],
                radius=3.5,
                color="#fb923c",
                weight=1,
                fill=True,
                fill_color="#ea580c",
                fill_opacity=0.8,
                tooltip=f"⚡ VIIRS ({r.get('satellite', 'V')}) | {r['frp']:.1f} MW | {r['date_str']}"
            ).add_to(fg_viirs)
        fg_viirs.add_to(m)

        # 4. Tekrarlayan / Type=2 Statik Kaynak Adayları Katmanı
        if not sites_df.empty:
            fg_sites = folium.FeatureGroup(name="🏭 Statik / Tekrarlayan Kaynak Adayları (Type=2)", show=True)
            for _, s in sites_df.head(40).iterrows():
                folium.CircleMarker(
                    location=[s["center_lat"], s["center_lon"]],
                    radius=7,
                    color="#facc15",
                    weight=2,
                    fill=True,
                    fill_color="#eab308",
                    fill_opacity=0.9,
                    tooltip=f"🏭 Statik Aday ({s['site_grid']}) | {s['distinct_days']} Farklı Gün | Type=2: {s['has_nasa_type2']}"
                ).add_to(fg_sites)
            fg_sites.add_to(m)

        # 5. Profesyonel CBS Eklentileri (Tam Ekran, Mesafe Ölçer, Mini Harita)
        Fullscreen(position="topleft", title="Tam Ekran", title_cancel="Çıkış").add_to(m)
        MeasureControl(position="bottomleft", primary_length_unit="kilometers", primary_area_unit="sqkilometers").add_to(m)
        MiniMap(tile_layer="CartoDB dark_matter", position="bottomright", width=110, height=110, toggle_display=True).add_to(m)
        folium.LayerControl(position="topright", collapsed=False).add_to(m)

        st_folium(m, use_container_width=True, height=520, returned_objects=[])

    with c_proof:
        st.markdown("#### 🧾 Bilimsel Kanıt ve Doğrulama Telemetrisi")
        st.caption("Her metriğin kaynağı, eşleşme sayısı ve bağımsız test hatası (MAE) anlık olarak hesaplanır.")
        st.markdown("""
        <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(148,163,184,0.2); border-radius:10px; padding:10px 14px; margin-bottom:10px; font-size:12px;">
            <b>🎨 Harita Katman Rehberi:</b><br>
            🟢 <b>Yeşil Çekirdek + Hale:</b> Eşleşen Aqua MODIS & VIIRS (Hale çapı FRP şiddetine duyarlıdır)<br>
            🔥 <b>Isı Katmanı:</b> FRP ağırlıklı termal yoğunluk gradyanı<br>
            🟡 <b>Sarı Halkalar:</b> 1 km Grid bazında tekrarlayan / Type=2 statik kaynak adayları<br>
            🔵 / 🟠 <b>Mavi & Turuncu:</b> Ham MODIS (1 km) ve VIIRS (375 m) pikselleri
        </div>
        """, unsafe_allow_html=True)
        st.json({"Eşleştirme_Özeti": summary, "Kalibrasyon_Test_Sonucu": cal_metrics})