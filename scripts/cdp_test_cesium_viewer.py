"""One-off CDP driver for testing the Phase 8 Cesium viewer's interactive features
(class toggle, confidence overlay, click-to-measure) — same throwaway-harness
rationale as cdp_test_viewer.py."""
import asyncio
import base64
import json
import urllib.request

import websockets


async def send_session(bws, session_id, msg_id, method, params=None):
    await bws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}, "sessionId": session_id}))
    while True:
        resp = json.loads(await bws.recv())
        if resp.get("id") == msg_id and resp.get("sessionId") == session_id:
            return resp


async def send_top(bws, msg_id, method, params=None):
    await bws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        resp = json.loads(await bws.recv())
        if resp.get("id") == msg_id:
            return resp


async def run():
    version = json.loads(urllib.request.urlopen("http://localhost:9333/json/version").read())
    async with websockets.connect(version["webSocketDebuggerUrl"], max_size=50_000_000) as bws:
        resp = await send_top(bws, 1, "Target.createTarget", {"url": "about:blank"})
        target_id = resp["result"]["targetId"]
        resp = await send_top(bws, 2, "Target.attachToTarget", {"targetId": target_id, "flatten": True})
        session_id = resp["result"]["sessionId"]

        await send_session(bws, session_id, 10, "Page.enable")
        await send_session(bws, session_id, 11, "Runtime.enable")
        await send_session(bws, session_id, 12, "Page.navigate", {"url": "http://localhost:8124/src/viewer/cesium_viewer.html"})
        await asyncio.sleep(25)  # Cesium + 2.8MB point data load, fresh profile = no cache

        status = await send_session(bws, session_id, 15, "Runtime.evaluate", {
            "expression": "document.getElementById('status').textContent", "returnByValue": True,
        })
        print("STATUS:", status.get("result",{}).get("result",{}).get("value", "ERROR: "+json.dumps(status)))

        # Click on a visible point cluster to test measurement (2 clicks).
        for x, y in [(400, 450), (800, 500)]:
            await send_session(bws, session_id, 20, "Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
            await send_session(bws, session_id, 21, "Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
            await asyncio.sleep(0.5)

        measurement = await send_session(bws, session_id, 22, "Runtime.evaluate", {
            "expression": "document.getElementById('measurement').textContent", "returnByValue": True,
        })
        print("MEASUREMENT:", measurement.get("result",{}).get("result",{}).get("value", "ERROR: "+json.dumps(measurement)))

        shot = await send_session(bws, session_id, 30, "Page.captureScreenshot", {"format": "png"})
        with open("outputs/cesium_after_measure.png", "wb") as f:
            f.write(base64.b64decode(shot["result"]["data"]))

        # Toggle off "Road" checkbox (2nd checkbox) and confidence overlay checkbox.
        await send_session(bws, session_id, 40, "Runtime.evaluate", {
            "expression": """
                (function() {
                  const checkboxes = document.querySelectorAll('#class-toggles input[type=checkbox]');
                  let result = [];
                  checkboxes.forEach(cb => { result.push(cb.parentElement.textContent.trim()); });
                  checkboxes[1].click();  // toggle off the 2nd class (Road)
                  document.getElementById('confidence-toggle').click();  // enable confidence overlay
                  return result.join(' | ');
                })()
            """, "returnByValue": True,
        })
        await asyncio.sleep(1)

        shot2 = await send_session(bws, session_id, 50, "Page.captureScreenshot", {"format": "png"})
        with open("outputs/cesium_after_toggle.png", "wb") as f:
            f.write(base64.b64decode(shot2["result"]["data"]))

        print("Screenshots saved.")
        await send_top(bws, 60, "Target.closeTarget", {"targetId": target_id})


if __name__ == "__main__":
    asyncio.run(run())
