"""Field content processing utilities for ankityping plugin."""

from __future__ import annotations

import re
import html
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class ProcessingConfig:
    """Configuration for content processing."""
    # HTML processing
    remove_html_tags: bool = True
    preserve_line_breaks: bool = True
    handle_html_entities: bool = True

    # Text cleaning
    normalize_whitespace: bool = True
    remove_extra_spaces: bool = True

    # Special handling
    keep_important_formatting: bool = False  # Keep <b>, <i>, <u> if needed
    replace_html_formatting: bool = True  # Replace <b>word</b> with word


class FieldProcessor:
    """Processes field content by removing HTML tags and cleaning text."""

    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()

    def process_field_content(self, content: str) -> str:
        """
        Process field content by removing HTML tags and cleaning text.

        Args:
            content: Raw field content from Anki

        Returns:
            Cleaned text content suitable for typing practice
        """
        if not content:
            return ""

        print(f"DEBUG: Processing field content: {content[:100]}...")

        # Step 1: Handle HTML entities
        if self.config.handle_html_entities:
            content = self._decode_html_entities(content)

        # Step 2: Handle HTML formatting tags specially
        if self.config.replace_html_formatting:
            content = self._replace_html_formatting(content)

        # Step 3: Remove HTML tags
        if self.config.remove_html_tags:
            content = self._remove_html_tags(content)

        # Step 4: Preserve line breaks if needed
        if self.config.preserve_line_breaks:
            content = self._preserve_line_breaks(content)

        # Step 5: Normalize whitespace
        if self.config.normalize_whitespace:
            content = self._normalize_whitespace(content)

        # Step 6: Remove extra spaces
        if self.config.remove_extra_spaces:
            content = self._remove_extra_spaces(content)

        print(f"DEBUG: Processed content: {content[:100]}...")
        return content.strip()

    def _decode_html_entities(self, content: str) -> str:
        """Decode HTML entities like &nbsp;, &lt;, etc."""
        try:
            return html.unescape(content)
        except Exception as e:
            print(f"DEBUG: Error decoding HTML entities: {e}")
            return content

    def _replace_html_formatting(self, content: str) -> str:
        """Replace HTML formatting tags with their text content."""
        # Common formatting tags to replace
        formatting_tags = [
            r'<b[^>]*>(.*?)</b>',      # Bold
            r'<i[^>]*>(.*?)</i>',      # Italic
            r'<u[^>]*>(.*?)</u>',      # Underline
            r'<strong[^>]*>(.*?)</strong>',  # Strong
            r'<em[^>]*>(.*?)</em>',     # Emphasis
            r'<mark[^>]*>(.*?)</mark>',  # Highlight
        ]

        for tag_pattern in formatting_tags:
            content = re.sub(tag_pattern, r'\1', content, flags=re.IGNORECASE | re.DOTALL)

        return content

    def _remove_html_tags(self, content: str) -> str:
        """Remove HTML tags while preserving content."""
        if self.config.keep_important_formatting:
            # Keep certain formatting tags
            important_tags = ['b', 'i', 'u', 'strong', 'em']
            # Create pattern to match all tags except important ones
            tag_pattern = r'<(?!/?(' + '|'.join(important_tags) + r')\b)[^>]+>'
        else:
            # Remove all HTML tags
            tag_pattern = r'<[^>]+>'

        content = re.sub(tag_pattern, '', content)
        return content

    def _preserve_line_breaks(self, content: str) -> str:
        """Convert HTML line breaks to regular line breaks."""
        # Convert <br> tags to newlines
        content = re.sub(r'<br[^>]*>', '\n', content, flags=re.IGNORECASE)

        # Handle paragraph tags
        content = re.sub(r'</p[^>]*>', '\n\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<p[^>]*>', '', content, flags=re.IGNORECASE)

        # Convert multiple newlines to double newlines
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content

    def _normalize_whitespace(self, content: str) -> str:
        """Normalize whitespace characters."""
        # Convert various whitespace to regular spaces
        content = re.sub(r'[\t\f\v]', ' ', content)

        # Handle non-breaking spaces
        content = content.replace('\xa0', ' ')

        return content

    def _remove_extra_spaces(self, content: str) -> str:
        """Remove extra spaces and clean up the text."""
        # Remove leading/trailing spaces from each line
        lines = content.split('\n')
        lines = [line.strip() for line in lines if line.strip()]

        # Join with single spaces
        result = ' '.join(lines)

        # Remove any double spaces that might remain
        result = re.sub(r' {2,}', ' ', result)

        return result

    def get_supported_html_tags(self) -> List[str]:
        """Get list of HTML tags that the processor can handle."""
        return [
            'b', 'i', 'u', 'strong', 'em', 'mark',  # Formatting
            'p', 'br', 'div', 'span',              # Structure
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',    # Headings
            'ul', 'ol', 'li',                      # Lists
            'table', 'tr', 'td', 'th',             # Tables
            'a', 'img',                             # Links and images
        ]

    def analyze_content(self, content: str) -> dict:
        """Analyze content and return information about what processing would do."""
        analysis = {
            'has_html': bool(re.search(r'<[^>]+>', content)),
            'has_html_entities': bool(re.search(r'&[a-zA-Z]+;', content)),
            'has_formatting': bool(re.search(r'<(b|i|u|strong|em)[^>]*>', content, re.IGNORECASE)),
            'line_count': len(content.split('\n')),
            'char_count': len(content),
            'word_count': len(content.split()),
        }

        # Count specific tags
        tag_counts = {}
        for tag in self.get_supported_html_tags():
            pattern = rf'<{tag}[^>]*>|</{tag}>'
            count = len(re.findall(pattern, content, re.IGNORECASE))
            if count > 0:
                tag_counts[tag] = count

        analysis['tag_counts'] = tag_counts

        return analysis


# Convenience function for common usage
def clean_field_content(content: str, remove_html: bool = True) -> str:
    """
    Quick function to clean field content with default settings.

    Args:
        content: Raw field content
        remove_html: Whether to remove HTML tags

    Returns:
        Cleaned content
    """
    config = ProcessingConfig(remove_html_tags=remove_html)
    processor = FieldProcessor(config)
    return processor.process_field_content(content)