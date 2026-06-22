"""Tests for PowerShell connector."""
import pytest

from ADAM.connections.powershell import PowerShellConnector, PowerShellError


def test_execute_simple():
    connector = PowerShellConnector()
    result = connector.execute("Get-Process | Select-Object -First 1 Name")
    assert result["exit_code"] == 0
    assert "Name" in result["stdout"]


def test_execute_blocked():
    connector = PowerShellConnector()
    with pytest.raises(PowerShellError):
        connector.execute("Read-Host 'prompt'")
