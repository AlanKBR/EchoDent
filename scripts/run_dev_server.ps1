# Starts the Flask app for local E2E runs
$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = "1"
python run.py