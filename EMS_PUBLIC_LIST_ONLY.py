#!/usr/bin/env python3
import requests
import zipfile
import io
import os
import csv

# Disable SSL warnings for self-signed certs (optional).
# In production, you'd want to validate the cert instead.
requests.packages.urllib3.disable_warnings()

############################################
# 1) Log in to EMS
############################################

LOGIN_URL = "https://fctems.fortidemo.com/api/v1/auth/signin"
EXPORT_URL = "https://fctems.fortidemo.com/api/v1/endpoints/export"

# Replace these with valid credentials for your EMS
USERNAME = r"corp\demo"
PASSWORD = "Fortinet1"

# Create a session so cookies persist across requests
session = requests.Session()

# Common headers (similar to what the browser sends)
common_headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

# Prepare login payload
login_payload = {
    "name": USERNAME,
    "password": PASSWORD
}

print("[*] Logging in to EMS...")

# Send the login request
resp_login = session.post(
    LOGIN_URL,
    json=login_payload,
    headers={**common_headers, "Content-Type": "application/json"},
    verify=False  # set to True if you have a valid certificate
)

if resp_login.status_code != 200:
    print(f"[!] Login failed: HTTP {resp_login.status_code}")
    print(resp_login.text)
    exit(1)

print("[*] Login success. Session cookies obtained.")


############################################
# 2) Download the ZIP (contains the CSV)
############################################

print("[*] Downloading endpoints export...")

# We’ll add an X-CSRFToken header if needed. Typically EMS checks it.
csrftoken = session.cookies.get("csrftoken", None)
export_headers = {
    **common_headers,
    "Ems-Call-Type": "2",
}
if csrftoken:
    export_headers["X-CSRFToken"] = csrftoken

resp_export = session.get(EXPORT_URL, headers=export_headers, verify=False)

if resp_export.status_code != 200:
    print(f"[!] Export failed: HTTP {resp_export.status_code}")
    print(resp_export.text)
    exit(1)

zip_filename = "endpoints_export.zip"
with open(zip_filename, "wb") as f:
    f.write(resp_export.content)

print(f"[*] Export ZIP saved as: {zip_filename}")


############################################
# 3) Extract the ZIP to get the CSV
############################################

extracted_folder = "exported_files"
os.makedirs(extracted_folder, exist_ok=True)

with zipfile.ZipFile(io.BytesIO(resp_export.content)) as z:
    z.extractall(extracted_folder)

print(f"[*] Files extracted to '{extracted_folder}'")

############################################
# 4) Parse the CSV for "public_ip_addr"
############################################

# We expect something like "endpoints.csv" inside the ZIP.
# Let's look for any CSV file; if you know the exact filename, you can just use it.
csv_file_path = None
for name in os.listdir(extracted_folder):
    if name.lower().endswith(".csv"):
        csv_file_path = os.path.join(extracted_folder, name)
        break

if not csv_file_path:
    print("[!] No CSV file found in the ZIP.")
    exit(1)

print(f"[*] Parsing CSV: {csv_file_path}")

# Grab all values under the "public_ip_addr" column
public_ips = []

with open(csv_file_path, "r", encoding="utf-8", newline="") as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)

    if not headers:
        print("[!] CSV appears to be empty.")
        exit(1)

    # Find the index of "public_ip_addr" column
    try:
        ip_col_index = headers.index("public_ip_addr")
    except ValueError:
        print("[!] 'public_ip_addr' column not found in the CSV headers.")
        exit(1)

    # Iterate rows and collect IPs
    for row in reader:
        if len(row) <= ip_col_index:
            continue
        ip_val = row[ip_col_index].strip()
        if ip_val:
            public_ips.append(ip_val)

############################################
# 5) Write the IP addresses to a file
############################################

with open("public_ips.txt", "w", encoding="utf-8") as out_f:
    for ip in public_ips:
        out_f.write(ip + "\n")

print(f"[*] Found {len(public_ips)} public IP(s). Saved to public_ips.txt.")
