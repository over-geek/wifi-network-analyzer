import re
import logging

# Configure logging
logger = logging.getLogger(__name__)

def parse_wifi_data(text):
    """
    Parse WiFi data from a text string containing SSID/BSSID pairs.
    
    Args:
        text (str): Text containing SSID and BSSID information
        
    Returns:
        list: List of dictionaries with 'ssid' and 'bssid' keys
    """
    results = []
    
    # Regular expressions for different potential formats
    # Pattern for "SSID: [name], BSSID: [mac]" format
    pattern1 = r'SSID\s*:?\s*["\']?([^,"\']+)["\']?\s*,?\s*BSSID\s*:?\s*([0-9A-Fa-f:.-]+)'
    
    # Pattern for "[mac] - [ssid]" format
    pattern2 = r'([0-9A-Fa-f:.-]{12,17})\s*-?\s*([^\n\r,]+)'
    
    # Pattern for "[ssid] [mac]" format
    pattern3 = r'([^\n\r,]{1,32})\s+([0-9A-Fa-f:.-]{12,17})'
    
    # MAC address pattern for extracting from messy text
    mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})|([0-9A-Fa-f]{12})'
    
    # Try multiple parsing strategies
    
    # Strategy 1: Line by line with specific patterns
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try pattern 1
        match = re.search(pattern1, line)
        if match:
            ssid, bssid = match.groups()
            results.append({'ssid': ssid.strip(), 'bssid': bssid.strip()})
            continue
            
        # Try pattern 2
        match = re.search(pattern2, line)
        if match:
            bssid, ssid = match.groups()
            results.append({'ssid': ssid.strip(), 'bssid': bssid.strip()})
            continue
            
        # Try pattern 3
        match = re.search(pattern3, line)
        if match:
            ssid, bssid = match.groups()
            results.append({'ssid': ssid.strip(), 'bssid': bssid.strip()})
            continue
            
    # If no results from patterns, try to extract MAC addresses and pair with nearby text
    if not results:
        # Find all MAC addresses in the text
        mac_matches = re.finditer(mac_pattern, text)
        
        for match in mac_matches:
            bssid = match.group(0)
            
            # Get text before and after the MAC to try to extract SSID
            start_pos = max(0, match.start() - 50)
            end_pos = min(len(text), match.end() + 50)
            
            context = text[start_pos:end_pos]
            
            # Try to find SSID in context
            # Look for common patterns like "SSID: name" or just words near the MAC
            ssid_match = re.search(r'SSID\s*:?\s*["\']?([^,"\']+)["\']?', context)
            
            if ssid_match:
                ssid = ssid_match.group(1).strip()
            else:
                # Just use some text near the MAC as the SSID
                words_before = ' '.join(context[:match.start()-start_pos].split()[-3:])
                ssid = words_before.strip() if words_before else "Unknown SSID"
            
            results.append({'ssid': ssid, 'bssid': bssid})
    
    # Log the results
    logger.debug(f"Parsed {len(results)} WiFi networks from input text")
    
    return results
