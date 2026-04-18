from app import create_app

# Entry point used by `flask run` and `python run.py`.
app = create_app()

if __name__ == "__main__":
    # debug=True is convenient for local development only.
    app.run(debug=True)
