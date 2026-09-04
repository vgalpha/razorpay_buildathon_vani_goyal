"""Order-id sourcing: synthetic (default) or real Razorpay test-mode orders.

The single place that knows whether order data is real or synthetic --
callers elsewhere just get a list of order_ids either way. mode="live" fails
loudly on any error rather than falling back to synthetic data, since silently
mislabeling synthetic data as real would undercut the whole point of drawing
this distinction in the first place.
"""

import os
import random
import string
import time

RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


def load_orders(count, mode="synthetic", seed=None):
  if mode == "synthetic":
    return _synthetic_orders(count, seed)
  if mode == "live":
    return _live_orders(count)
  raise ValueError(f"unknown mode: {mode!r} (expected 'synthetic' or 'live')")


def _synthetic_orders(count, seed):
  rng = random.Random(seed)
  chars = string.ascii_letters + string.digits
  return ["order_" + "".join(rng.choice(chars) for _ in range(14))
          for _ in range(count)]


def _live_orders(count):
  import requests  # local import: only needed on the live path
  key_id, key_secret = _load_credentials()
  order_ids = []
  for i in range(count):
    order_ids.append(_create_one_order(requests, key_id, key_secret, i))
  return order_ids


def _load_credentials():
  key_id = os.environ.get("RAZORPAY_KEY_ID")
  key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
  if key_id and key_secret:
    return key_id, key_secret
  key_id, key_secret = _read_dotenv()
  if not key_id or not key_secret:
    raise RuntimeError(
      "RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET not found in the environment or "
      f".env ({_ENV_PATH}). mode='live' requires real test-mode credentials.")
  return key_id, key_secret


def _read_dotenv():
  values = {}
  if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH) as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
          k, v = line.split("=", 1)
          values[k.strip()] = v.strip()
  return values.get("RAZORPAY_KEY_ID"), values.get("RAZORPAY_KEY_SECRET")


def _create_one_order(requests, key_id, key_secret, index):
  payload = {
    "amount": 100_00,
    "currency": "INR",
    "receipt": f"reconciler_{int(time.time())}_{index}",
  }
  try:
    resp = requests.post(RAZORPAY_ORDERS_URL, json=payload,
                          auth=(key_id, key_secret), timeout=10)
    resp.raise_for_status()
  except requests.RequestException as e:
    raise RuntimeError(f"Razorpay order creation failed at index {index}: {e}") from e
  return resp.json()["id"]
