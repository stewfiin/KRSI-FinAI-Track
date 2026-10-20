import datetime
import json
import urllib.error
import urllib.request


def request(url, method="GET", data=None, token=None):
    req_data = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"http://127.0.0.1:8000{url}", data=req_data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return (
                resp.status,
                json.loads(resp.read().decode()) if resp.status != 204 else None,
            )
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_finance_workflow():
    # 1. Login
    status, res = request(
        "/api/v1/auth/login",
        "POST",
        {"email": "test@example.com", "password": "password123"},
    )
    assert status == 200, f"Login failed: {res}"
    token = res["access_token"]

    # 2. Get Wallets
    status, wallets = request("/api/v1/wallets", "GET", token=token)
    assert status == 200 and len(wallets) >= 1
    tunai_wallet = wallets[0]

    # 3. Create BCA Wallet
    status, bca_wallet = request(
        "/api/v1/wallets",
        "POST",
        {"name": "BCA Test", "type": "bank", "balance": 500000},
        token=token,
    )
    assert status == 201

    # 4. Get Categories
    status, categories = request("/api/v1/categories", "GET", token=token)
    assert status == 200
    food_cat = next(c for c in categories if c["name"] == "Makanan & Minuman")
    salary_cat = next(c for c in categories if c["name"] == "Gaji")

    # 5. Create Budget for Food (100,000)
    today = datetime.date.today()
    status, budget = request(
        "/api/v1/budgets",
        "POST",
        {
            "category_id": food_cat["id"],
            "amount_limit": 100000,
            "month": today.month,
            "year": today.year,
        },
        token=token,
    )
    assert status in (201, 400)

    # 6. Add Income to BCA
    status, tx_income = request(
        "/api/v1/transactions",
        "POST",
        {
            "wallet_id": bca_wallet["id"],
            "category_id": salary_cat["id"],
            "amount": 1000000,
            "type": "income",
            "description": "Gaji Bulanan",
        },
        token=token,
    )
    assert status == 201

    # 7. Add Expense & Check Budget Alert
    status, tx_exp = request(
        "/api/v1/transactions",
        "POST",
        {
            "wallet_id": tunai_wallet["id"],
            "category_id": food_cat["id"],
            "amount": 85000,
            "type": "expense",
            "description": "Makan Siang Restoran",
        },
        token=token,
    )
    assert status == 201
    assert tx_exp["budget_alert"] is not None

    # 8. Dashboard Summary
    status, summary = request("/api/v1/dashboard/summary", "GET", token=token)
    assert status == 200
    assert float(summary["monthly_income"]) >= 1000000

    print("Finance workflow integration test completed successfully.")


if __name__ == "__main__":
    test_finance_workflow()

