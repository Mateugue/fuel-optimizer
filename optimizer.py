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


def fuel_needed(distance_km, consumption):
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
