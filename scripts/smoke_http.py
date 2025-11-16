import sys

import httpx


def main() -> int:
    base = "http://127.0.0.1:5000"
    results: list[tuple[str, int, str | None]] = []

    try:
        with httpx.Client(
            base_url=base, follow_redirects=False, timeout=10
        ) as s:
            r = s.get("/")
            results.append(("GET /", r.status_code, r.headers.get("location")))

            r = s.get("/login")
            results.append(("GET /login", r.status_code, None))

            r = s.post(
                "/login",
                data={"username": "admin", "password": "dev123"},
            )
            results.append(
                ("POST /login", r.status_code, r.headers.get("location"))
            )

            # Reuse cookies and follow redirects
            s = httpx.Client(
                base_url=base,
                follow_redirects=True,
                timeout=10,
                cookies=s.cookies,
            )
            r = s.get("/dashboard")
            results.append(("GET /dashboard", r.status_code, None))

            r = s.get("/pacientes/")
            results.append(("GET /pacientes/", r.status_code, None))
    except Exception as e:
        print(f"Smoke error: {e}")
        return 2

    # Print results and compute a simple pass/fail
    ok = True
    for name, code, loc in results:
        loc_txt = f" -> {loc}" if loc else ""
        print(f"{name:<18} -> {code}{loc_txt}")

    # Expectations
    expected = {
        "GET /": {302, 301, 200},
        "GET /login": {200},
        "POST /login": {302},
        "GET /dashboard": {200},
        "GET /pacientes/": {200},
    }

    for name, code, _ in results:
        if code not in expected.get(name, {200}):
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
