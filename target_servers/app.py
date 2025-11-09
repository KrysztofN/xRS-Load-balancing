from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/compute', methods=['POST'])
def compute_request():
    data = request.json
    n = data.get("number")
    if n <= 1:
        res = False
    elif n == 2:
        res = True
    else:
        res = True
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0:
                res = False
                break
    
    return jsonify({"is_prime": res, "number": n})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)