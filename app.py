from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Bem-vindo caralho!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
