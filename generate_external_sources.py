from datetime import datetime, timedelta
import json
import random
import string
from faker import Faker
import pandas as pd

fake = Faker()


def get_random_string(length=8):
  val_chars = string.ascii_uppercase + string.digits
  return "".join(random.choices(val_chars, k=length))


def generate_external_data():
  print("🔄 Starting generation of external JSON and CSV data sources...\n")

  # ----------------------------------------------------
  # 1. JSON Source #1: Clickstream / Web Session Logs (5,000 Events)
  # ----------------------------------------------------
  print("⏳ Generating 'clickstream_logs.json' (Web Activity Data)...")
  actions = [
      "page_view",
      "search",
      "add_to_cart",
      "remove_from_cart",
      "view_checkout",
      "apply_coupon",
  ]
  devices = ["Mobile_iOS", "Mobile_Android", "Desktop_Windows", "Desktop_MacOS"]
  browsers = ["Chrome", "Safari", "Firefox", "Edge"]

  clickstream_data = []
  for i in range(1, 5001):
    event_time = fake.date_time_between(start_date="-1y", end_date="now")
    clickstream_data.append({
        "event_id": f"EVT-{get_random_string(10)}",
        "user_id": random.randint(1, 2000),  # Maps to PostgreSQL users
        "session_id": f"SES-{get_random_string(8)}",
        "action": random.choice(actions),
        "product_id": (
            random.randint(1, 500) if random.random() < 0.7 else None
        ),
        "device_type": random.choice(devices),
        "browser": random.choice(browsers),
        "ip_address": fake.ipv4(),
        "timestamp": event_time.strftime("%Y-%m-%d %H:%M:%S"),
    })

  with open("clickstream_logs.json", "w", encoding="utf-8") as f:
    json.dump(clickstream_data, f, indent=4, ensure_ascii=False)
  print("✅ Saved 'clickstream_logs.json' (5,000 records).")

  # ----------------------------------------------------
  # 2. JSON Source #2: CRM Customer Support Tickets (1,500 Tickets)
  # ----------------------------------------------------
  print("\n⏳ Generating 'crm_interactions.json' (Customer Support Data)...")
  ticket_categories = [
      "Delayed Delivery",
      "Refund Request",
      "Wrong Item Received",
      "Payment Failure",
      "General Query",
  ]
  ticket_statuses = ["Closed", "Closed", "Closed", "In Progress", "Open"]
  priorities = ["Low", "Medium", "High", "Urgent"]

  crm_data = []
  for i in range(1, 1501):
    created_date = fake.date_time_between(start_date="-1y", end_date="now")
    crm_data.append({
        "ticket_id": f"TKT-{get_random_string(6)}",
        "user_id": random.randint(1, 2000),
        "order_id": random.randint(1, 10000),  # Maps to PostgreSQL orders
        "category": random.choice(ticket_categories),
        "priority": random.choice(priorities),
        "status": random.choice(ticket_statuses),
        "satisfaction_score": (
            random.randint(1, 5) if random.random() < 0.8 else None
        ),
        "created_at": created_date.strftime("%Y-%m-%d %H:%M:%S"),
    })

  with open("crm_interactions.json", "w", encoding="utf-8") as f:
    json.dump(crm_data, f, indent=4, ensure_ascii=False)
  print("✅ Saved 'crm_interactions.json' (1,500 records).")

  # ----------------------------------------------------
  # 3. CSV Source #1: Shipping Partners Rates & Service Metrics
  # ----------------------------------------------------
  print(
      "\n⏳ Generating 'shipping_partners.csv' (Carrier Rates & SLA Metrics)..."
  )
  carriers = ["FedEx", "DHL", "Aramex", "UPS"]
  shipping_csv_data = []

  for carrier in carriers:
    for zone in ["Domestic-Local", "Domestic-Regional", "International"]:
      shipping_csv_data.append({
          "carrier_name": carrier,
          "service_zone": zone,
          "base_shipping_rate": round(
              random.uniform(10.0, 40.0)
              * (2.5 if zone == "International" else 1.0),
              2,
          ),
          "fuel_surcharge_pct": round(random.uniform(0.02, 0.08), 3),
          "target_sla_days": 2 if zone == "Domestic-Local" else (5 if zone == "Domestic-Regional" else 10),
          "carrier_contact_email": f"support@{carrier.lower()}.com",
      })

  df_shipping = pd.DataFrame(shipping_csv_data)
  df_shipping.to_csv("shipping_partners.csv", index=False)
  print("✅ Saved 'shipping_partners.csv' (12 records).")

  # ----------------------------------------------------
  # 4. CSV Source #2: Suppliers Costs & Lead Times (100 Suppliers)
  # ----------------------------------------------------
  print(
      "\n⏳ Generating 'suppliers_costs.csv' (Supplier Operational Data)..."
  )
  suppliers_data = []

  for i in range(1, 101):
    suppliers_data.append({
        "supplier_id": f"SUP-{1000 + i}",
        "supplier_name": fake.company(),
        "country": fake.country(),
        "primary_contact": fake.name(),
        "contact_phone": fake.phone_number()[:20],
        "lead_time_days": random.randint(3, 21),
        "minimum_order_qty": random.choice([50, 100, 200, 500]),
        "reliability_rating": round(random.uniform(3.5, 5.0), 1),
    })

  df_suppliers = pd.DataFrame(suppliers_data)
  df_suppliers.to_csv("suppliers_costs.csv", index=False)
  print("✅ Saved 'suppliers_costs.csv' (100 records).")

  print(
      "\n🎉 All external JSON and CSV data files generated successfully!"
  )


if __name__ == "__main__":
  generate_external_data()