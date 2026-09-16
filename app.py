import streamlit as st
from api_clients import geocode, route, stations_near_route
from optimizer import Vehicle, Station, evaluate_stations

st.set_page_config(page_title="Fuel Route Optimizer", layout="wide")
st.title("Fuel Route Optimizer")
st.caption("V0.4 — géocodage + itinéraire + prix réels des carburants")

st.header("1. Véhicule")
c1, c2 = st.columns(2)
with c1:
    fuel_type = st.selectbox("Carburant", ["SP95-E10", "SP98", "SP95", "E85", "Diesel", "GPLc"])
    tank = st.number_input("Capacité du réservoir (L)", 20.0, 150.0, 53.0, 1.0)
    consumption = st.number_input("Consommation moyenne (L/100 km)", 2.0, 30.0, 7.0, 0.1)
with c2:
    mode = st.radio("Indication du véhicule", ["Autonomie restante (km)", "Niveau de carburant (%)"])
    if mode.startswith("Autonomie"):
        range_km = st.number_input("Autonomie affichée (km)", 1.0, 2000.0, 280.0, 10.0)
        fuel_remaining = range_km * consumption / 100
    else:
        pct = st.slider("Niveau de carburant (%)", 1, 100, 40)
        fuel_remaining = tank * pct / 100
        range_km = fuel_remaining / consumption * 100
    fuel_remaining = min(fuel_remaining, tank)
    st.caption(f"Carburant estimé : {fuel_remaining:.1f} L — autonomie : {range_km:.0f} km")

st.header("2. Trajet")
start = st.text_input("Départ", "Paris, France")
destination = st.text_input("Destination", "Lyon, France")

st.header("3. Contraintes")
c1, c2, c3 = st.columns(3)
with c1:
    time_value = st.number_input("Valeur du temps (€/h)", 0.0, 200.0, 15.0, 5.0)
with c2:
    max_detour = st.number_input("Détour maximal (min)", 0.0, 60.0, 20.0, 1.0)
with c3:
    min_saving = st.number_input("Économie nette minimale (€)", 0.0, 100.0, 5.0, 1.0)
safety = st.number_input("Marge de sécurité minimale (km)", 0.0, 200.0, 20.0, 5.0)
max_from_route = st.number_input(
    "Distance max d'une station par rapport à la route (km)", 1.0, 20.0, 5.0, 1.0
)

if st.button("Analyser le trajet", type="primary"):
    try:
        with st.spinner("Géocodage..."):
            slat, slon, slabel = geocode(start)
            dlat, dlon, dlabel = geocode(destination)

        with st.spinner("Calcul de l'itinéraire..."):
            normal = route([(slat, slon), (dlat, dlon)])

        normal_km = normal["distance"] / 1000
        normal_min = normal["duration"] / 60
        geometry = normal["geometry"]["coordinates"]
        st.info(f"{slabel} → {dlabel} : {normal_km:.1f} km, {normal_min:.0f} min")

        with st.spinner("Recherche des stations réelles..."):
            raw = stations_near_route(geometry, fuel_type, max_from_route, 12)

        if not raw:
            st.warning("Aucune station compatible trouvée.")
            st.stop()

        vehicle = Vehicle(fuel_type, tank, consumption, fuel_remaining)
        stations = []
        progress = st.progress(0)

        for i, x in enumerate(raw):
            try:
                r = route(
                    [(slat, slon), (x["lat"], x["lon"]), (dlat, dlon)],
                    overview=False,
                )
                legs = r["legs"]
                stations.append(
                    Station(
                        x["id"],
                        x["name"],
                        x["lat"],
                        x["lon"],
                        x["price"],
                        x["availability"],
                        legs[0]["distance"] / 1000,
                        max(r["distance"] / 1000 - normal_km, 0),
                        max(r["duration"] / 60 - normal_min, 0),
                        legs[1]["distance"] / 1000,
                        x["updated"],
                    )
                )
            except Exception:
                pass
            progress.progress((i + 1) / len(raw))

        progress.empty()

        if not stations:
            st.error("Impossible de calculer les itinéraires vers les stations.")
            st.stop()

        # Build the feasible set first so the reference is not based on an
        # arbitrary expensive station or on a station that violates constraints.
        safety_l = safety * consumption / 100
        feasible_for_reference = []
        for s in stations:
            if s.availability == "Indisponible":
                continue
            if s.detour_minutes > max_detour:
                continue
            needed = s.distance_to_station_km * consumption / 100
            remaining = fuel_remaining - needed
            if remaining < safety_l:
                continue
            fuel_after_refuel = tank
            needed_destination = s.station_to_destination_km * consumption / 100
            if fuel_after_refuel - needed_destination < safety_l:
                continue
            feasible_for_reference.append(s)

        if not feasible_for_reference:
            st.header("4. Résultat")
            st.warning("Aucune station n'est atteignable avec les contraintes actuelles.")
            st.subheader("Stations écartées")
            _, rejected = evaluate_stations(
                stations, vehicle, time_value, 0.0, safety, min_saving, max_detour
            )
            for s, reason in rejected:
                st.write(f"- {s.name} : {reason}")
            st.stop()

        # Baseline: the feasible station requiring the smallest detour.
        reference_station = min(
            feasible_for_reference,
            key=lambda s: (s.detour_minutes, s.detour_km, s.price_per_l),
        )
        reference_price = reference_station.price_per_l

        results, rejected = evaluate_stations(
            stations,
            vehicle,
            time_value,
            reference_price,
            safety,
            min_saving,
            max_detour,
        )

        st.header("4. Résultat")
        st.caption(
            f"Référence de comparaison : {reference_station.name} "
            f"({reference_price:.3f} €/L, détour {reference_station.detour_minutes:.0f} min)"
        )

        if not results:
            st.warning("Aucune station ne respecte toutes les contraintes et le seuil d'économie nette.")
        else:
            best = results[0]
            s = best["station"]

            st.success(f"Station recommandée : {s.name}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prix", f"{s.price_per_l:.3f} €/L")
            c2.metric("Détour", f"{s.detour_km:.1f} km / {s.detour_minutes:.0f} min")
            c3.metric("Économie nette", f"{best['net_saving']:.2f} €")
            c4.metric("Marge à destination", f"{best['safety_margin_at_destination_km']:.0f} km")

            st.subheader("Avant le ravitaillement")
            st.write(
                f"Carburant à l'arrivée à la station : {best['fuel_remaining_at_station']:.2f} L "
                f"({best['fuel_remaining_at_station'] / consumption * 100:.0f} km d'autonomie)"
            )
            st.write(
                f"Marge au-dessus de la sécurité à la station : "
                f"{best['safety_margin_at_station_km']:.0f} km "
                f"(minimum requis : {safety:.0f} km)"
            )

            st.subheader("Après le ravitaillement")
            st.write(f"Carburant acheté : {best['liters_to_buy']:.1f} L")
            st.write(f"Carburant après ravitaillement : {best['fuel_after_refuel']:.1f} L")
            st.write(f"Carburant estimé à l'arrivée à destination : {best['fuel_at_destination']:.2f} L")
            st.write(f"Autonomie estimée à l'arrivée : {best['arrival_range_km']:.0f} km")
            st.write(
                f"Marge au-dessus de la sécurité à l'arrivée : "
                f"{best['safety_margin_at_destination_km']:.0f} km "
                f"(minimum requis : {safety:.0f} km)"
            )

            st.subheader("Décomposition de l'économie")
            st.write(f"Économie brute : {best['gross_saving']:.2f} €")
            st.write(f"Coût du carburant du détour : {best['detour_fuel_cost']:.2f} €")
            st.write(f"Coût du temps : {best['time_cost']:.2f} €")
            st.write(f"Économie nette : {best['net_saving']:.2f} €")
            st.write(f"Prix mis à jour : {s.price_updated_at or 'inconnu'}")

            st.subheader("Autres stations retenues")
            for item in results[1:]:
                s = item["station"]
                st.write(
                    f"**{s.name}** — {s.price_per_l:.3f} €/L — +{s.detour_minutes:.0f} min "
                    f"— économie {item['net_saving']:.2f} € — "
                    f"marge destination {item['safety_margin_at_destination_km']:.0f} km"
                )

        if rejected:
            st.subheader("Stations écartées")
            for s, reason in rejected:
                st.write(f"- {s.name} : {reason}")

    except Exception as e:
        st.error("Une erreur est survenue.")
        st.exception(e)
        with st.spinner("Géocodage..."):
            slat,slon,slabel=geocode(start); dlat,dlon,dlabel=geocode(destination)
        with st.spinner("Calcul de l'itinéraire..."):
            normal=route([(slat,slon),(dlat,dlon)])
        normal_km=normal["distance"]/1000; normal_min=normal["duration"]/60; geometry=normal["geometry"]["coordinates"]
        st.info(f"{slabel} → {dlabel} : {normal_km:.1f} km, {normal_min:.0f} min")
        with st.spinner("Recherche des stations réelles..."):
            raw=stations_near_route(geometry,fuel_type,max_from_route,12)
        if not raw: st.warning("Aucune station compatible trouvée."); st.stop()
        vehicle=Vehicle(fuel_type,tank,consumption,fuel_remaining); stations=[]; progress=st.progress(0)
        for i,x in enumerate(raw):
            try:
                r=route([(slat,slon),(x["lat"],x["lon"]),(dlat,dlon)],overview=False); legs=r["legs"]
                stations.append(Station(x["id"],x["name"],x["lat"],x["lon"],x["price"],x["availability"],legs[0]["distance"]/1000,max(r["distance"]/1000-normal_km,0),max(r["duration"]/60-normal_min,0),legs[1]["distance"]/1000,x["updated"]))
            except Exception: pass
            progress.progress((i+1)/len(raw))
        progress.empty()
        if not stations: st.error("Impossible de calculer les itinéraires vers les stations."); st.stop()
        reference_price=max(s.price_per_l for s in stations)
        results,rejected=evaluate_stations(stations,vehicle,time_value,reference_price,safety,min_saving,tank)
        st.header("4. Résultat")
        if not results: st.warning("Aucune station ne respecte toutes les contraintes.")
        else:
            best=results[0]; s=best["station"]; r=best; margin=r["fuel_remaining_at_station"]/consumption*100
            st.success(f"Station recommandée : {s.name}")
            c1,c2,c3,c4=st.columns(4); c1.metric("Prix",f"{s.price_per_l:.3f} €/L"); c2.metric("Détour",f"{s.detour_km:.1f} km / {s.detour_minutes:.0f} min"); c3.metric("Économie nette",f"{r['net_saving']:.2f} €"); c4.metric("Marge",f"{margin:.0f} km")
            st.write(f"Carburant à acheter : {r['liters_to_buy']:.1f} L")
            st.write(f"Carburant restant à l'arrivée : {r['fuel_remaining_at_station']:.2f} L")
            st.write(f"Économie brute : {r['gross_saving']:.2f} €")
            st.write(f"Coût du détour : {r['detour_fuel_cost']:.2f} €")
            st.write(f"Coût du temps : {r['time_cost']:.2f} €")
            st.write(f"Prix mis à jour : {s.price_updated_at or 'inconnu'}")
            st.subheader("Autres stations retenues")
            for item in results[1:]:
                s=item["station"]; r=item; margin=r["fuel_remaining_at_station"]/consumption*100
                st.write(f"**{s.name}** — {s.price_per_l:.3f} €/L — +{s.detour_minutes:.0f} min — économie {r['net_saving']:.2f} € — marge {margin:.0f} km")
        if rejected:
            st.subheader("Stations écartées")
            for s,reason in rejected: st.write(f"- {s.name} : {reason}")
    except Exception as e:
        st.error("Une erreur est survenue."); st.exception(e)
        with st.spinner("Géocodage..."):
            slat,slon,slabel=geocode(start); dlat,dlon,dlabel=geocode(destination)
        with st.spinner("Calcul de l'itinéraire..."):
            normal=route([(slat,slon),(dlat,dlon)])
        normal_km=normal["distance"]/1000; normal_min=normal["duration"]/60; geometry=normal["geometry"]["coordinates"]
        st.info(f"{slabel} → {dlabel} : {normal_km:.1f} km, {normal_min:.0f} min")
        with st.spinner("Recherche des stations réelles..."):
            raw=stations_near_route(geometry,fuel_type,max_from_route,12)
        if not raw: st.warning("Aucune station compatible trouvée."); st.stop()
        vehicle=Vehicle(fuel_type,tank,consumption,fuel_remaining); stations=[]; progress=st.progress(0)
        for i,x in enumerate(raw):
            try:
                r=route([(slat,slon),(x["lat"],x["lon"]),(dlat,dlon)],overview=False); legs=r["legs"]
                stations.append(Station(x["id"],x["name"],x["lat"],x["lon"],x["price"],x["availability"],legs[0]["distance"]/1000,max(r["distance"]/1000-normal_km,0),max(r["duration"]/60-normal_min,0),legs[1]["distance"]/1000,x["updated"]))
            except Exception: pass
            progress.progress((i+1)/len(raw))
        progress.empty()
        if not stations: st.error("Impossible de calculer les itinéraires vers les stations."); st.stop()
        reference_price=max(s.price_per_l for s in stations)
        results,rejected=evaluate_stations(stations,vehicle,time_value,reference_price,safety,min_saving,tank)
        st.header("4. Résultat")
        if not results: st.warning("Aucune station ne respecte toutes les contraintes.")
        else:
            best=results[0]; s=best["station"]; r=best["result"]; margin=r["fuel_remaining_at_station"]/consumption*100
            st.success(f"Station recommandée : {s.name}")
            c1,c2,c3,c4=st.columns(4); c1.metric("Prix",f"{s.price_per_l:.3f} €/L"); c2.metric("Détour",f"{s.detour_km:.1f} km / {s.detour_minutes:.0f} min"); c3.metric("Économie nette",f"{r['net_saving']:.2f} €"); c4.metric("Marge",f"{margin:.0f} km")
            st.write(f"Carburant à acheter : {r['liters_to_buy']:.1f} L")
            st.write(f"Carburant restant à l'arrivée : {r['fuel_remaining_at_station']:.2f} L")
            st.write(f"Économie brute : {r['gross_saving']:.2f} €")
            st.write(f"Coût du détour : {r['detour_fuel_cost']:.2f} €")
            st.write(f"Coût du temps : {r['time_cost']:.2f} €")
            st.write(f"Prix mis à jour : {s.price_updated_at or 'inconnu'}")
            st.subheader("Autres stations retenues")
            for item in results[1:]:
                s=item["station"]; r=item["result"]; margin=r["fuel_remaining_at_station"]/consumption*100
                st.write(f"**{s.name}** — {s.price_per_l:.3f} €/L — +{s.detour_minutes:.0f} min — économie {r['net_saving']:.2f} € — marge {margin:.0f} km")
        if rejected:
            st.subheader("Stations écartées")
            for s,reason in rejected: st.write(f"- {s.name} : {reason}")
    except Exception as e:
        st.error("Une erreur est survenue."); st.exception(e)
