import requests
import heapq
from math import radians, sin, cos, sqrt, atan2
import json
from flask import Flask, jsonify
from flask_cors import CORS
import re
# Hàm chuyển đổi địa chỉ sang tọa độ GPS
app = Flask(__name__) 
CORS(app) 
def geocode_address(address):
    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json"
    headers = {
        "User-Agent": "YourAppName (your_email@example.com)"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return lat, lon
            else:
                print("Không tìm thấy dữ liệu cho địa chỉ đã nhập.")
                return None, None
        except ValueError:
            print("Lỗi trong quá trình chuyển đổi dữ liệu JSON.")
            return None, None
    else:
        print(f"Lỗi kết nối API: {response.status_code}")
        return None, None

# Hàm tính khoảng cách giữa hai điểm dựa vào tọa độ GPS
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Bán kính trái đất trong km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c * 1000  # Chuyển đổi thành mét

# Tải dữ liệu trạm xe buýt trong khu vực
import requests
import json

def load_bus_stops():
    url = "https://overpass-api.de/api/interpreter"

    # Truy vấn lấy dữ liệu các trạm xe buýt trong khu vực từ Cầu Sài Gòn đến cuối quận Tân Phú
    query_stops = """
    [out:json];
    node["highway"="bus_stop"](10.7672, 106.6053, 10.8031, 106.7304);
    out body;
    """

    response_stops = requests.get(url, params={'data': query_stops})
    if response_stops.status_code != 200:
        print(f"Error fetching bus stops: {response_stops.status_code}")
        return {}
    data_stops = response_stops.json()

    # Lưu danh sách các trạm xe buýt với thông tin tọa độ
    bus_stops = {}
    for element in data_stops.get("elements", []):
        lat = element["lat"]
        lon = element["lon"]
        stop_name = element["tags"].get("name", "Unknown")
        # Kiểm tra xem có id không, nếu không tạo một id mới từ tọa độ
        stop_id = element.get("id", f"{lat}_{lon}")
        bus_stops[stop_id] = {"name": stop_name, "lat": lat, "lon": lon, "routes": []}

    # Truy vấn tất cả các tuyến xe buýt trong khu vực để tìm các tuyến đi qua các trạm
    query_routes = """
    [out:json];
    area["name"="Ho Chi Minh City"]->.searchArea;
    relation["route"="bus"](10.7672, 106.6053, 10.8031, 106.7304);
    out body;
    """

    response_routes = requests.get(url, params={'data': query_routes})
    if response_routes.status_code != 200:
        print(f"Error fetching bus routes: {response_routes.status_code}")
        return bus_stops
    data_routes = response_routes.json()

    # Liên kết các tuyến xe buýt với các trạm dừng, loại bỏ tuyến có dấu gạch ngang trong tên
    for relation in data_routes.get("elements", []):
        route_name = relation.get("tags", {}).get("ref", "Unknown Route")
        
        # Loại bỏ tuyến có dấu gạch ngang trong tên
        if "-" in route_name:
            continue  # Bỏ qua tuyến có dấu gạch ngang

        for member in relation.get("members", []):
            if member["type"] == "node" and member["ref"] in bus_stops:
                bus_stops[member["ref"]]["routes"].append(route_name)

    # Giả sử chúng ta muốn tìm các trạm xe buýt và so sánh chúng
    # (Dùng phương thức .get() để tránh lỗi KeyError)
    route_stops_sorted = []
    for stop_id, info in bus_stops.items():
        for route in info["routes"]:
            route_stops_sorted.append({"id": stop_id, "routes": info["routes"], "lat": info["lat"], "lon": info["lon"]})

    # Sắp xếp các trạm theo tên tuyến và tọa độ
    route_stops_sorted = sorted(route_stops_sorted, key=lambda x: (x["routes"].index(route) if route in x["routes"] else -1, x["lat"], x["lon"]))
    
    # Lưu dữ liệu vào file JSON
    with open('bus_stops.json', 'w') as json_file:
        json.dump(bus_stops, json_file)

    return bus_stops
    return jsonify(bus_stops)


                

# Tìm các trạm xe buýt trong bán kính 500m
def find_nearest_stops(lat, lon, bus_stops, radius=500):
    nearby_stops = []
    
    for stop_id, info in bus_stops.items():
        # Tính khoảng cách giữa lat, lon với trạm xe buýt
        distance = haversine(lat, lon, info["lat"], info["lon"])
        
        # Nếu vị trí trùng với trạm xe buýt, đặt distance = 0
        if lat == info["lat"] and lon == info["lon"]:
            distance = 0
        
        # Nếu trạm trong bán kính, thêm vào danh sách
        if distance <= radius:
            nearby_stops.append((stop_id, distance))
    
    # Sắp xếp các trạm xe buýt gần nhất, đảm bảo trạm có distance=0 luôn ở đầu
    
    return sorted(nearby_stops, key=lambda x: x[1])

# Xây dựng đồ thị với khoảng cách giữa các trạm lân cận
def build_graph(bus_stops):
    graph = {}
    route_to_stops = {}

    # Khởi tạo đồ thị cho mỗi trạm
    for stop_id in bus_stops:
        graph[stop_id] = []

    # Lặp qua các tuyến xe buýt và trạm xe buýt
    for stop_id, info in bus_stops.items():
        for route in info["routes"]:
            if route not in route_to_stops:
                route_to_stops[route] = []

            route_to_stops[route].append(stop_id)

    # Xây dựng kết nối giữa các trạm trên cùng một tuyến
    for route, stops in route_to_stops.items():
        for i in range(len(stops) - 1):
            stop_id_1 = stops[i]
            stop_id_2 = stops[i + 1]

            lat1, lon1 = bus_stops[stop_id_1]["lat"], bus_stops[stop_id_1]["lon"]
            lat2, lon2 = bus_stops[stop_id_2]["lat"], bus_stops[stop_id_2]["lon"]

            distance = haversine(lat1, lon1, lat2, lon2)  # Tính khoảng cách giữa các trạm

            # Thêm các kết nối vào đồ thị
            graph[stop_id_1].append((stop_id_2, distance))
            graph[stop_id_2].append((stop_id_1, distance))  # Đảm bảo kết nối ngược lại

    return graph
def save_graph_to_file(graph, filename="graph.json"):
    with open(filename, 'w') as f:
        json.dump(graph, f, indent=4)
    print(f"Đồ thị đã được lưu vào {filename}")
# Thuật toán Dijkstra để tìm đường đi ngắn nhất giữa hai trạm
def dijkstra(graph, start, end):
    queue = [(0, start)]
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    previous_nodes = {node: None for node in graph}

    while queue:
        current_distance, current_node = heapq.heappop(queue)

        if current_node == end:
            break

        if current_distance > distances[current_node]:
            continue

        for neighbor, weight in graph[current_node]:
            distance = current_distance + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(queue, (distance, neighbor))

    path = []
    current = end
    while current is not None:
        path.append(current)
        current = previous_nodes[current]
    path.reverse()

    return path, distances[end]

# Tìm trạm khởi đầu tối ưu
def find_optimal_start_stop(start_lat, start_lon, end_lat, end_lon, bus_stops, graph, start_radius=500, end_radius=500):
    # Tìm các trạm xe buýt gần điểm xuất phát và điểm đến
    nearby_start_stops = find_nearest_stops(start_lat, start_lon, bus_stops, radius=start_radius)
    nearby_end_stops = find_nearest_stops(end_lat, end_lon, bus_stops, radius=end_radius)
    if not nearby_start_stops:
        print("Không tìm thấy trạm xe buýt gần điểm xuất phát.")
        return None

    if not nearby_end_stops:
        print("Không tìm thấy trạm xe buýt gần điểm đến.")
        return None

    optimal_start_stop = None
    optimal_end_stop = None
    min_distance = float('inf')  # Khoảng cách tối thiểu giữa các trạm
    
    # Kiểm tra nếu tọa độ xuất phát hoặc đích đã trùng với trạm xe buýt có sẵn
    for stop_id, info in bus_stops.items():
        if info["lat"] == start_lat and info["lon"] == start_lon:
            optimal_start_stop = stop_id
            break  # Dừng lại ngay khi tìm thấy điểm xuất phát là trạm xe buýt
    for stop_id, info in bus_stops.items():
        if info["lat"] == end_lat and info["lon"] == end_lon:
            optimal_end_stop = stop_id
            break  # Dừng lại ngay khi tìm thấy điểm đích là trạm xe buýt
        
    if optimal_start_stop and optimal_end_stop:
        path, distance = dijkstra(graph, optimal_start_stop, optimal_end_stop)
        return optimal_start_stop, optimal_end_stop
    end_stop_id= nearby_end_stops[0][0]
    
    # Duyệt qua tất cả các trạm kề điểm xuất phát và điểm đến
    for start_stop_id, _ in nearby_start_stops:
        if start_stop_id != end_stop_id:  # Đảm bảo trạm xuất phát và trạm kết thúc khác nhau
                # Tìm đường đi ngắn nhất giữa trạm xuất phát và trạm kết thúc
            path, distance = dijkstra(graph, start_stop_id, end_stop_id)
                # Kiểm tra nếu đường đi hợp lệ và là đường đi ngắn nhất
            if distance < min_distance:
                min_distance = distance
                optimal_start_stop = start_stop_id
                optimal_end_stop = end_stop_id
                optimal_path = path

    # Kiểm tra nếu không tìm thấy trạm tối ưu
    if optimal_start_stop is None or optimal_end_stop is None:
        print("Không tìm thấy trạm tối ưu.")
        return None
    return optimal_start_stop, optimal_end_stop

def is_within_bounds(lat, lon, bounds):
    """Kiểm tra xem tọa độ có nằm trong phạm vi cho trước không."""
    lat_min, lon_min, lat_max, lon_max = bounds
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max

def get_correct_coordinates_from_file(tram_name, file_path):
    """Đọc file graph.info.txt và lấy tọa độ của trạm nếu có tên trạm khớp."""
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # Tìm tên trạm sau "Trạm xe buýt:" và lấy tọa độ trong ngoặc
            match = re.match(r"Trạm xe buýt:\s*(.*)\s*\(Tọa độ: ([0-9.-]+),\s*([0-9.-]+)\)", line.strip())
            if match:
                tram_name_in_file = match.group(1).strip()
                lat = float(match.group(2))
                lon = float(match.group(3))
                
                # So sánh tên trạm
                if tram_name_in_file == tram_name:
                    return lat, lon
    return None, None   # Nếu không tìm thấy trạm trong file
# Tìm đường đi từ địa chỉ xuất phát đến địa chỉ đích
def parse_coordinates(address):
    # Kiểm tra xem chuỗi có định dạng (lat, lon) hay không
    pattern = r'^\s*\(?\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)?\s*$'
    match = re.match(pattern, address)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        return lat, lon
    return None, None
# Tìm tuyến chung giữa 2 tuyến
def find_common_routes(stop1_routes, stop2_routes):
    # Tìm các tuyến chung giữa hai trạm
    return list(set(stop1_routes) & set(stop2_routes))
def find_route(start_address, end_address, start_radius=500, end_radius=500):
    # Chuyển đổi địa chỉ sang tọa độ
    start_lat, start_lon = parse_coordinates(start_address)
    end_lat, end_lon = parse_coordinates(end_address)

# Nếu không phải định dạng (lat, lon), gọi hàm geocode_address
    if start_lat is None or start_lon is None:
        start_lat, start_lon = geocode_address(start_address)

    if end_lat is None or end_lon is None:
        end_lat, end_lon = geocode_address(end_address)

    bounds = (10.7672, 106.6053, 10.8031, 106.7304)  # Phạm vi cần kiểm tra

    if  not is_within_bounds(start_lat, start_lon, bounds):
        # Nếu tọa độ không hợp lệ, tìm trong graph.info.txt
        start_lat, start_lon = get_correct_coordinates_from_file(start_address, 'graph_info.txt')
        
    if not is_within_bounds(end_lat, end_lon, bounds):
        # Nếu tọa độ không hợp lệ, tìm trong graph.info.txt
        end_lat, end_lon = get_correct_coordinates_from_file(end_address, 'graph_info.txt')
    # Tải dữ liệu trạm và tuyến xe buýt
    bus_stops = load_bus_stops()
    graph = build_graph(bus_stops)

    # Tìm trạm khởi đầu tối ưu và trạm kết thúc tối ưu
    optimal_start_stop, optimal_end_stop = find_optimal_start_stop(
        start_lat, start_lon, end_lat, end_lon, bus_stops, graph, start_radius, end_radius)

    if not optimal_start_stop or not optimal_end_stop:
        return "Không tìm thấy trạm xe buýt tối ưu gần điểm xuất phát hoặc điểm đến."

    # Tính khoảng cách từ điểm xuất phát đến trạm `optimal_start_stop`
    start_to_optimal_start_distance = haversine(
        start_lat, start_lon, bus_stops[optimal_start_stop]["lat"], bus_stops[optimal_start_stop]["lon"]
    )

    # Tính khoảng cách từ trạm `optimal_end_stop` đến điểm đích
    optimal_end_to_end_distance = haversine(
        bus_stops[optimal_end_stop]["lat"], bus_stops[optimal_end_stop]["lon"], end_lat, end_lon
    )

    # Tìm lộ trình từ `optimal_start_stop` đến `optimal_end_stop`
    path, total_distance_between_stops = dijkstra(graph, optimal_start_stop, optimal_end_stop)
    path.insert(0, (start_lat, start_lon))
    path.append((end_lat, end_lon))
    
    # Tìm các tuyến thực sự mà 2 trạm đi qua
    filtered_routes = []
    for i in range(len(path[1:-1]) - 1):
        stop1 = path[1:-1][i]
        stop2 = path[1:-1][i + 1]
        stop1_routes = bus_stops[stop1]['routes']
        stop2_routes = bus_stops[stop2]['routes']
        common_routes = find_common_routes(stop1_routes, stop2_routes)
        filtered_routes.append(common_routes if common_routes else ['No Common Route'])
    route_data = {
    'path': path[1:-1],  # Bỏ qua trạm đầu và cuối trong path
    'stops': [bus_stops[stop]['name'] for stop in path[1:-1]],  # Lấy tên các trạm giữa
    'routes': filtered_routes,  # Lấy các tuyến đường của các trạm giữa
    'start_distance':start_to_optimal_start_distance,
    'end_distance':optimal_end_to_end_distance,
    'total_distance':total_distance_between_stops
}
    return {"status": "success", "data": route_data}


start_address="(10.77536, 106.62214)"

end_address="(10.77970, 106.63418)"
print(find_route(start_address,end_address))
# Tải dữ liệu trạm và tuyến xe buýt

# Tìm trạm khởi đầu tối ưu và trạm kết thúc tối ưu

# Ví dụ sử dụng
# Địa chỉ của điểm xuất phát và điểm đến
