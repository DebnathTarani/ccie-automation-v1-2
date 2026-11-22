from scrapli import Scrapli

def get_cdp_neighbors(host: str, username: str, password: str, platform: str, auth_secondary: str = None) -> str:
    """Retrieve CDP neighbor information from a network device.

    Args:
        host: The IP address or hostname of the device.
        username: The SSH username.
        password: The SSH password.
        platform: The platform type (e.g., 'cisco_iosxe', 'arista_eos').
        auth_secondary: The secondary authentication password.
    Returns:
        A string containing the CDP neighbor information or an error message.
    """
    try:
        with Scrapli(
            host=host,
            auth_username=username,
            auth_password=password,
            auth_secondary=auth_secondary,
            platform=platform,
            transport="ssh2",
            auth_strict_key=False,
        ) as conn:
            response = conn.send_command("show ip interface brief")
            if response.failed:
                return f"Error executing command on {host}: {response.result}"
            
            parsed_output = response.textfsm_parse_output()
            for entry in parsed_output:
                if not entry.get("ip_address").startswith("192.168.29."):
                    continue  # Skip interfaces that don't match the specified IP range
                send_commands = [
                    f"interface {entry.get('interface')}",
                    "description CDP Disabled by Lab Script",
                    "no cdp enable"
                ]
                response = conn.send_configs(send_commands)
                if response.failed:
                    return f"Error executing command on {host}: {response.result}"
                
                # save the configuration after disabling CDP
                response = conn.send_command("write memory")
                if response.failed:
                    return f"Error saving configuration on {host}: {response.result}"
            return f"Successfully disabled CDP on {host}."
    except Exception as e:
        return f"Connection failed to {host}: {str(e)}"

def read_csv_file(file_path: str) -> list[dict[str, str]]:
    """Read a CSV file and return a list of dictionaries.

    Args:
        file_path: The path to the CSV file.
    Returns:
        A list of dictionaries where each dictionary represents a row in the CSV file.
    """
    import csv

    data = []
    try:
        with open(file_path, mode='r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                data.append(row)
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {str(e)}")
    return data

if __name__ == "__main__":
    device_list = read_csv_file("Lab_1_mgmt_ips.csv")
    print("Starting CDP neighbor retrieval...")
    for device in device_list:
        host = device.get("IP Address")
        username = device.get("username", "cisco")
        password = device.get("password", "Cisco@1234")
        platform = device.get("platform", "cisco_iosxe")
        auth_secondary = device.get("auth_secondary", "cisco")

        if not all([host, username, password, platform]):
            print(f"Skipping device with incomplete information: {device}")
            continue

        print(f"Retrieving CDP neighbors for {host}...")
        cdp_output = get_cdp_neighbors(host, username, password, platform, auth_secondary)
        print(f"CDP neighbors for {host}:\n{cdp_output}\n")