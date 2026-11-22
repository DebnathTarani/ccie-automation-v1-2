import asyncio
from enum import Enum
from scrapli import AsyncScrapli
from scrapli.exceptions import ScrapliException


class SupportedPlatform(str, Enum):
    CISCO_IOSXE = "cisco_iosxe"
    ARISTA_EOS = "arista_eos"


class ScrapliDeviceSession:
    """Manages an individual SSH session to a network device using AsyncScrapli."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        platform: SupportedPlatform,
        port: int = 22,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.platform = platform
        self.port = port
        self._conn: AsyncScrapli | None = None

    async def open(self) -> None:
        """Establish the async SSH connection."""
        self._conn = AsyncScrapli(
            host=self.host,
            port=self.port,
            auth_username=self.username,
            auth_password=self.password,
            platform=self.platform.value,
            auth_strict_key=False,
            transport="asyncssh",
        )
        await self._conn.open()

    async def send_command(self, command: str) -> str:
        """Execute a show/exec command and return output."""
        if not self._conn or not self._conn.isalive():
            raise RuntimeError(f"Connection to {self.host} is inactive or closed.")

        response = await self._conn.send_command(command)
        if response.failed:
            raise ScrapliException(f"Command '{command}' failed on {self.host}.")

        return response.result
    
    async def send_config_command(self, commands: list[str]) -> str:
        """Execute configuration commands and return output."""
        if not self._conn or not self._conn.isalive():
            raise RuntimeError(f"Connection to {self.host} is inactive or closed.")

        response = await self._conn.send_configs(commands)
        if response.failed:
            raise ScrapliException(f"Configuration commands failed on {self.host}.")

        # MultiResponse is iterable; collect each command's output
        return "\n".join(r.result for r in response)

    async def save_config(self) -> str:
        """Save running configuration to startup configuration."""
        if not self._conn or not self._conn.isalive():
            raise RuntimeError(f"Connection to {self.host} is inactive or closed.")

        # Ensure we are in enable/privilege_exec mode
        await self._conn.acquire_priv("privilege_exec")

        if self.platform == SupportedPlatform.CISCO_IOSXE:
            command = "write memory"
        elif self.platform == SupportedPlatform.ARISTA_EOS:
            command = "copy running-config startup-config"
        else:
            raise ValueError(f"Unsupported platform: {self.platform}")

        response = await self._conn.send_command(command)
        if response.failed:
            raise ScrapliException(f"Command '{command}' failed on {self.host}.")

        return response.result
    
    async def reboot(self) -> str:
        """Reboot the device cleanly handling confirmation prompts and connection drop."""
        if not self._conn or not self._conn.isalive():
            raise RuntimeError(f"Connection to {self.host} is inactive or closed.")

        # 1. Save config first so device won't prompt with 'Save? [yes/no]'
        try:
            await self._conn.send_command("write memory")
        except Exception:
            pass

        # 2. Interactive events: send 'reload', wait for 'confirm', press enter
        interact_events = [
            ("reload", r"confirm"),
            ("\n", r"")
        ]

        try:
            await self._conn.send_interactive(
                interact_events=interact_events,
                timeout_ops=8,
            )
        except (ScrapliException, asyncio.TimeoutError, Exception):
            # Dropping connection / timing out while rebooting is normal expected behavior
            pass
        finally:
            await self.close()

        return f"Reload command sent successfully to {self.host}."

    async def close(self) -> None:
        """Gracefully terminate connection to release device VTY lines."""
        if self._conn and self._conn.isalive():
            await self._conn.close()

    @property
    def is_alive(self) -> bool:
        return self._conn is not None and self._conn.isalive()