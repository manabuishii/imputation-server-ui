from flask import (
    Flask,
    render_template,
)

app = Flask(__name__)

# set the secret key.  keep this really secret:
app.secret_key = "k9SZr98j/3yX R~XHH!jmN]0d2,?RT"


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    # run host 0.0.0.0
    # Base.metadata.create_all(bind=ENGINE)

    app.run(
        debug=True,
        host="0.0.0.0",
    )
