"""One-off CDP driver script to click-test the Phase 4 viewer (not part of the
pipeline — a throwaway test harness since chromium-cli/playwright weren't available
in this environment, and system Chrome + raw CDP was the lightest path to actually
driving the page, not just loading it)."""
import asyncio
import base64
import json
import sys

import websockets


async def main():
    async with websockets.connect(
        "http://localhost:9333/json/version", ) as _:
        pass


async def send(ws, msg_id, method, params=None):
    await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == msg_id:
            return resp


async def run():
    import urllib.request

    version = json.loads(urllib.request.urlopen("http://localhost:9333/json/version").read())
    browser_ws_url = version["webSocketDebuggerUrl"]

    async with websockets.connect(browser_ws_url, max_size=50_000_000) as bws:
        resp = await send(bws, 1, "Target.createTarget", {"url": "about:blank"})
        target_id = resp["result"]["targetId"]
        resp = await send(bws, 2, "Target.attachToTarget", {"targetId": target_id, "flatten": True})
        session_id = resp["result"]["sessionId"]

        async def send_session(msg_id, method, params=None):
            await bws.send(json.dumps({
                "id": msg_id, "method": method, "params": params or {}, "sessionId": session_id
            }))
            while True:
                resp = json.loads(await bws.recv())
                if resp.get("id") == msg_id and resp.get("sessionId") == session_id:
                    return resp

        await send_session(10, "Page.enable")
        await send_session(11, "Runtime.enable")
        await send_session(12, "Page.navigate", {"url": "http://localhost:8123/index.html"})
        await asyncio.sleep(3)  # let three.js load + render the model

        # Two clicks on the canvas at different points, to trigger the measurement.
        for x, y in [(740, 360), (800, 395)]:
            await send_session(20, "Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1
            })
            await send_session(21, "Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1
            })
            await asyncio.sleep(0.5)

        await asyncio.sleep(1)

        console_logs = await send_session(30, "Runtime.evaluate", {
            "expression": "document.getElementById('measurement').textContent + '|' + document.getElementById('debug').textContent",
            "returnByValue": True,
        })
        print("MEASUREMENT+DEBUG TEXT:", console_logs["result"]["result"]["value"])

        shot = await send_session(40, "Page.captureScreenshot", {"format": "png"})
        img_data = base64.b64decode(shot["result"]["data"])
        with open("outputs/viewer_click_test.png", "wb") as f:
            f.write(img_data)
        print("Screenshot saved to outputs/viewer_click_test.png")

        await send(bws, 50, "Target.closeTarget", {"targetId": target_id})


if __name__ == "__main__":
    asyncio.run(run())
