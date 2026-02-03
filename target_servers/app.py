from flask import Flask, request, jsonify

app = Flask(__name__)

def fibonacci_recursive(n):
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)

@app.route('/compute', methods=['POST'])
def compute_request():
    data = request.json
    n = data.get('number', 10) + 15 
    
    result = fibonacci_recursive(n)
    return jsonify({"result": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)