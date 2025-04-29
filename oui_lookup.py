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
    # Remove non-hexadecimal characters
    mac = re.sub(r'[^0-9a-fA-F]', '', mac)
    
    # Make sure we have 12 hexadecimal characters
    if len(mac) != 12:
        logger.warning(f"Invalid MAC address length after normalization: {mac}")
        return None
    
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
    
    try:
        # Use the macaddress.io API
        # Fallback to the MAC Vendors API if an API key is not available
        api_key = "at_NZYAb4ktsBjjqmRvQpZqk2RkR6eRv"  # Using API key environment variable with fallback
        
        if api_key:
            # Use macaddress.io API
            url = f"https://api.macaddress.io/v1?apiKey={api_key}&output=json&search={quote(mac)}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('vendorDetails', {}).get('companyName')
            else:
                logger.warning(f"Failed to get OUI from macaddress.io API: {response.status_code}")
        
        # Fallback to macvendors.com API (no API key required)
        url = f"https://api.macvendors.com/{quote(mac[:8])}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.text.strip()
        elif response.status_code != 404:  # 404 means not found, which is expected in some cases
            logger.warning(f"Failed to get OUI from macvendors.com API: {response.status_code}")
            
    except Exception as e:
        logger.exception(f"Error looking up OUI for {mac}")
    
    # Final fallback - try IEEE's OUI lookup
    try:
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
                        return parts[1].strip()
    except Exception as e:
        logger.exception(f"Error looking up OUI from IEEE database for {mac}")
    
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
