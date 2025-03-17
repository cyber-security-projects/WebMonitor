from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Bem-vindo ao meu servidor Flask!"})

if __name__ == "__main__":
    app
