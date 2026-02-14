"""Unit tests for logging_config module"""

import logging
from unittest.mock import MagicMock, patch


class TestSetupLogging:
    """Tests for setup_logging function"""

    def test_setup_logging_returns_logger(self):
        """setup_logging() should return a logging.Logger instance"""
        from budget_app.utils.logging_config import setup_logging

        with patch('budget_app.utils.logging_config.RotatingFileHandler'):
            logger = setup_logging()

        assert isinstance(logger, logging.Logger)

    def test_setup_logging_with_console_output(self):
        """setup_logging(console_output=True) should add a StreamHandler"""
        from budget_app.utils.logging_config import setup_logging

        with patch('budget_app.utils.logging_config.RotatingFileHandler'):
            logger = setup_logging(console_output=True)

        stream_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(stream_handlers) >= 1

    def test_setup_logging_file_handler_failure(self):
        """setup_logging() should still return a logger when file handler fails"""
        from budget_app.utils.logging_config import setup_logging

        with patch(
            'budget_app.utils.logging_config.RotatingFileHandler',
            side_effect=OSError("Permission denied"),
        ):
            logger = setup_logging()

        assert isinstance(logger, logging.Logger)


class TestConvenienceFunctions:
    """Tests for convenience logging functions"""

    def test_log_info(self):
        """log_info should call logger.info with the message"""
        from budget_app.utils.logging_config import log_info

        mock_logger = MagicMock()
        with patch('budget_app.utils.logging_config.get_logger', return_value=mock_logger):
            log_info("test")

        mock_logger.info.assert_called_once_with("test")

    def test_log_warning(self):
        """log_warning should call logger.warning with the message"""
        from budget_app.utils.logging_config import log_warning

        mock_logger = MagicMock()
        with patch('budget_app.utils.logging_config.get_logger', return_value=mock_logger):
            log_warning("test")

        mock_logger.warning.assert_called_once_with("test")

    def test_log_error(self):
        """log_error should call logger.error with the message"""
        from budget_app.utils.logging_config import log_error

        mock_logger = MagicMock()
        with patch('budget_app.utils.logging_config.get_logger', return_value=mock_logger):
            log_error("test")

        mock_logger.error.assert_called_once_with("test", exc_info=False)

    def test_log_debug(self):
        """log_debug should call logger.debug with the message"""
        from budget_app.utils.logging_config import log_debug

        mock_logger = MagicMock()
        with patch('budget_app.utils.logging_config.get_logger', return_value=mock_logger):
            log_debug("test")

        mock_logger.debug.assert_called_once_with("test")

    def test_log_operation_with_details(self):
        """log_operation with details should log 'operation: details'"""
        from budget_app.utils.logging_config import log_operation

        mock_logger = MagicMock()
        with patch('budget_app.utils.logging_config.get_logger', return_value=mock_logger):
            log_operation("Import", details="Excel")

        mock_logger.info.assert_called_once_with("Import: Excel")

    def test_log_operation_without_details(self):
        """log_operation without details should log just the operation"""
        from budget_app.utils.logging_config import log_operation

        mock_logger = MagicMock()
        with patch('budget_app.utils.logging_config.get_logger', return_value=mock_logger):
            log_operation("Refresh")

        mock_logger.info.assert_called_once_with("Refresh")


class TestLogException:
    """Tests for log_exception function"""

    def test_log_exception(self):
        """log_exception should call logger.exception with the message"""
        from budget_app.utils.logging_config import log_exception

        mock_logger = MagicMock()
        with patch('budget_app.utils.logging_config.get_logger', return_value=mock_logger):
            log_exception("error msg")

        mock_logger.exception.assert_called_once_with("error msg")


class TestGetLogger:
    """Tests for get_logger function"""

    def test_get_logger_with_name(self):
        """get_logger('database') should return a child logger"""
        from budget_app.utils.logging_config import get_logger

        with patch('budget_app.utils.logging_config.setup_logging'):
            logger = get_logger("database")

        assert logger.name == "budget_app.database"

    def test_get_logger_without_name(self):
        """get_logger() should return the base 'budget_app' logger"""
        from budget_app.utils.logging_config import get_logger

        with patch('budget_app.utils.logging_config.setup_logging'):
            logger = get_logger()

        assert logger.name == "budget_app"
