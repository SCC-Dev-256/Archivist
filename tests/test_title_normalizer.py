# PURPOSE: Unit tests for Title Normalizer CLI Tool
# DEPENDENCIES: pytest, unittest.mock, datetime, re
# MODIFICATION NOTES: v1.0 - Initial test suite covering all normalization logic

"""
Unit tests for the Title Normalizer CLI Tool.

Tests cover:
- Title normalization logic
- Date pattern extraction
- API interaction mocking
- CLI argument parsing
- CSV export functionality
"""

import pytest
import re
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the classes to test
from core.chronologic_order import TitleNormalizer, CablecastTitleManager


class TestTitleNormalizer:
    """Test cases for TitleNormalizer class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.normalizer = TitleNormalizer()
    
    def test_extract_date_from_title_valid_patterns(self):
        """Test extracting dates from valid title patterns."""
        test_cases = [
            ("Grant City Council (6/3/25)", (6, 3, 2025)),
            ("Board Meeting (12/25/24)", (12, 25, 2024)),
            ("Special Event (1/1/30)", (1, 1, 1930)),  # Year < 30 becomes 19xx
            ("Meeting (3/15/29)", (3, 15, 2029)),      # Year >= 30 becomes 20xx
        ]
        
        for title, expected in test_cases:
            result = self.normalizer.extract_date_from_title(title)
            assert result == expected, f"Failed for title: {title}"
    
    def test_extract_date_from_title_invalid_patterns(self):
        """Test extracting dates from invalid title patterns."""
        invalid_titles = [
            "Grant City Council",  # No date pattern
            "Meeting (13/1/25)",   # Invalid month
            "Event (12/32/25)",    # Invalid day
            "Show (12/15)",        # Missing year
            "Title (12/15/25/extra)",  # Extra components
            "Meeting (a/b/25)",    # Non-numeric
        ]
        
        for title in invalid_titles:
            result = self.normalizer.extract_date_from_title(title)
            assert result is None, f"Should return None for: {title}"
    
    def test_is_already_normalized(self):
        """Test detection of already normalized titles."""
        normalized_titles = [
            "2025-06-03 - Grant City Council",
            "2024-12-25 - Board Meeting",
            "1930-01-01 - Special Event",
        ]
        
        non_normalized_titles = [
            "Grant City Council (6/3/25)",
            "Board Meeting",
            "2025-06-03 Grant City Council",  # Missing dash
            "2025/06/03 - Grant City Council",  # Wrong date format
        ]
        
        for title in normalized_titles:
            assert self.normalizer.is_already_normalized(title), f"Should be normalized: {title}"
        
        for title in non_normalized_titles:
            assert not self.normalizer.is_already_normalized(title), f"Should not be normalized: {title}"
    
    def test_normalize_title_success(self):
        """Test successful title normalization."""
        test_cases = [
            ("Grant City Council (6/3/25)", "2025-06-03 - Grant City Council"),
            ("Board Meeting (12/25/24)", "2024-12-25 - Board Meeting"),
            ("Special Event (1/1/30)", "1930-01-01 - Special Event"),
            ("Meeting with extra spaces (3/15/29)", "2029-03-15 - Meeting with extra spaces"),
        ]
        
        for original, expected in test_cases:
            result = self.normalizer.normalize_title(original)
            assert result == expected, f"Failed for: {original}"
    
    def test_normalize_title_already_normalized(self):
        """Test normalization of already normalized titles."""
        already_normalized = [
            "2025-06-03 - Grant City Council",
            "2024-12-25 - Board Meeting",
        ]
        
        for title in already_normalized:
            result = self.normalizer.normalize_title(title)
            assert result is None, f"Should return None for already normalized: {title}"
    
    def test_normalize_title_no_date_pattern(self):
        """Test normalization of titles without date patterns."""
        no_date_titles = [
            "Grant City Council",
            "Board Meeting",
            "Special Event",
            "Meeting (no date here)",
        ]
        
        for title in no_date_titles:
            result = self.normalizer.normalize_title(title)
            assert result is None, f"Should return None for: {title}"


class TestCablecastTitleManager:
    """Test cases for CablecastTitleManager class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        with patch('core.chronologic_order.requests.Session') as mock_session:
            self.mock_session = mock_session.return_value
            self.manager = CablecastTitleManager("test_token", "https://test.cablecast.com")
    
    def test_setup_session(self):
        """Test session setup with authentication."""
        expected_headers = {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        self.mock_session.headers.update.assert_called_with(expected_headers)
    
    def test_test_connection_success(self):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        self.mock_session.get.return_value = mock_response
        
        result = self.manager.test_connection()
        
        assert result is True
        self.mock_session.get.assert_called_once()
    
    def test_test_connection_failure(self):
        """Test failed connection test."""
        mock_response = Mock()
        mock_response.status_code = 401
        self.mock_session.get.return_value = mock_response
        
        result = self.manager.test_connection()
        
        assert result is False
    
    def test_get_all_shows_single_page(self):
        """Test fetching shows with single page response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'shows': [
                {'id': 1, 'title': 'Show 1'},
                {'id': 2, 'title': 'Show 2'},
            ]
        }
        self.mock_session.get.return_value = mock_response
        
        shows = self.manager.get_all_shows()
        
        assert len(shows) == 2
        assert shows[0]['id'] == 1
        assert shows[1]['id'] == 2
    
    def test_get_all_shows_multiple_pages(self):
        """Test fetching shows with multiple pages."""
        # First page
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            'shows': [{'id': i, 'title': f'Show {i}'} for i in range(1, 101)]
        }
        
        # Second page (final)
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            'shows': [{'id': i, 'title': f'Show {i}'} for i in range(101, 150)]
        }
        
        self.mock_session.get.side_effect = [mock_response1, mock_response2]
        
        shows = self.manager.get_all_shows()
        
        assert len(shows) == 149
        assert self.mock_session.get.call_count == 2
    
    def test_get_all_shows_with_project_id(self):
        """Test fetching shows with project ID filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'shows': []}
        self.mock_session.get.return_value = mock_response
        
        self.manager.get_all_shows(project_id=123)
        
        # Check that project_id was included in params
        call_args = self.mock_session.get.call_args
        assert 'project_id' in call_args[1]['params']
        assert call_args[1]['params']['project_id'] == 123
    
    def test_update_show_title_success(self):
        """Test successful show title update."""
        mock_response = Mock()
        mock_response.status_code = 200
        self.mock_session.put.return_value = mock_response
        
        result = self.manager.update_show_title(123, "New Title")
        
        assert result is True
        self.mock_session.put.assert_called_once_with(
            "https://test.cablecast.com/cablecastapi/v1/shows/123",
            json={"title": "New Title"}
        )
    
    def test_update_show_title_failure(self):
        """Test failed show title update."""
        mock_response = Mock()
        mock_response.status_code = 404
        self.mock_session.put.return_value = mock_response
        
        result = self.manager.update_show_title(123, "New Title")
        
        assert result is False
    
    def test_process_shows_dry_run(self):
        """Test processing shows in dry-run mode."""
        shows = [
            {'id': 1, 'title': 'Grant City Council (6/3/25)'},
            {'id': 2, 'title': 'Board Meeting (12/25/24)'},
            {'id': 3, 'title': 'Already Normalized (2025-01-01 - Event)'},
            {'id': 4, 'title': 'No Date Pattern'},
        ]
        
        results = self.manager.process_shows(shows, dry_run=True)
        
        assert results['total_shows'] == 4
        assert results['processed'] == 2
        assert results['updated'] == 2
        assert results['skipped'] == 2
        assert results['errors'] == 0
        
        # Check details
        assert len(results['details']) == 4
        
        # Check that shows with date patterns were processed
        processed_shows = [d for d in results['details'] if d['action'] == 'would_update']
        assert len(processed_shows) == 2
    
    def test_process_shows_actual_update(self):
        """Test processing shows with actual updates."""
        with patch.object(self.manager, 'update_show_title', return_value=True):
            shows = [
                {'id': 1, 'title': 'Grant City Council (6/3/25)'},
                {'id': 2, 'title': 'Board Meeting (12/25/24)'},
            ]
            
            results = self.manager.process_shows(shows, dry_run=False)
            
            assert results['total_shows'] == 2
            assert results['processed'] == 2
            assert results['updated'] == 2
            assert results['skipped'] == 0
            assert results['errors'] == 0


class TestCLIFunctionality:
    """Test cases for CLI functionality."""
    
    def test_export_results_to_csv(self, tmp_path):
        """Test CSV export functionality."""
        from core.chronologic_order import export_results_to_csv
        
        results = {
            'details': [
                {
                    'show_id': 1,
                    'original_title': 'Grant City Council (6/3/25)',
                    'new_title': '2025-06-03 - Grant City Council',
                    'action': 'updated',
                    'reason': 'success'
                },
                {
                    'show_id': 2,
                    'original_title': 'Board Meeting',
                    'new_title': None,
                    'action': 'skipped',
                    'reason': 'No date pattern'
                }
            ]
        }
        
        csv_file = tmp_path / "test_results.csv"
        export_results_to_csv(results, str(csv_file))
        
        assert csv_file.exists()
        
        # Read and verify CSV content
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'show_id,original_title,new_title,action,reason' in content
            assert 'Grant City Council (6/3/25)' in content
            assert '2025-06-03 - Grant City Council' in content


class TestIntegration:
    """Integration tests for the complete workflow."""
    
    def test_complete_normalization_workflow(self):
        """Test complete normalization workflow."""
        normalizer = TitleNormalizer()
        
        # Test various title formats
        test_cases = [
            # Input title, expected normalized title, should be processed
            ("Grant City Council (6/3/25)", "2025-06-03 - Grant City Council", True),
            ("Board Meeting (12/25/24)", "2024-12-25 - Board Meeting", True),
            ("2025-06-03 - Already Normalized", None, False),  # Already normalized
            ("No Date Pattern", None, False),  # No date pattern
            ("Meeting (13/1/25)", None, False),  # Invalid date
        ]
        
        for input_title, expected_normalized, should_process in test_cases:
            normalized = normalizer.normalize_title(input_title)
            
            if should_process:
                assert normalized == expected_normalized, f"Failed for: {input_title}"
            else:
                assert normalized is None, f"Should not process: {input_title}"
    
    def test_date_pattern_edge_cases(self):
        """Test edge cases in date pattern matching."""
        normalizer = TitleNormalizer()
        
        edge_cases = [
            ("Meeting (1/1/00)", "2000-01-01 - Meeting"),  # Year 00
            ("Event (12/31/99)", "1999-12-31 - Event"),    # Year 99
            ("Show (2/29/24)", "2024-02-29 - Show"),       # Leap year
            ("Meeting (3/15/29)", "2029-03-15 - Meeting"), # Year boundary
            ("Event (3/15/30)", "1930-03-15 - Event"),     # Year boundary
        ]
        
        for input_title, expected in edge_cases:
            result = normalizer.normalize_title(input_title)
            assert result == expected, f"Failed for: {input_title}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 