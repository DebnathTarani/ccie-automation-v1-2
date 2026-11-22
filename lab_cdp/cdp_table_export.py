import asyncio
import csv
from concurrent.futures import ThreadPoolExecutor
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
            hostname = conn.get_prompt().strip().split("#")[0]
            version_response = conn.send_command("show version")
            if version_response.failed:
                return f"Error executing command on {host}: {version_response.result}"
            parsed_version = version_response.textfsm_parse_output()
            hardware_model = parsed_version[0]["hardware"][0] if parsed_version and parsed_version[0].get("hardware") else "Unknown"

            response = conn.send_command("show cdp neighbors")
            if response.failed:
                return f"Error executing command on {host}: {response.result}"
            
            parsed_output = response.textfsm_parse_output()
            if not parsed_output:
                return f"No CDP neighbors found on {hostname} ({host})."
            
            for entry in parsed_output:
                temp = {
                    "hostname": hostname,
                    "local_platform": hardware_model,
                    "neighbor_name": entry.get("neighbor_name").split(".")[0].upper() if entry.get("neighbor_name") else "Unknown",
                    "local_interface": entry.get("local_interface"),
                    "neighbor_interface": entry.get("neighbor_interface"),
                    "neighbor_platform": entry.get("platform")
                }
                all_cdp_neighbors.append(temp)
            return f"Successfully retrieved CDP neighbors for {hostname} ({host})."
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

async def main(device_list):
    with ThreadPoolExecutor(max_workers=10) as executor:
        batch = []
        for device in device_list:
            host = device.get("IP Address")
            username = device.get("username", "cisco")
            password = device.get("password", "Cisco@1234")
            platform = device.get("platform", "cisco_iosxe")
            auth_secondary = device.get("auth_secondary", "cisco")

            if not all([host, username, password, platform]):
                print(f"Skipping device with incomplete information: {device}")
                continue

            batch.append((host, username, password, platform, auth_secondary))

        def process_device(args):
            host, username, password, platform, auth_secondary = args
            print(f"Retrieving CDP neighbors for {host}...")
            cdp_output = get_cdp_neighbors(host, username, password, platform, auth_secondary)
            print(f"CDP neighbors for {host}:\n{cdp_output}\n")

        # Submit all tasks and wait for completion
        executor.map(process_device, batch)

if __name__ == "__main__":
    all_cdp_neighbors = []
    device_list = read_csv_file("Lab_1_mgmt_ips.csv")
    print("Starting CDP neighbor retrieval...")
    asyncio.run(main(device_list))
    
    # After processing all devices, you can choose to export the collected CDP neighbor information to a CSV file or handle it as needed.
    with open("cdp_neighbors.csv", mode="w", newline="") as csvfile:
        fieldnames = ["hostname", "local_platform", "neighbor_name", "local_interface", "neighbor_interface", "neighbor_platform"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for neighbor in all_cdp_neighbors:
            writer.writerow(neighbor)