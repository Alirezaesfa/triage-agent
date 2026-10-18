from flask import Flask, request, jsonify, send_from_directory
from product_agent import ask_products

app = Flask(__name__)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()
    history = data.get("history", [])

    if not question:
        return jsonify({"answer": "Please describe your problem.", "follow_up": False})

    try:
        answer, follow_up = ask_products(question, history)
    except Exception as error:
        print("Error while answering:", error)
        return jsonify({"answer": "Something went wrong. Check the terminal running server.py.", "follow_up": False})

    return jsonify({"answer": answer, "follow_up": follow_up})


if __name__ == "__main__":
    app.run(port=5000)