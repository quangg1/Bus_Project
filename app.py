from flask import Flask, request, jsonify, render_template
from Run_Bus_Project import *
from flask_cors import CORS
from flask_caching import Cache
from flask_compress import Compress
app = Flask(__name__)
cache = Cache(app)
CORS(app)
Compress(app)
@app.route('/found_route', methods=['POST'])
@cache.cached(timeout=60)
def found_route():
    # Lấy dữ liệu từ request JSON
    print("Received POST request")
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    start_address = data.get('start_address')
    end_address = data.get('end_address')

    # Gọi hàm xử lý logic tìm lộ trình
    result = find_route(start_address, end_address)

    # Kiểm tra kết quả trả về
    if result['status'] == 'error':
        return jsonify({'status': 'error', 'message': result['message']})

    # Lấy các thông tin cần thiết từ kết quả (lộ trình và trạm dừng)
    path = result['data']['path']
    stops = result['data']['stops']
    route=result['data']['routes']
    start_distance=result['data']['start_distance']
    end_distance =result['data']['end_distance']
    total_distance=result['data']['total_distance']
    start_path=result['data']['start_path']
    end_path=result['data']['end_path']

    # Định dạng lại dữ liệu trả về để phù hợp với yêu cầu frontend
    bus_stops = load_bus_stops()  # Tải lại danh sách trạm xe buýt
    route_data = {
        'path': [{'lat': bus_stops[stop]['lat'], 'lon': bus_stops[stop]['lon']} for stop in path],
        'stops': stops, 'routes':route,'start_distance':start_distance,'end_distance':end_distance,'total_distance':total_distance,
        'end_path':end_path,'start_path':start_path
    }
    print(route_data)
    # Trả về dữ liệu JSON
    return jsonify({'status': 'success', 'data': route_data})
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
