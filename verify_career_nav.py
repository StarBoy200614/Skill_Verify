import requests

base_url = "http://localhost:5000"

# Routes and expected/unexpected terms in navigation
checks = [
    {
        "url": "/careers/cs",
        "expected": [
            'href="/careers/habitation">Habitation</a>',
            'href="/careers/polsci">Political Science</a>'
        ],
        "unexpected": [
            'href="/community">Community</a>',
            'href="/organizations">for Organizations</a>'
        ]
    },
    {
        "url": "/careers/habitation",
        "expected": [
            'href="/careers/cs">Computer Science</a>',
            'href="/careers/polsci">Political Science</a>'
        ],
        "unexpected": [
            'href="/community">Community</a>'
        ]
    },
    {
        "url": "/careers/polsci",
        "expected": [
            'href="/careers/cs">Computer Science</a>',
            'href="/careers/habitation">Habitation</a>'
        ],
        "unexpected": [
            'href="/community">Community</a>'
        ]
    }
]

print("Verifying Career Branch Navigation...")
all_passed = True

for check in checks:
    route = check["url"]
    try:
        response = requests.get(f"{base_url}{route}")
        content = response.text
        
        print(f"Checking {route}...")
        
        if response.status_code != 200:
            print(f"  FAIL: Status code {response.status_code}")
            all_passed = False
            continue

        # Check expected
        for exp in check["expected"]:
            if exp in content:
                print(f"  PASS: Found '{exp}'")
            else:
                print(f"  FAIL: Missing '{exp}'")
                all_passed = False

        # Check unexpected
        for unexp in check["unexpected"]:
            if unexp not in content:
                print(f"  PASS: Did not find '{unexp}'")
            else:
                print(f"  FAIL: Found unexpected '{unexp}'")
                all_passed = False
                
    except Exception as e:
        print(f"Error checking {route}: {e}")
        all_passed = False

if all_passed:
    print("\nOVERALL: PASS")
else:
    print("\nOVERALL: FAIL")
