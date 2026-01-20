"""
Tests for YORI CLI entry point
"""
import pytest
from unittest.mock import patch, Mock
import sys
from pathlib import Path

from yori.main import main
from yori.config import YoriConfig


class TestMainCLI:
    """Test CLI entry point"""

    @patch('yori.main.uvicorn.run')
    @patch('yori.main.YoriConfig.from_default_locations')
    def test_main_default_config(self, mock_config_loader, mock_uvicorn):
        """Test main with default config"""
        mock_config_loader.return_value = YoriConfig(
            mode="observe",
            listen="127.0.0.1:8443",
        )

        with patch.object(sys, 'argv', ['yori']):
            main()

        assert mock_uvicorn.called
        call_kwargs = mock_uvicorn.call_args[1]
        assert call_kwargs['host'] == '127.0.0.1'
        assert call_kwargs['port'] == 8443

    @patch('yori.main.uvicorn.run')
    @patch('yori.main.YoriConfig.from_yaml')
    def test_main_with_config_file(self, mock_yaml, mock_uvicorn):
        """Test loading config from file"""
        mock_yaml.return_value = YoriConfig(mode="enforce", listen="0.0.0.0:9000")

        with patch.object(sys, 'argv', ['yori', '--config', '/tmp/yori.conf']):
            main()

        mock_yaml.assert_called_once()
        assert mock_uvicorn.called

    @patch('yori.main.uvicorn.run')
    @patch('yori.main.YoriConfig.from_default_locations')
    def test_main_host_override(self, mock_config, mock_uvicorn):
        """Test --host override"""
        mock_config.return_value = YoriConfig(mode="observe", listen="127.0.0.1:8443")

        with patch.object(sys, 'argv', ['yori', '--host', '0.0.0.0']):
            main()

        call_kwargs = mock_uvicorn.call_args[1]
        assert call_kwargs['host'] == '0.0.0.0'
        assert call_kwargs['port'] == 8443

    @patch('yori.main.uvicorn.run')
    @patch('yori.main.YoriConfig.from_default_locations')
    def test_main_port_override(self, mock_config, mock_uvicorn):
        """Test --port override"""
        mock_config.return_value = YoriConfig(mode="observe", listen="127.0.0.1:8443")

        with patch.object(sys, 'argv', ['yori', '--port', '9999']):
            main()

        call_kwargs = mock_uvicorn.call_args[1]
        assert call_kwargs['port'] == 9999

    @patch('yori.main.uvicorn.run')
    @patch('yori.main.YoriConfig.from_default_locations')
    def test_main_creates_proxy(self, mock_config, mock_uvicorn):
        """Test that main creates ProxyServer"""
        mock_config.return_value = YoriConfig(mode="observe", listen="127.0.0.1:8443")

        with patch.object(sys, 'argv', ['yori']):
            main()

        # Verify proxy app was passed to uvicorn
        assert mock_uvicorn.called
        app = mock_uvicorn.call_args[0][0]
        assert app is not None
        assert hasattr(app, 'title')

    @patch('yori.main.uvicorn.run')
    @patch('yori.main.YoriConfig.from_default_locations')
    def test_main_enables_logging(self, mock_config, mock_uvicorn):
        """Test uvicorn logging configuration"""
        mock_config.return_value = YoriConfig(mode="observe", listen="127.0.0.1:8443")

        with patch.object(sys, 'argv', ['yori']):
            main()

        call_kwargs = mock_uvicorn.call_args[1]
        assert call_kwargs['log_level'] == 'info'
        assert call_kwargs['access_log'] == True


class TestMainModule:
    """Test main module attributes"""

    def test_logger_exists(self):
        """Test logger is configured"""
        from yori.main import logger
        assert logger is not None
        assert logger.name == 'yori.main'
