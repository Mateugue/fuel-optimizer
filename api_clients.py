import math, requests
GEOCODING_URL="https://data.geopf.fr/geocodage/search/"
OSRM_URL="https://router.project-osrm.org/route/v1/driving"
FUEL_URL="https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/exports/geojson"
HEADERS={"User-Agent":"FuelRouteOptimizer-MVP/0.1"}

def geocode(address):
    r=requests.get(GEOCODING_URL,params={"q":address,"limit":1},headers=HEADERS,timeout=15); r.raise_for_status()
    data=r.json()
    if not data.get("features"): raise ValueError(f"Adresse introuvable : {address}")
    f=data["features"][0]; lon,lat=f["geometry"]["coordinates"][:2]
    return lat,lon,f["properties"].get("label",address)

def route(points,overview=True):
    coords=";".join(f"{lon},{lat}" for lat,lon in points)
    r=requests.get(f"{OSRM_URL}/{coords}",params={"overview":"full" if overview else "false","geometries":"geojson"},headers=HEADERS,timeout=30); r.raise_for_status()
    data=r.json()
    if data.get("code")!="Ok": raise ValueError("Aucun itinéraire trouvé.")
    return data["routes"][0]

def haversine(a_lat,a_lon,b_lat,b_lon):
    R=6371.0088; p1,p2=math.radians(a_lat),math.radians(b_lat); dp=math.radians(b_lat-a_lat); dl=math.radians(b_lon-a_lon)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

def closest_route_distance(lat,lon,geometry):
    return min(haversine(lat,lon,p[1],p[0]) for p in geometry)

def stations_near_route(geometry,fuel_type,max_km=5,limit=12):
    r=requests.get(FUEL_URL,headers=HEADERS,timeout=60); r.raise_for_status()
    features=r.json().get("features",[])
    price_field={"SP95-E10":"e10_prix","SP98":"sp98_prix","SP95":"sp95_prix","E85":"e85_prix","Diesel":"gazole_prix","GPLc":"gplc_prix"}[fuel_type]
    stations=[]
    for f in features:
        p=f.get("properties",{}); g=f.get("geometry") or {}; c=g.get("coordinates")
        if not c or len(c)<2: continue
        try: price=float(p.get(price_field)); lon,lat=float(c[0]),float(c[1])
        except (TypeError,ValueError): continue
        d=closest_route_distance(lat,lon,geometry)
        if d>max_km: continue
        unavailable=str(p.get("carburants_indisponibles","")); temporary=str(p.get("carburants_rupture_temporaire","")); definitive=str(p.get("carburants_rupture_definitive",""))
        status="Indisponible" if fuel_type in unavailable or fuel_type in temporary or fuel_type in definitive else "Disponible"
        stations.append({"id":str(p.get("id","")),"name":f"{p.get('adresse','')}, {p.get('ville','')}".strip(", "),"lat":lat,"lon":lon,"price":price,"availability":status,"distance_from_route":d,"updated":p.get(price_field.replace("_prix","_maj"),"")})
    stations.sort(key=lambda x:x["distance_from_route"])
    return stations[:limit]
