"""Modbus RTU over UDP client for the Sinilink SK200W.

The SK200W programmable power supply exposes a Modbus RTU slave over its
serial/UART interface.  When combined with a serial-to-WiFi bridge (or an
XY-WFPOW style module) it can be reached over the network.  This client speaks
Modbus **RTU** frames tunnelled inside **UDP** datagrams.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from time import monotonic
from typing import Any

from pymodbus.client import AsyncModbusUdpClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerType


class SinilinkModbusClient:
    """Thin async wrapper around pymodbus for RTU-over-UDP communication."""

    #: The device silently drops requests that arrive less than ~50 ms after the
    #: previous one, so keep a safety margin between two requests.
    MIN_FRAME_GAP = 0.1

    #: Extra wait after a failed request so that a late reply arrives while no
    #: request is pending (RTU over UDP has no transaction id to match on).
    DRAIN_TIME = 0.3

    def __init__(
        self,
        host: str,
        port: int,
        slave: int,
        timeout: float = 3,
        retries: int = 3,
    ) -> None:
        """Initialise the client."""
        self._slave = slave
        self._last_request: float | None = None
        self._client = AsyncModbusUdpClient(
            host=host,
            port=port,
            framer=FramerType.RTU,
            timeout=timeout,
            retries=retries,
        )

    async def _async_throttle(self) -> None:
        """Wait long enough since the previous request to be answered."""
        if self._last_request is not None:
            delay = self.MIN_FRAME_GAP - (monotonic() - self._last_request)
            if delay > 0:
                await asyncio.sleep(delay)
        self._last_request = monotonic()

    @property
    def connected(self) -> bool:
        """Return True when the underlying client is connected."""
        return bool(self._client.connected)

    async def async_connect(self) -> bool:
        """Open the connection to the device if it is not already open."""
        if self._client.connected:
            return True
        return bool(await self._client.connect())

    def close(self) -> None:
        """Close the connection to the device."""
        self._client.close()

    async def _async_ensure_connected(self) -> None:
        """Reconnect transparently before issuing a request.

        pymodbus raises ``ConnectionException`` when a request is sent while
        the transport is down, so make sure it is up first.  This also lets the
        integration recover automatically after a dropped connection.
        """
        if not self._client.connected:
            await self.async_connect()

    async def async_read_holding_registers(
        self, address: int, count: int
    ) -> list[int]:
        """Read ``count`` holding registers starting at ``address``."""
        await self._async_ensure_connected()
        await self._async_throttle()
        try:
            result = await self._client.read_holding_registers(
                address, count=count, slave=self._slave
            )
        except ModbusException:
            await asyncio.sleep(self.DRAIN_TIME)
            raise
        if result.isError():
            await asyncio.sleep(self.DRAIN_TIME)
            msg = f"Error reading holding registers at {address}: {result}"
            raise ModbusException(msg)
        return list(result.registers)

    async def async_write_register(self, address: int, value: int) -> None:
        """Write a single holding register."""
        await self._async_ensure_connected()
        await self._async_throttle()
        try:
            result = await self._client.write_register(
                address, value, slave=self._slave
            )
        except ModbusException:
            await asyncio.sleep(self.DRAIN_TIME)
            raise
        if result.isError():
            await asyncio.sleep(self.DRAIN_TIME)
            msg = f"Error writing register at {address}: {result}"
            raise ModbusException(msg)


# ---------------------------------------------------------------------------
# Local / standalone entry point
# ---------------------------------------------------------------------------
#
# The block below lets you talk to a device directly from a shell, without
# Home Assistant, for example:
#
#     python modbus_client.py 192.168.1.50
#     python modbus_client.py 192.168.1.50 --slave 1 --count 0 --interval 2
#
# ``--count 0`` keeps reading until you stop it with Ctrl+C.


@lru_cache(maxsize=1)
def _get_constants() -> Any:
    """Return the ``const`` module, importing it in any execution context."""
    try:
        from . import const
    except ImportError:  # Running this file directly (no package context).
        import importlib.util

        path = Path(__file__).with_name("const.py")
        spec = importlib.util.spec_from_file_location("sinilink_sk200w_const", path)
        if spec is None or spec.loader is None:  # pragma: no cover
            msg = f"Unable to load constants from {path}"
            raise ImportError(msg) from None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    else:
        return const


def _parse_registers(registers: list[int]) -> dict[str, Any]:
    """Parse a raw register block into a dictionary of scaled values."""
    const = _get_constants()
    if len(registers) < const.POLL_COUNT:
        msg = f"Expected {const.POLL_COUNT} registers, got {len(registers)}"
        raise ValueError(msg)

    def reg(address: int) -> int:
        return registers[address - const.POLL_START]

    def s16(value: int) -> int:
        return value - 0x10000 if value >= 0x8000 else value

    def u32(address: int) -> int:
        # 32-bit values are stored low word first.
        return reg(address) | (reg(address + 1) << 16)

    def temp(address: int) -> float | None:
        raw = s16(reg(address))
        if raw in const.TEMPERATURE_INVALID_SENTINELS:
            return None
        return raw * const.TEMPERATURE_SCALE

    regulation_mode = reg(const.REG_REGULATION_MODE)
    output_enable = reg(const.REG_OUTPUT_ENABLE)

    return {
        "voltage_set": reg(const.REG_VOLTAGE_SET) * const.VOLTAGE_SCALE,
        "current_set": reg(const.REG_CURRENT_SET) * const.CURRENT_SCALE,
        "voltage_out": reg(const.REG_VOLTAGE_OUT) * const.VOLTAGE_SCALE,
        "current_out": reg(const.REG_CURRENT_OUT) * const.CURRENT_SCALE,
        "power_out": reg(const.REG_POWER_OUT) * const.POWER_SCALE,
        "voltage_in": reg(const.REG_VOLTAGE_IN) * const.VOLTAGE_SCALE,
        "capacity": u32(const.REG_CAPACITY) * const.CAPACITY_SCALE,
        "energy": u32(const.REG_ENERGY) * const.CAPACITY_SCALE,
        "on_time": (
            f"{reg(const.REG_ON_HOURS):02d}:"
            f"{reg(const.REG_ON_MINUTES):02d}:"
            f"{reg(const.REG_ON_SECONDS):02d}"
        ),
        "temperature": temp(const.REG_TEMPERATURE),
        "temperature_external": temp(const.REG_TEMPERATURE_EXTERNAL),
        "protection": reg(const.REG_PROTECTION),
        "regulation_mode": regulation_mode,
        "output_enable": output_enable,
        "output_on": bool(output_enable & const.MASK_OUTPUT_ENABLE),
        "constant_current": bool(regulation_mode & const.MASK_CONSTANT_CURRENT),
    }


def _format_temperature(value: float | None) -> str:
    """Format a temperature value, or note that no probe is connected."""
    if value is None:
        return "n/a (no sensor)"
    return f"{value:.1f} °C"


def _format_values(values: dict[str, Any], registers: list[int], raw: bool) -> str:
    """Format the parsed values as a human readable block."""

    def row(label: str, text: str) -> str:
        return f"  {label:<16}: {text}"

    rows = [
        row("Output voltage", f"{values['voltage_out']:.2f} V"),
        row("Output current", f"{values['current_out']:.3f} A"),
        row("Output power", f"{values['power_out']:.2f} W"),
        row("Input voltage", f"{values['voltage_in']:.2f} V"),
        row("Voltage set", f"{values['voltage_set']:.2f} V"),
        row("Current set", f"{values['current_set']:.3f} A"),
        row("Temperature", _format_temperature(values["temperature"])),
        row(
            "Temperature ext",
            _format_temperature(values["temperature_external"]),
        ),
        row("Capacity", f"{values['capacity']:.3f} Ah"),
        row("Energy", f"{values['energy']:.3f} Wh"),
        row("On time", str(values["on_time"])),
        row("Output", "ON" if values["output_on"] else "OFF"),
        row(
            "Regulation",
            "CC (constant current)"
            if values["constant_current"]
            else "CV (constant voltage)",
        ),
        row("Protection", "FAULT" if values["protection"] else "OK"),
    ]

    if raw:
        rows.append(row("Raw registers", " ".join(f"{word:04X}" for word in registers)))

    return "\n".join(rows)


async def _read_loop(args: Any) -> None:
    """Connect and print readings until the requested count is reached."""
    import asyncio
    from datetime import datetime

    const = _get_constants()
    client = SinilinkModbusClient(
        host=args.host,
        port=args.port,
        slave=args.slave,
        timeout=args.timeout,
        retries=args.retries,
    )
    try:
        await client.async_connect()
        print(
            f"Reading from {args.host}:{args.port} (slave {args.slave}) "
            "via Modbus RTU over UDP"
        )
        count = 0
        while True:
            registers = await client.async_read_holding_registers(
                const.POLL_START, const.POLL_COUNT
            )
            values = _parse_registers(registers)
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
            print(_format_values(values, registers, args.raw))
            count += 1
            if args.count and count >= args.count:
                break
            await asyncio.sleep(args.interval)
    finally:
        client.close()


def _build_parser() -> Any:
    """Build the command line argument parser."""
    import argparse

    const = _get_constants()
    parser = argparse.ArgumentParser(
        prog="modbus_client.py",
        description=(
            "Read values from a Sinilink SK200W power supply over "
            "Modbus RTU over UDP."
        ),
    )
    parser.add_argument("host", help="device IP address or hostname")
    parser.add_argument(
        "-p", "--port", type=int, default=const.DEFAULT_PORT,
        help=f"UDP port (default: {const.DEFAULT_PORT})",
    )
    parser.add_argument(
        "-s", "--slave", type=int, default=const.DEFAULT_SLAVE,
        help=f"Modbus slave address (default: {const.DEFAULT_SLAVE})",
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=const.DEFAULT_TIMEOUT,
        help=f"response timeout in seconds (default: {const.DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "-r", "--retries", type=int, default=const.DEFAULT_RETRIES,
        help=f"number of retries (default: {const.DEFAULT_RETRIES})",
    )
    parser.add_argument(
        "-n", "--count", type=int, default=1,
        help="number of readings; 0 = read until interrupted (default: 1)",
    )
    parser.add_argument(
        "-i", "--interval", type=float, default=2.0,
        help="seconds between readings (default: 2.0)",
    )
    parser.add_argument(
        "--raw", action="store_true",
        help="also print the raw register values",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    import asyncio
    import sys

    args = _build_parser().parse_args(argv)
    try:
        asyncio.run(_read_loop(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except (ModbusException, OSError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
