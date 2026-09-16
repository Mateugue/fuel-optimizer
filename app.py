import streamlit as st

from api_clients import geocode, route, stations_near_route
from optimizer import (
    Vehicle,
    Station,
    find_reference_station,
    evaluate_stations,
)


st.set_page_config(
    page_title="Fuel Route Optimizer",
    layout="wide",
)

st.title("Fuel Route Optimizer")
st.caption(
    "V0.5 — géocodage + itinéraire + prix réels "
    "des carburants + comparaison avec station de référence"
)


st.header("1. Véhicule")

c1, c2 = st.columns(2)

with c1:
    fuel_type = st.selectbox(
        "Carburant",
        [
            "SP95-E10",
            "SP98",
            "SP95",
            "E85",
            "Diesel",
            "GPLc",
        ],
    )

    tank = st.number_input(
        "Capacité du réservoir (L)",
        20.0,
        150.0,
        53.0,
        1.0,
    )

    consumption = st.number_input(
        "Consommation moyenne (L/100 km)",
        2.0,
        30.0,
        7.0,
        0.1,
    )

with c2:
    mode = st.radio(
        "Indication du véhicule",
        [
            "Autonomie restante (km)",
            "Niveau de carburant (%)",
        ],
    )

    if mode.startswith("Autonomie"):
        range_km = st.number_input(
            "Autonomie affichée (km)",
            1.0,
            2000.0,
            280.0,
            10.0,
        )

        fuel_remaining = (
            range_km
            * consumption
            / 100.0
        )

    else:
        pct = st.slider(
            "Niveau de carburant (%)",
            1,
            100,
            40,
        )

        fuel_remaining = (
            tank
            * pct
            / 100.0
        )

        range_km = (
            fuel_remaining
            / consumption
            * 100.0
        )

    fuel_remaining = min(
        fuel_remaining,
        tank,
    )

    range_km = (
        fuel_remaining
        / consumption
        * 100.0
    )

    st.caption(
        f"Carburant estimé : {fuel_remaining:.1f} L "
        f"— autonomie : {range_km:.0f} km"
    )


st.header("2. Trajet")

start = st.text_input(
    "Départ",
    "Paris, France",
)

destination = st.text_input(
    "Destination",
    "Lyon, France",
)


st.header("3. Contraintes")

c1, c2, c3 = st.columns(3)

with c1:
    time_value = st.number_input(
        "Valeur du temps (€/h)",
        0.0,
        200.0,
        15.0,
        5.0,
    )

with c2:
    max_detour = st.number_input(
        "Détour maximal (min)",
        0.0,
        60.0,
        20.0,
        1.0,
    )

with c3:
    min_saving = st.number_input(
        "Économie nette minimale (€)",
        0.0,
        100.0,
        5.0,
        1.0,
    )

safety = st.number_input(
    "Marge de sécurité minimale (km)",
    0.0,
    200.0,
    20.0,
    5.0,
)

max_from_route = st.number_input(
    "Distance max d'une station par rapport à la route (km)",
    1.0,
    20.0,
    5.0,
    1.0,
)


if st.button(
    "Analyser le trajet",
    type="primary",
):

    try:

        with st.spinner("Géocodage..."):

            slat, slon, slabel = geocode(start)
            dlat, dlon, dlabel = geocode(destination)

        with st.spinner(
            "Calcul de l'itinéraire..."
        ):

            normal = route(
                [
                    (slat, slon),
                    (dlat, dlon),
                ]
            )

        normal_km = (
            normal["distance"]
            / 1000.0
        )

        normal_min = (
            normal["duration"]
            / 60.0
        )

        geometry = normal[
            "geometry"
        ]["coordinates"]

        st.info(
            f"{slabel} → {dlabel} : "
            f"{normal_km:.1f} km, "
            f"{normal_min:.0f} min"
        )

        with st.spinner(
            "Recherche des stations réelles..."
        ):

            raw = stations_near_route(
                geometry,
                fuel_type,
                max_from_route,
                12,
            )

        if not raw:

            st.warning(
                "Aucune station compatible trouvée."
            )

            st.stop()

        vehicle = Vehicle(
            fuel_type,
            tank,
            consumption,
            fuel_remaining,
        )

        stations = []

        progress = st.progress(0)

        for i, x in enumerate(raw):

            try:

                r = route(
                    [
                        (slat, slon),
                        (x["lat"], x["lon"]),
                        (dlat, dlon),
                    ],
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
                        legs[0]["distance"] / 1000.0,
                        max(
                            r["distance"] / 1000.0
                            - normal_km,
                            0.0,
                        ),
                        max(
                            r["duration"] / 60.0
                            - normal_min,
                            0.0,
                        ),
                        legs[1]["distance"] / 1000.0,
                        x["updated"],
                    )
                )

            except Exception:
                pass

            progress.progress(
                (i + 1) / len(raw)
            )

        progress.empty()

        if not stations:

            st.error(
                "Impossible de calculer les itinéraires "
                "vers les stations."
            )

            st.stop()

        reference_station = find_reference_station(
            stations,
            vehicle,
            safety,
            max_detour,
        )

        st.header("4. Résultat")

        if reference_station is None:

            st.warning(
                "Aucune station n'est atteignable "
                "avec les contraintes actuelles."
            )

            st.stop()

        st.subheader(
            "Station de référence"
        )

        st.info(
            f"{reference_station.name} — "
            f"{reference_station.price_per_l:.3f} €/L — "
            f"détour "
            f"{reference_station.detour_minutes:.0f} min"
        )

        results, rejected = evaluate_stations(
            stations,
            vehicle,
            time_value,
            reference_station,
            safety,
            min_saving,
            max_detour,
        )

        reference_state = None

        if reference_station:

            from optimizer import calculate_station_state

            reference_state = calculate_station_state(
                reference_station,
                vehicle,
                safety,
            )

        reference_liters = (
            reference_state["liters_to_buy"]
            if reference_state
            else 0.0
        )

        reference_cost = (
            reference_liters
            * reference_station.price_per_l
        )

        st.write(
            f"Ravitaillement de référence : "
            f"{reference_liters:.1f} L"
        )

        st.write(
            f"Coût de référence : "
            f"{reference_cost:.2f} €"
        )

        if not results:

            st.warning(
                "Aucune station ne permet une économie "
                f"nettement supérieure ou égale à "
                f"{min_saving:.2f} € "
                "par rapport au scénario de référence."
            )

        else:

            best = results[0]
            s = best["station"]

            st.success(
                f"Station recommandée : {s.name}"
            )

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Prix",
                f"{s.price_per_l:.3f} €/L",
            )

            c2.metric(
                "Détour",
                f"{s.detour_km:.1f} km / "
                f"{s.detour_minutes:.0f} min",
            )

            c3.metric(
                "Économie nette",
                f"{best['net_saving']:.2f} €",
            )

            c4.metric(
                "Marge destination",
                f"{best['safety_margin_at_destination_km']:.0f} km",
            )

            st.subheader(
                "Avant le ravitaillement"
            )

            st.write(
                f"Carburant à l'arrivée : "
                f"{best['fuel_remaining_at_station']:.2f} L"
            )

            st.write(
                f"Autonomie à la station : "
                f"{best['fuel_remaining_at_station'] / consumption * 100:.0f} km"
            )

            st.write(
                f"Marge de sécurité à la station : "
                f"{best['safety_margin_at_station_km']:.0f} km"
            )

            st.subheader(
                "Après le ravitaillement"
            )

            st.write(
                f"Carburant acheté : "
                f"{best['liters_to_buy']:.1f} L"
            )

            st.write(
                f"Carburant après ravitaillement : "
                f"{best['fuel_after_refuel']:.1f} L"
            )

            st.write(
                f"Carburant à destination : "
                f"{best['fuel_at_destination']:.2f} L"
            )

            st.write(
                f"Autonomie à destination : "
                f"{best['arrival_range_km']:.0f} km"
            )

            st.write(
                f"Marge de sécurité à destination : "
                f"{best['safety_margin_at_destination_km']:.0f} km"
            )

            st.subheader(
                "Analyse économique"
            )

            c1, c2 = st.columns(2)

            with c1:

                st.write(
                    f"Coût de référence : "
                    f"{best['reference_refuel_cost']:.2f} €"
                )

                st.write(
                    f"Coût du ravitaillement : "
                    f"{best['refuel_cost']:.2f} €"
                )

            with c2:

                st.write(
                    f"Coût carburant du détour : "
                    f"{best['detour_fuel_cost']:.2f} €"
                )

                st.write(
                    f"Coût du temps : "
                    f"{best['time_cost']:.2f} €"
                )

            st.metric(
                "ÉCONOMIE NETTE",
                f"{best['net_saving']:.2f} €",
            )

            st.caption(
                f"Prix mis à jour : "
                f"{s.price_updated_at or 'inconnu'}"
            )

            st.subheader(
                "Autres stations retenues"
            )

            for item in results[1:]:

                s = item["station"]

                st.write(
                    f"**{s.name}** — "
                    f"{s.price_per_l:.3f} €/L — "
                    f"+{s.detour_minutes:.0f} min — "
                    f"économie "
                    f"{item['net_saving']:.2f} € — "
                    f"marge destination "
                    f"{item['safety_margin_at_destination_km']:.0f} km"
                )

        if rejected:

            st.subheader(
                "Stations écartées"
            )

            for s, reason in rejected:

                st.write(
                    f"- {s.name} : {reason}"
                )

    except Exception as e:

        st.error(
            "Une erreur est survenue."
        )

        st.exception(e)
