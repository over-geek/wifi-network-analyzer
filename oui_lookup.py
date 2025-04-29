import re
import requests
import logging
from urllib.parse import quote

# Configure logging
logger = logging.getLogger(__name__)

def normalize_mac(mac):
    """
    Normalize a MAC address to a consistent format (uppercase with colons).
    
    Args:
        mac (str): MAC address in various formats
        
    Returns:
        str: Normalized MAC address
    """
    if not mac:
        return None
        
    # Remove non-hexadecimal characters
    mac = re.sub(r'[^0-9a-fA-F]', '', mac)
    
    # Make sure we have at least 12 hexadecimal characters or pad if necessary
    if len(mac) < 10:  # Too short to be a valid MAC
        logger.warning(f"MAC address too short after normalization: {mac}")
        return None
    elif len(mac) > 12:  # Trim if too long
        mac = mac[:12]
        logger.warning(f"MAC address too long, trimmed to: {mac}")
    elif len(mac) < 12:  # Pad with zeros if needed
        mac = mac.ljust(12, '0')
        logger.info(f"MAC address padded to 12 characters: {mac}")
    
    # Format with colons
    normalized = ':'.join(mac[i:i+2].upper() for i in range(0, 12, 2))
    return normalized

def get_oui(mac):
    """
    Get the OUI (manufacturer) information for a MAC address.
    
    Args:
        mac (str): Normalized MAC address
        
    Returns:
        str: Manufacturer name or None if not found
    """
    if not mac:
        return None
    
    # Extract OUI (first 3 bytes / 6 characters)
    oui = mac.replace(':', '')[:6].upper()
    
    # Try different API services in sequence until one works
    
    # 1. Try macvendors.com API first (no API key required)
    try:
        url = f"https://api.macvendors.com/{quote(mac[:8])}"
        logger.debug(f"Querying macvendors.com for {mac[:8]}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            vendor = response.text.strip()
            logger.info(f"Found vendor from macvendors.com: {vendor}")
            return vendor
        elif response.status_code != 404:  # 404 means not found, which is expected in some cases
            logger.warning(f"Failed to get OUI from macvendors.com API: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error with macvendors.com lookup: {str(e)}")
    
    # 2. Try macaddress.io API if available (needs API key)
    try:
        # Get API key from environment variable with fallback
        import os
        api_key = os.environ.get("MACADDRESS_IO_API_KEY", "")
        
        if api_key:
            logger.debug(f"Using macaddress.io API for {mac}")
            url = f"https://api.macaddress.io/v1?apiKey={api_key}&output=json&search={quote(mac)}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                vendor = data.get('vendorDetails', {}).get('companyName')
                if vendor:
                    logger.info(f"Found vendor from macaddress.io: {vendor}")
                    return vendor
            else:
                logger.warning(f"Failed to get OUI from macaddress.io API: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error with macaddress.io lookup: {str(e)}")
    
    # 3. Try a local lookup approach based on common OUI patterns
    # This is a simple approach that doesn't require external APIs
    common_ouis = {
        "000000": "Locally Administered",
        "000C29": "VMware",
        "000CE5": "Dell",
        "001122": "Cisco Systems",
        "0050C2": "IEEE Registration Authority",
        "00A0C6": "Qualcomm",
        "00D0C9": "NVIDIA",
        "001A11": "Google",
        "002272": "American Micro-Fuel Device Corp",
        "002637": "Samsung Electronics",
        "0050F2": "Microsoft",
        "001C42": "Parallels",
        "74C63B": "AzureWave Technology",
        "74D7CA": "Panasonic Automotive",
        "74D02B": "ASUSTek Computer",
        "748114": "Apple",
        "74DA38": "Edimax Technology",
        "24A074": "Apple",
        "647002": "TP-Link",
        "D8A3B1": "Juniper Networks",
        "FCFBFB": "Ubiquiti Networks",
        "F8E71E": "Ruckus Wireless",
        "2C6E85": "Intel Corporate"
    }
    
    clean_oui = oui.upper()
    if clean_oui in common_ouis:
        vendor = common_ouis[clean_oui]
        logger.info(f"Found vendor from local database: {vendor}")
        return vendor
        
    # 4. As a fallback for older systems, try IEEE's OUI lookup
    # Note: This is resource-intensive and may be slow
    try:
        logger.debug("Attempting IEEE OUI database lookup")
        url = f"http://standards-oui.ieee.org/oui/oui.txt"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            oui_text = response.text
            # Search for the OUI in the IEEE database
            search_pattern = oui[:2] + "-" + oui[2:4] + "-" + oui[4:6]
            
            for line in oui_text.splitlines():
                if search_pattern in line:
                    # Extract the company name (after the OUI)
                    parts = line.split('(hex)')
                    if len(parts) > 1:
                        vendor = parts[1].strip()
                        logger.info(f"Found vendor from IEEE database: {vendor}")
                        return vendor
        else:
            logger.warning(f"Failed to access IEEE OUI database: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error with IEEE database lookup: {str(e)}")
    
    logger.info(f"No vendor found for MAC: {mac}")
    return None

def lookup_ouis(wifi_data):
    """
    Look up OUIs for a list of WiFi networks.
    
    Args:
        wifi_data (list): List of dictionaries with 'ssid' and 'bssid' keys
        
    Returns:
        list: Original data with added 'vendor' field
    """
    results = []
    
    for entry in wifi_data:
        bssid = entry.get('bssid')
        normalized_bssid = normalize_mac(bssid) if bssid else None
        
        if normalized_bssid:
            vendor = get_oui(normalized_bssid)
            results.append({
                'ssid': entry.get('ssid', ''),
                'bssid': normalized_bssid,
                'vendor': vendor
            })
        else:
            logger.warning(f"Skipping invalid BSSID: {bssid}")
    
    return results
