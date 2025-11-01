# Starts the Flask app for local E2E runs
$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = "1"

# Prefer the workspace virtualenv python if available
$venvPython = "A:/programa/EchoDent/.venv/Scripts/python.exe"
if (Test-Path $venvPython) {
	& $venvPython run.py
} else {
	python run.py
}