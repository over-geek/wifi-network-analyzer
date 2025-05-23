import re
import csv
import logging
import requests
import os.path
from urllib.parse import quote

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the CSV OUI database
csv_oui_db = {}
csv_db_path = 'oui.csv'
try:
    if os.path.exists(csv_db_path):
        with open(csv_db_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 3:
                    # Ensure the prefix is normalized - remove colons and convert to lowercase
                    prefix = row[1].lower().replace(':', '')
                    vendor = row[2]
                    csv_oui_db[prefix] = vendor
        logger.info(f"Loaded {len(csv_oui_db)} OUI entries from CSV database")
        # Reload the DB when app is restarted
        import time

        time.sleep(0.5)  # Short pause to ensure file is completely written
    else:
        logger.warning(f"CSV OUI database not found at {csv_db_path}")
except Exception as e:
    logger.warning(f"Error loading CSV OUI database: {str(e)}")
    csv_oui_db = {}


def normalize_mac(mac):
    if not mac:
        return None, False

    # Remove non-hexadecimal characters
    mac = re.sub(r'[^0-9a-fA-F]', '', mac)

    # Check if it's a truncated MAC address
    is_truncated = len(mac) < 12

    # Format with colons
    if len(mac) < 4:  # Too short to be even a truncated MAC
        logger.warning(f"MAC address too short after normalization: {mac}")
        return None, False

    # Format the MAC with colons, handling truncated MACs
    formatted_segments = []
    for i in range(0, len(mac), 2):
        if i + 1 < len(mac):
            formatted_segments.append(mac[i:i + 2].upper())
        elif i < len(mac):  # Handle odd number of characters
            formatted_segments.append((mac[i] + '0').upper())

    normalized = ':'.join(formatted_segments)
    logger.debug(f"Normalized MAC: {normalized}")
    return normalized, is_truncated


def get_oui(mac):
    if not mac:
        return None, None

    normalized_mac, is_truncated = normalize_mac(mac)
    if not normalized_mac:
        return None, None

    # Extract OUI (first 3 bytes / 6 characters or whatever we have for truncated MACs)
    mac_no_colons = re.sub(r'[^0-9A-F]', '', normalized_mac)
    logger.info(f":MAC no columns: {mac_no_colons}")

    oui = mac_no_colons[:6].upper()
    logger.info(f"Extracted OUI: {oui} from MAC: {normalized_mac}")
    print(f"Extracted OUI: {oui} from MAC: {normalized_mac}")

    # If the OUI is incomplete (for truncated MACs), pad it with zeroes for lookups
    if len(oui) < 6:
        padded_oui = oui.ljust(6, '0')
        logger.debug(f"Padded truncated OUI to: {padded_oui}")
    else:
        padded_oui = oui

    # 1. First try our CSV database with exact match
    csv_lookup_oui = oui.lower()
    if csv_lookup_oui in csv_oui_db:
        vendor = csv_oui_db[csv_lookup_oui]
        if is_truncated:
            vendor = f"{vendor} (based on partial MAC)"
        logger.info(f"Found vendor from CSV database: {vendor}")
        return vendor, "csv"

    # 3. Try macvendors.com API (only for non-truncated MACs)
    # Only attempt this if we have at least the first 6 characters (3 bytes)
    if len(mac_no_colons) >= 6:
        try:
            lookup_mac = normalized_mac.split(':')
            # For truncated MACs, use what we have
            lookup_mac = ':'.join(lookup_mac[:3]) if len(lookup_mac) >= 3 else normalized_mac

            url = f"https://api.macvendors.com/{quote(lookup_mac)}"
            logger.debug(f"Querying macvendors.com for {lookup_mac}")
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                vendor = response.text.strip()
                logger.info(f"Found vendor from macvendors.com: {vendor}")
                if is_truncated:
                    vendor = f"{vendor} (based on partial MAC)"
                return vendor, "macvendors"
            elif response.status_code != 404:  # 404 means not found, which is expected in some cases
                logger.warning(f"Failed to get OUI from macvendors.com API: {response.status_code}")
        except Exception as e:
            logger.warning(f"Error with macvendors.com lookup: {str(e)}")
    return None, None


def lookup_ouis(wifi_data):
    results = []

    for entry in wifi_data:
        bssid = entry.get('bssid')

        if bssid:
            vendor, source = get_oui(bssid)
            normalized_mac, is_truncated = normalize_mac(bssid)

            results.append({
                'ssid': entry.get('ssid', ''),
                'bssid': normalized_mac if normalized_mac else bssid,
                'vendor': vendor if vendor else "no match",
                'vendor_source': source,
                'flagged': vendor is None
            })
            logger.debug(f"Lookup result: {results}")
        else:
            logger.warning(f"Skipping entry with no BSSID: {entry}")

    return results
