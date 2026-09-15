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

def evaluate_stations(stations, vehicle, value_of_time, reference_price,
                      safety_margin_km, minimum_net_saving, liters_to_buy):
    candidates, rejected = [], []
    safety_l = fuel_needed(safety_margin_km, vehicle.consumption_l_per_100km)
    for s in stations:
        if s.availability == "Indisponible":
            rejected.append((s, "Carburant indisponible")); continue
        needed = fuel_needed(s.distance_to_station_km, vehicle.consumption_l_per_100km)
        remaining = vehicle.fuel_remaining_l - needed
        if remaining < safety_l:
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
