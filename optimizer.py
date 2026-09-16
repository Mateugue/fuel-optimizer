from dataclasses import dataclass


@dataclass
class Vehicle:
    fuel_type: str
    tank_capacity_l: float
    consumption_l_per_100km: float
    fuel_remaining_l: float


@dataclass
class Station:
    station_id: str
    name: str
    latitude: float
    longitude: float
    price_per_l: float
    availability: str
    distance_to_station_km: float = 0.0
    detour_km: float = 0.0
    detour_minutes: float = 0.0
    station_to_destination_km: float = 0.0
    price_updated_at: str = ""


def fuel_needed(distance_km: float, consumption_l_per_100km: float) -> float:
    return distance_km * consumption_l_per_100km / 100.0


def station_is_reachable(
    station: Station,
    vehicle: Vehicle,
    safety_margin_km: float,
    max_detour_minutes: float,
):
    consumption = vehicle.consumption_l_per_100km
    safety_l = fuel_needed(safety_margin_km, consumption)

    if station.availability == "Indisponible":
        return False, "Carburant indisponible"

    if station.detour_minutes > max_detour_minutes:
        return False, "Détour maximal dépassé"

    fuel_needed_to_station = fuel_needed(
        station.distance_to_station_km,
        consumption,
    )

    fuel_at_station = vehicle.fuel_remaining_l - fuel_needed_to_station

    if fuel_at_station < safety_l:
        return False, "Marge de sécurité insuffisante pour atteindre la station"

    free_space = max(
        vehicle.tank_capacity_l - fuel_at_station,
        0.0,
    )

    fuel_after_refuel = fuel_at_station + free_space

    fuel_needed_to_destination = fuel_needed(
        station.station_to_destination_km,
        consumption,
    )

    fuel_at_destination = (
        fuel_after_refuel - fuel_needed_to_destination
    )

    if fuel_at_destination < safety_l:
        return False, "Réservoir insuffisant pour terminer le trajet avec la marge"

    return True, ""


def calculate_station_state(
    station: Station,
    vehicle: Vehicle,
    safety_margin_km: float,
):
    consumption = vehicle.consumption_l_per_100km
    safety_l = fuel_needed(safety_margin_km, consumption)

    fuel_needed_to_station = fuel_needed(
        station.distance_to_station_km,
        consumption,
    )

    fuel_at_station = (
        vehicle.fuel_remaining_l - fuel_needed_to_station
    )

    free_space = max(
        vehicle.tank_capacity_l - fuel_at_station,
        0.0,
    )

    liters_to_buy = free_space

    fuel_after_refuel = fuel_at_station + liters_to_buy

    fuel_needed_to_destination = fuel_needed(
        station.station_to_destination_km,
        consumption,
    )

    fuel_at_destination = (
        fuel_after_refuel - fuel_needed_to_destination
    )

    safety_margin_at_station_km = max(
        (fuel_at_station - safety_l)
        / consumption
        * 100.0,
        0.0,
    )

    safety_margin_at_destination_km = max(
        (fuel_at_destination - safety_l)
        / consumption
        * 100.0,
        0.0,
    )

    arrival_range_km = max(
        fuel_at_destination / consumption * 100.0,
        0.0,
    )

    return {
        "fuel_needed_to_station": fuel_needed_to_station,
        "fuel_remaining_at_station": fuel_at_station,
        "safety_margin_at_station_km": safety_margin_at_station_km,
        "liters_to_buy": liters_to_buy,
        "fuel_after_refuel": fuel_after_refuel,
        "fuel_needed_to_destination": fuel_needed_to_destination,
        "fuel_at_destination": fuel_at_destination,
        "arrival_range_km": arrival_range_km,
        "safety_margin_at_destination_km": (
            safety_margin_at_destination_km
        ),
    }


def find_reference_station(
    stations,
    vehicle: Vehicle,
    safety_margin_km: float,
    max_detour_minutes: float,
):
    """
    Détermine le scénario de référence.

    La référence représente la station la plus naturelle
    pour le conducteur : celle nécessitant le moins de détour.

    Elle doit néanmoins être réellement atteignable et permettre
    de terminer le trajet avec la marge de sécurité demandée.
    """

    feasible = []

    for station in stations:
        reachable, _ = station_is_reachable(
            station,
            vehicle,
            safety_margin_km,
            max_detour_minutes,
        )

        if reachable:
            feasible.append(station)

    if not feasible:
        return None

    return min(
        feasible,
        key=lambda s: (
            s.detour_minutes,
            s.detour_km,
            s.distance_to_station_km,
        ),
    )


def evaluate_stations(
    stations,
    vehicle: Vehicle,
    value_of_time: float,
    reference_station: Station,
    safety_margin_km: float,
    minimum_net_saving: float,
    max_detour_minutes: float,
):
    """
    Compare chaque station avec une station de référence.

    La station de référence représente le ravitaillement
    le plus naturel sur le trajet.

    L'économie nette tient compte :
      - du prix du carburant,
      - de la quantité achetée,
      - du carburant consommé pendant le détour,
      - du coût du temps supplémentaire.
    """

    candidates = []
    rejected = []

    consumption = vehicle.consumption_l_per_100km

    # État de la station de référence
    reference_state = calculate_station_state(
        reference_station,
        vehicle,
        safety_margin_km,
    )

    reference_liters = reference_state["liters_to_buy"]
    reference_refuel_cost = (
        reference_liters
        * reference_station.price_per_l
    )

    for station in stations:

        # Disponibilité
        if station.availability == "Indisponible":
            rejected.append(
                (station, "Carburant indisponible")
            )
            continue

        # Détour
        if station.detour_minutes > max_detour_minutes:
            rejected.append(
                (station, "Détour maximal dépassé")
            )
            continue

        # Accessibilité et état du carburant
        reachable, reason = station_is_reachable(
            station,
            vehicle,
            safety_margin_km,
            max_detour_minutes,
        )

        if not reachable:
            rejected.append((station, reason))
            continue

        state = calculate_station_state(
            station,
            vehicle,
            safety_margin_km,
        )

        liters_to_buy = state["liters_to_buy"]

        # Coût du ravitaillement à la station candidate
        refuel_cost = (
            liters_to_buy
            * station.price_per_l
        )

        # Carburant consommé spécifiquement à cause du détour
        detour_fuel = fuel_needed(
            station.detour_km,
            consumption,
        )

        detour_fuel_cost = (
            detour_fuel
            * station.price_per_l
        )

        # Coût du temps supplémentaire
        time_cost = (
            station.detour_minutes
            / 60.0
            * value_of_time
        )

        # Coût total du scénario optimisé
        total_optimized_cost = (
            refuel_cost
            + detour_fuel_cost
            + time_cost
        )

        # Pour comparer correctement avec la référence,
        # on considère le même besoin de remplissage.
        reference_cost = (
            reference_liters
            * reference_station.price_per_l
        )

        net_saving = (
            reference_cost
            - total_optimized_cost
        )

        # La station de référence elle-même ne doit pas
        # être présentée comme une économie.
        if station.station_id == reference_station.station_id:
            net_saving = 0.0

        if net_saving < minimum_net_saving:
            rejected.append(
                (station, "Économie nette insuffisante")
            )
            continue

        candidates.append(
            {
                "station": station,

                "fuel_needed_to_station": (
                    state["fuel_needed_to_station"]
                ),

                "fuel_remaining_at_station": (
                    state["fuel_remaining_at_station"]
                ),

                "safety_margin_at_station_km": (
                    state["safety_margin_at_station_km"]
                ),

                "liters_to_buy": liters_to_buy,

                "fuel_after_refuel": (
                    state["fuel_after_refuel"]
                ),

                "fuel_needed_to_destination": (
                    state["fuel_needed_to_destination"]
                ),

                "fuel_at_destination": (
                    state["fuel_at_destination"]
                ),

                "arrival_range_km": (
                    state["arrival_range_km"]
                ),

                "safety_margin_at_destination_km": (
                    state["safety_margin_at_destination_km"]
                ),

                "reference_liters": reference_liters,

                "reference_price": (
                    reference_station.price_per_l
                ),

                "reference_refuel_cost": (
                    reference_refuel_cost
                ),

                "refuel_cost": refuel_cost,

                "detour_fuel_cost": detour_fuel_cost,

                "time_cost": time_cost,

                "total_optimized_cost": (
                    total_optimized_cost
                ),

                "gross_saving": (
                    reference_cost - refuel_cost
                ),

                "net_saving": net_saving,
            }
        )

    candidates.sort(
        key=lambda x: (
            x["net_saving"],
            -x["station"].detour_minutes,
            -x["station"].price_per_l,
        ),
        reverse=True,
    )

    return candidates, rejected
