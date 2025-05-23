import re
import logging

# Configure logging
logger = logging.getLogger(__name__)

def parse_wifi_data(text):
    results = []
    
    # Regular expressions for different potential formats
    # Pattern for "SSID: [name], BSSID: [mac]" format
    pattern1 = r'SSID\s*:?\s*["\']?([^,"\']+)["\']?\s*,?\s*BSSID\s*:?\s*([0-9A-Fa-f:.-]+)'
    
    # Pattern for "[mac] - [ssid]" format
    pattern2 = r'([0-9A-Fa-f:.-]{10,17})\s*-?\s*([^\n\r,]+)'
    
    # Pattern for "[ssid] [mac]" format - More lenient with MAC address format
    pattern3 = r'([^\n\r,]{1,32})\s+([0-9A-Fa-f:.-]{10,17})'
    
    # Pattern for WiFi surveyor app format: [True/False] [SSID] [MAC] [other data]
    pattern4 = r'(True|False)\s+([^\t]+)\s+([0-9A-Fa-f:.-]{10,17})'

    # Pattern for standalone MAC address (including truncated ones)
    pattern5 = r'^([0-9A-Fa-f]{2}[:-]){1,5}([0-9A-Fa-f]{1,2})$'
    
    # MAC address pattern for extracting from messy text - more lenient
    mac_pattern = r'([0-9A-Fa-f]{2}[:-]){4,5}([0-9A-Fa-f]{1,2})|([0-9A-Fa-f]{10,12})'
    
    # Strategy 1: Line by line with specific patterns
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try standalone MAC address format (including truncated)
        match = re.match(pattern5, line.strip())
        if match:
            # If it's just a MAC address with no SSID, use "Unknown" as SSID
            results.append({'ssid': 'Unknown SSID', 'bssid': line.strip()})
            continue
        
        # Try WiFi surveyor app format first
        match = re.search(pattern4, line)
        if match:
            _, ssid, bssid = match.groups()  # Ignore the True/False flag
            results.append({'ssid': ssid.strip(), 'bssid': bssid.strip()})
            continue
            
        # Try pattern 1
        match = re.search(pattern1, line)
        if match:
            ssid, bssid = match.groups()
            results.append({'ssid': ssid.strip(), 'bssid': bssid.strip()})
            continue
            
        # Try pattern 3 (SSID MAC format) - Try this before pattern 2
        match = re.search(pattern3, line)
        if match:
            ssid, bssid = match.groups()
            # Clean up 'True' or 'False' prefixes that might be part of the SSID
            ssid = re.sub(r'^(True|False)\s+', '', ssid.strip())
            results.append({'ssid': ssid.strip(), 'bssid': bssid.strip()})
            continue
            
        # Try pattern 2 (MAC - SSID format)
        match = re.search(pattern2, line)
        if match:
            bssid, ssid = match.groups()
            results.append({'ssid': ssid.strip(), 'bssid': bssid.strip()})
            continue
        
        # If the line contains tab-separated values (like from wifi surveyor or CSV exports)
        if '\t' in line:
            parts = line.split('\t')
            mac_address = None
            ssid = None
            
            # Look for MAC address in each part
            for i, part in enumerate(parts):
                # Check if this part contains a MAC address
                mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){4,5}[0-9A-Fa-f]{1,2}|[0-9A-Fa-f]{10,12}', part)
                if mac_match:
                    mac_address = mac_match.group(0)
                    # If MAC found, look for SSID - usually column 2 in wifi surveyor format
                    if i >= 1 and len(parts) > 1:
                        ssid = parts[1].strip()
                    break
            
            if mac_address and ssid:
                # Remove any "True" or "False" prefix if present
                ssid = re.sub(r'^(True|False)\s+', '', ssid)
                results.append({'ssid': ssid, 'bssid': mac_address})
                continue
        
        # If none of the patterns match but line contains what looks like a MAC address
        mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){4,5}[0-9A-Fa-f]{1,2}|[0-9A-Fa-f]{10,12}', line)
        if mac_match:
            bssid = mac_match.group(0)
            # Get the rest of the line as SSID
            before_mac = line[:mac_match.start()].strip()
            after_mac = line[mac_match.end():].strip()
            
            # If MAC is at the beginning, use text after it as SSID
            if before_mac == "":
                ssid = after_mac if after_mac else "Unknown SSID"
            else:
                # Otherwise, use text before MAC as SSID
                ssid = before_mac
                # Clean up 'True' or 'False' prefixes
                ssid = re.sub(r'^(True|False)\s+', '', ssid)
                
            results.append({'ssid': ssid, 'bssid': bssid})
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
                words_before = re.sub(r'^(True|False)\s+', '', words_before)
                ssid = words_before.strip() if words_before else "Unknown SSID"
            
            results.append({'ssid': ssid, 'bssid': bssid})
    
    return results
