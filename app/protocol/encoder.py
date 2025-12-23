import base64

def build_payload(cmd: dict) -> bytes:
    """
    Build raw bytes to send over TCP based on command definition.
    cmd keys expected:
      - payload (str)
      - encoding: ascii | hex | base64
      - append_null, append_cr, append_lf (bool)
    """

    encoding = cmd["encoding"]
    payload = cmd["payload"]

    if encoding == "ascii":
        data = payload.encode("ascii", errors="strict")

    elif encoding == "hex":
        # Accept formats like: "01 03 00 00 00 02" or "010300000002"
        data = bytes.fromhex(payload.replace(" ", ""))

    elif encoding == "base64":
        data = base64.b64decode(payload)

    else:
        raise ValueError(f"Unsupported encoding: {encoding}")

    if cmd.get("append_cr"):
        data += b"\r"
    if cmd.get("append_lf"):
        data += b"\n"
    if cmd.get("append_null"):
        data += b"\x00"

    return data
