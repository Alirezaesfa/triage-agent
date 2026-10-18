from flask import Flask, request, jsonify, send_from_directory
from product_agent import ask_products

app = Flask(__name__)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/ask", methods=["POST"])
def ask():
    question = request.get_json().get("question", "").strip()
    if not question:
        return jsonify({"answer": "Please describe your problem."})

    try:
        answer = ask_products(question)
    except Exception as error:
        print("Error while answering:", error)
        return jsonify({"answer": "Something went wrong. Check the terminal running server.py."})

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(port=5000)