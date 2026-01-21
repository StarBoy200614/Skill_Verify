import requests

base_url = "http://localhost:5000"

routes = [
    "/",
    "/organizations",
    "/careers?cat=cs",
    "/community",
    "/about"
]

print("Verifying Navigation Routes...")
all_passed = True
for route in routes:
    try:
        response = requests.get(f"{base_url}{route}")
        print(f"Checking {route}: {response.status_code}")
        if response.status_code != 200:
            all_passed = False
            print(f"FAIL: {route}")
    except Exception as e:
        print(f"Error checking {route}: {e}")
        all_passed = False

if all_passed:
    print("PASS: All navigation routes verified!")
else:
    print("FAIL: Some routes failed.")
