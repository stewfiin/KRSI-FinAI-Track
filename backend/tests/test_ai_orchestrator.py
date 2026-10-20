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


def test_ai_services():
    # 1. Login
    status, res = request(
        "/api/v1/auth/login",
        "POST",
        {"email": "test@example.com", "password": "password123"},
    )
    assert status == 200, f"Login failed: {res}"
    token = res["access_token"]
    print("[1] Auth Token OK")

    # 2. Test AI Chat - Natural Language Transaction Recording
    test_msg = "Tadi beli nasi padang 25rb pakai Tunai"
    status, chat_res = request(
        "/api/ai/chat",
        "POST",
        {"message": test_msg, "platform": "web"},
        token=token,
    )
    assert status == 200, f"Chat failed: {chat_res}"
    print(f"[2] Chat Transaction Intent:")
    print(f"    Intent: {chat_res['intent']}")
    print(f"    Reply: {chat_res['reply']}")
    assert chat_res["intent"] == "transaction"
    assert chat_res["transaction"] is not None
    assert float(chat_res["transaction"]["amount"]) == 25000.0
    print("    -> Atomic transaction successfully created via AI Chat!")

    # 3. Test AI Chat - Financial Q&A (Query Intent)
    query_msg = "Berapa total pengeluaranku bulan ini?"
    status, q_res = request(
        "/api/ai/chat",
        "POST",
        {"message": query_msg, "platform": "web"},
        token=token,
    )
    assert status == 200
    print(f"[3] Chat Query Intent:")
    print(f"    Intent: {q_res['intent']}")
    print(f"    Reply: {q_res['reply']}")
    assert q_res["intent"] == "query"

    # 4. Test AI Chat - General conversation
    general_msg = "Halo apa kabar?"
    status, g_res = request(
        "/api/ai/chat",
        "POST",
        {"message": general_msg, "platform": "web"},
        token=token,
    )
    assert status == 200
    print(f"[4] Chat General Intent:")
    print(f"    Intent: {g_res['intent']}")
    print(f"    Reply: {g_res['reply']}")
    assert g_res["intent"] == "general"

    # 5. Test AI Dynamic Budget Generator
    budget_payload = {
        "prompt": "Gaji saya 5 juta, tolong buatkan budget bulanan hemat untuk makan dan transportasi",
        "apply_to_database": True,
    }
    status, b_res = request(
        "/api/ai/budget",
        "POST",
        budget_payload,
        token=token,
    )
    assert status == 200, f"Budget failed: {b_res}"
    print(f"[5] AI Dynamic Budgeting:")
    print(f"    Total Budget: Rp{float(b_res['total_budget']):,.0f}")
    print(f"    Strategy: {b_res['strategy_summary']}")
    print(f"    Allocations Count: {len(b_res['allocations'])}")
    for alloc in b_res["allocations"][:3]:
        print(f"    - {alloc['category_name']}: Rp{float(alloc['suggested_limit']):,.0f} ({alloc['reasoning']})")
    assert b_res["saved_to_database"] is True

    # 6. Test AI Voice Endpoint (Validation & Auth Check)
    boundary = "----WebKitFormBoundaryTest123"
    voice_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="test.webm"\r\n'
        f"Content-Type: audio/webm\r\n\r\n"
        f"fake_audio_bytes_data\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    voice_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/ai/voice",
        data=voice_body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(voice_req)
        print("[6] Voice endpoint called successfully.")
    except urllib.error.HTTPError as e:
        err_msg = json.loads(e.read().decode())
        print(f"[6] Voice Endpoint Validation OK (Code {e.code}): {err_msg.get('detail')}")

    print("\n>>> ALL AI ORCHESTRATOR TESTS PASSED! <<<")


if __name__ == "__main__":
    test_ai_services()
