# server.py
import uuid
from typing import Dict
from fastmcp import FastMCP

from ccie_automation_v1_2.connection import ScrapliDeviceSession, SupportedPlatform

mcp = FastMCP("network-device-manager")

ACTIVE_SESSIONS: Dict[str, ScrapliDeviceSession] = {}


@mcp.tool()
async def connect_device(
    host: str,
    username: str,
    password: str,
    platform: SupportedPlatform,
    port: int = 22,
) -> str:
    """Open an SSH connection to a network device and return a session ID.

    Args:
        host: IP address or hostname.
        username: SSH username.
        password: SSH password.
        platform: Network OS platform. Allowed values: 'cisco_iosxe', 'arista_eos'.
        port: SSH port (default: 22).
    """
    session_id = str(uuid.uuid4())
    session = ScrapliDeviceSession(
        host=host,
        username=username,
        password=password,
        platform=platform,
        port=port,
    )

    try:
        await session.open()
        ACTIVE_SESSIONS[session_id] = session
        return f"Successfully connected to {host} ({platform.value}). Session ID: {session_id}"
    except Exception as e:
        return f"Connection failed to {host}: {str(e)}"


@mcp.tool()
async def execute_command(session_id: str, command: str) -> str:
    """Run an operational/show command on an active session.

    Args:
        session_id: The UUID returned by connect_device.
        command: The CLI command to run (e.g., 'show ip interface brief').
    """
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        return f"Error: No active session with ID '{session_id}'. Please connect first."

    try:
        output = await session.send_command(command)
        return output if output.strip() else "[Command executed with empty output]"
    except Exception as e:
        return f"Execution error on {session.host}: {str(e)}"


@mcp.tool()
async def execute_config_command(session_id: str, commands: list[str]) -> str:
    """Run a configuration command on an active session.
       Don't use this for reload or reboot commands, as it will break the session.

    Args:
        session_id: The UUID returned by connect_device.
        commands: A list of CLI commands to run.
    """
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        return f"Error: No active session with ID '{session_id}'. Please connect first."

    try:
        output = await session.send_config_command(commands)
        return output if output.strip() else "[Command executed with empty output]"
    except Exception as e:
        return f"Execution error on {session.host}: {str(e)}"


@mcp.tool()
async def execute_save_config(session_id: str) -> str:
    """Save the running configuration to startup configuration.

    Args:
        session_id: The UUID returned by connect_device.
    """
    session = ACTIVE_SESSIONS.get(session_id)
    if not session:
        return f"Error: No active session with ID '{session_id}'. Please connect first."

    try:
        output = await session.save_config()
        return output if output.strip() else "[Command executed with empty output]"
    except Exception as e:
        return f"Execution error on {session.host}: {str(e)}"


@mcp.tool()
async def execute_reboot(session_id: str) -> str:
    """Reboot a network device and clean up the active session.

    Args:
        session_id: The UUID returned by connect_device.
    """
    session = ACTIVE_SESSIONS.pop(session_id, None)
    if not session:
        return f"Error: No active session with ID '{session_id}'."

    try:
        return await session.reboot()
    except Exception as e:
        return f"Failed to reboot {session.host}: {str(e)}"

@mcp.tool()
async def disconnect_device(session_id: str) -> str:
    """Close an active SSH session and release network device VTY lines.

    Args:
        session_id: The UUID returned by connect_device.
    """
    session = ACTIVE_SESSIONS.pop(session_id, None)
    if not session:
        return f"No active session with ID '{session_id}' found."

    await session.close()
    return f"Closed connection {session_id} to {session.host}."


if __name__ == "__main__":
    # fastmcp defaults to stdio transport when run
    mcp.run(transport="http", port=8888, host="0.0.0.0")