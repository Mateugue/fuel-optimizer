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


def evaluate_stations(
    stations,
    vehicle: Vehicle,
    value_of_time: float,
    reference_price: float,
    safety_margin_km: float,
    minimum_net_saving: float,
    max_detour_minutes: float,
):
    """Evaluate one-stop refueling options.

    The algorithm assumes the vehicle fills the tank at the selected station.
    The economic comparison is made against a reference station price using
    the same quantity of fuel that would be purchased at the selected station.
    """
    candidates = []
    rejected = []
    consumption = vehicle.consumption_l_per_100km
    safety_l = fuel_needed(safety_margin_km, consumption)

    for s in stations:
        # 1) Fuel availability
        if s.availability == "Indisponible":
            rejected.append((s, "Carburant indisponible"))
            continue

        # 2) Detour constraint
        if s.detour_minutes > max_detour_minutes:
            rejected.append((s, "Détour maximal dépassé"))
            continue

        # 3) Can the vehicle safely reach the station?
        needed_to_station = fuel_needed(s.distance_to_station_km, consumption)
        fuel_remaining_at_station = vehicle.fuel_remaining_l - needed_to_station

        if fuel_remaining_at_station < safety_l:
            rejected.append(
                (s, "Marge de sécurité insuffisante pour atteindre la station")
            )
            continue

        # 4) Refuel: never buy more than the physical tank capacity.
        free_space = max(vehicle.tank_capacity_l - fuel_remaining_at_station, 0.0)
        liters_to_buy = free_space
        fuel_after_refuel = fuel_remaining_at_station + liters_to_buy

        # 5) Can the vehicle finish the trip with the requested safety margin?
        fuel_needed_to_destination = fuel_needed(
            s.station_to_destination_km, consumption
        )
        fuel_at_destination = fuel_after_refuel - fuel_needed_to_destination

        if fuel_at_destination < safety_l:
            rejected.append(
                (s, "Réservoir insuffisant pour terminer le trajet avec la marge")
            )
            continue

        # 6) Two distinct safety indicators.
        safety_margin_at_station_km = max(
            (fuel_remaining_at_station - safety_l) / consumption * 100.0,
            0.0,
        )
        safety_margin_at_destination_km = max(
            (fuel_at_destination - safety_l) / consumption * 100.0,
            0.0,
        )
        arrival_range_km = max(fuel_at_destination / consumption * 100.0, 0.0)

        # 7) Economic calculation.
        gross_saving = max(reference_price - s.price_per_l, 0.0) * liters_to_buy
        detour_fuel_cost = fuel_needed(s.detour_km, consumption) * s.price_per_l
        time_cost = s.detour_minutes / 60.0 * value_of_time
        net_saving = gross_saving - detour_fuel_cost - time_cost

        if net_saving < minimum_net_saving:
            rejected.append((s, "Économie nette insuffisante"))
            continue

        candidates.append(
            {
                "station": s,
                "fuel_needed_to_station": needed_to_station,
                "fuel_remaining_at_station": fuel_remaining_at_station,
                "safety_margin_at_station_km": safety_margin_at_station_km,
                "liters_to_buy": liters_to_buy,
                "fuel_after_refuel": fuel_after_refuel,
                "fuel_needed_to_destination": fuel_needed_to_destination,
                "fuel_at_destination": fuel_at_destination,
                "arrival_range_km": arrival_range_km,
                "safety_margin_at_destination_km": safety_margin_at_destination_km,
                "gross_saving": gross_saving,
                "detour_fuel_cost": detour_fuel_cost,
                "time_cost": time_cost,
                "net_saving": net_saving,
            }
        )

    # Highest real net saving first. Tie-breakers favor less detour and lower price.
    candidates.sort(
        key=lambda x: (
            x["net_saving"],
            -x["station"].detour_minutes,
            -x["station"].price_per_l,
        ),
        reverse=True,
    )
    return candidates, rejected
    return distance_km * consumption / 100


def evaluate_stations(
    stations,
    vehicle,
    value_of_time,
    reference_price,
    safety_margin_km,
    minimum_net_saving,
    max_detour_minutes,
):
    """Evaluate one-stop refueling options.

    The reference price is supplied by the caller and should represent a
    realistic baseline station, preferably the feasible station with the
    smallest detour.
    """
    candidates, rejected = [], []
    safety_l = fuel_needed(safety_margin_km, vehicle.consumption_l_per_100km)

    for s in stations:
        if s.availability == "Indisponible":
            rejected.append((s, "Carburant indisponible"))
            continue

        if s.detour_minutes > max_detour_minutes:
            rejected.append((s, "Détour maximal dépassé"))
            continue

        needed_to_station = fuel_needed(
            s.distance_to_station_km, vehicle.consumption_l_per_100km
        )
        remaining_at_station = vehicle.fuel_remaining_l - needed_to_station

        if remaining_at_station < safety_l:
            rejected.append(
                (s, "Marge de sécurité insuffisante pour atteindre la station")
            )
            continue

        # Fill the tank. The quantity can never exceed the actual free space.
        space = max(vehicle.tank_capacity_l - remaining_at_station, 0.0)
        liters_to_buy = space
        fuel_after_refuel = remaining_at_station + liters_to_buy

        fuel_needed_to_destination = fuel_needed(
            s.station_to_destination_km, vehicle.consumption_l_per_100km
        )
        fuel_at_destination = fuel_after_refuel - fuel_needed_to_destination

        if fuel_at_destination < safety_l:
            rejected.append(
                (s, "Réservoir insuffisant pour terminer le trajet avec la marge")
            )
            continue

        arrival_range_km = max(
            fuel_at_destination / vehicle.consumption_l_per_100km * 100, 0.0
        )
        safety_margin_at_station_km = max(
            (remaining_at_station - safety_l)
            / vehicle.consumption_l_per_100km
            * 100,
            0.0,
        )
        safety_margin_at_destination_km = max(
            (fuel_at_destination - safety_l)
            / vehicle.consumption_l_per_100km
            * 100,
            0.0,
        )

        gross_saving = max(reference_price - s.price_per_l, 0.0) * liters_to_buy
        detour_fuel_cost = (
            fuel_needed(s.detour_km, vehicle.consumption_l_per_100km)
            * s.price_per_l
        )
        time_cost = s.detour_minutes / 60 * value_of_time
        net_saving = gross_saving - detour_fuel_cost - time_cost

        # The reference station itself has zero saving by definition. It is
        # kept as a candidate only when the user allows a zero threshold.
        if net_saving < minimum_net_saving:
            rejected.append((s, "Économie nette insuffisante"))
            continue

        candidates.append(
            {
                "station": s,
                "fuel_needed_to_station": needed_to_station,
                "fuel_remaining_at_station": remaining_at_station,
                "safety_margin_at_station_km": safety_margin_at_station_km,
                "liters_to_buy": liters_to_buy,
                "fuel_after_refuel": fuel_after_refuel,
                "fuel_needed_to_destination": fuel_needed_to_destination,
                "fuel_at_destination": fuel_at_destination,
                "arrival_range_km": arrival_range_km,
                "safety_margin_at_destination_km": safety_margin_at_destination_km,
                "gross_saving": gross_saving,
                "detour_fuel_cost": detour_fuel_cost,
                "time_cost": time_cost,
                "net_saving": net_saving,
            }
        )

    candidates.sort(key=lambda x: x["net_saving"], reverse=True)
    return candidates, rejected
    minimum_net_saving,
    max_detour_minutes,
):
    """Evaluate one-stop refueling options.

    The reference price is supplied by the caller and should represent a
    realistic baseline station, preferably the feasible station with the
    smallest detour.
    """
    candidates, rejected = [], []
    safety_l = fuel_needed(safety_margin_km, vehicle.consumption_l_per_100km)

    for s in stations:
        if s.availability == "Indisponible":
            rejected.append((s, "Carburant indisponible"))
            continue

        if s.detour_minutes > max_detour_minutes:
            rejected.append((s, "Détour maximal dépassé"))
            continue

        needed_to_station = fuel_needed(
            s.distance_to_station_km, vehicle.consumption_l_per_100km
        )
        remaining_at_station = vehicle.fuel_remaining_l - needed_to_station

        if remaining_at_station < safety_l:
            rejected.append(
                (s, "Marge de sécurité insuffisante pour atteindre la station")
            )
            continue

        # Fill the tank. The quantity can never exceed the actual free space.
        space = max(vehicle.tank_capacity_l - remaining_at_station, 0.0)
        liters_to_buy = space
        fuel_after_refuel = remaining_at_station + liters_to_buy

        fuel_needed_to_destination = fuel_needed(
            s.station_to_destination_km, vehicle.consumption_l_per_100km
        )
        fuel_at_destination = fuel_after_refuel - fuel_needed_to_destination

        if fuel_at_destination < safety_l:
            rejected.append(
                (s, "Réservoir insuffisant pour terminer le trajet avec la marge")
            )
            continue

        arrival_range_km = max(
            fuel_at_destination / vehicle.consumption_l_per_100km * 100, 0.0
        )
        safety_margin_at_station_km = max(
            (remaining_at_station - safety_l)
            / vehicle.consumption_l_per_100km
            * 100,
            0.0,
        )
        safety_margin_at_destination_km = max(
            (fuel_at_destination - safety_l)
            / vehicle.consumption_l_per_100km
            * 100,
            0.0,
        )

        gross_saving = max(reference_price - s.price_per_l, 0.0) * liters_to_buy
        detour_fuel_cost = (
            fuel_needed(s.detour_km, vehicle.consumption_l_per_100km)
            * s.price_per_l
        )
        time_cost = s.detour_minutes / 60 * value_of_time
        net_saving = gross_saving - detour_fuel_cost - time_cost

        # The reference station itself has zero saving by definition. It is
        # kept as a candidate only when the user allows a zero threshold.
        if net_saving < minimum_net_saving:
            rejected.append((s, "Économie nette insuffisante"))
            continue

        candidates.append(
            {
                "station": s,
                "fuel_needed_to_station": needed_to_station,
                "fuel_remaining_at_station": remaining_at_station,
                "safety_margin_at_station_km": safety_margin_at_station_km,
                "liters_to_buy": liters_to_buy,
                "fuel_after_refuel": fuel_after_refuel,
                "fuel_needed_to_destination": fuel_needed_to_destination,
                "fuel_at_destination": fuel_at_destination,
                "arrival_range_km": arrival_range_km,
                "safety_margin_at_destination_km": safety_margin_at_destination_km,
                "gross_saving": gross_saving,
                "detour_fuel_cost": detour_fuel_cost,
                "time_cost": time_cost,
                "net_saving": net_saving,
            }
        )

    candidates.sort(key=lambda x: x["net_saving"], reverse=True)
    return candidates, rejected
            rejected.append((s, "Marge de sécurité insuffisante pour atteindre la station")); continue
        space = max(vehicle.tank_capacity_l - remaining, 0)
        buy = min(max(liters_to_buy, 0), space)
        required_after = fuel_needed(s.station_to_destination_km + safety_margin_km,
                                     vehicle.consumption_l_per_100km)
        if remaining + buy < required_after:
            rejected.append((s, "Réservoir insuffisant pour terminer le trajet avec la marge")); continue
        gross = (reference_price - s.price_per_l) * buy
        detour_fuel_cost = fuel_needed(s.detour_km, vehicle.consumption_l_per_100km) * s.price_per_l
        time_cost = s.detour_minutes / 60 * value_of_time
        net = gross - detour_fuel_cost - time_cost
        if net < minimum_net_saving:
            rejected.append((s, "Économie nette insuffisante")); continue
        candidates.append({"station": s, "fuel_needed_to_station": needed,
                           "fuel_remaining_at_station": remaining, "liters_to_buy": buy,
                           "gross_saving": gross, "detour_fuel_cost": detour_fuel_cost,
                           "time_cost": time_cost, "net_saving": net})
    candidates.sort(key=lambda x: x["net_saving"], reverse=True)
    return candidates, rejected
