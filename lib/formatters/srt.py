"""
SRT (SubRip) Subtitle Formatter

Generates subtitle files in SubRip format (.srt), the most widely supported
subtitle format used by YouTube, Premiere Pro, and most video players.
"""

import logging
from typing import List
from lib.engines.base import Segment, Word

logger = logging.getLogger(__name__)


class SRTFormatter:
    """
    Formats transcription results as SubRip (.srt) subtitle files.

    SRT Format Specification:
    - Sequential numbering starting from 1
    - Timestamps in HH:MM:SS,mmm format
    - Text content with UTF-8 encoding
    - Blank line between entries

    Example:
        1
        00:00:00,000 --> 00:00:02,500
        Hello world.

        2
        00:00:02,500 --> 00:00:05,000
        This is a test.
    """

    # Reading speed: characters per second (for Chinese ~4-5 chars/sec, English ~15-20 chars/sec)
    DEFAULT_CPS_CJK = 4.0  # Chinese/Japanese/Korean
    DEFAULT_CPS_LATIN = 15.0  # English and other Latin scripts
    MIN_DURATION = 1.0  # Minimum subtitle duration in seconds
    MAX_DURATION = 7.0  # Maximum subtitle duration in seconds

    # Punctuation marks that indicate sentence/clause boundaries
    SPLIT_PUNCTUATION = {'。', '，', '？', '！', ',', '.', '?', '!', '、', '；', ';'}

    def __init__(
        self,
        max_line_width: int = 42,
        max_line_count: int = 2,
        adjust_timing: bool = False,
        chars_per_second: float = None,
        split_by_punctuation: bool = False,
    ):
        """
        Initialize SRT formatter.

        Args:
            max_line_width: Maximum characters per line (default: 42, recommended for readability)
            max_line_count: Maximum lines per subtitle entry (1-3, default: 2)
            adjust_timing: If True, calculate start time backwards from end time based on text length
            chars_per_second: Reading speed override (auto-detected if None)
            split_by_punctuation: If True, split segments at punctuation marks (requires word timestamps)
        """
        self.max_line_width = max_line_width
        self.max_line_count = max(1, min(3, max_line_count))
        self.adjust_timing = adjust_timing
        self.chars_per_second = chars_per_second
        self.split_by_punctuation = split_by_punctuation

    def format(self, segments: List[Segment], word_level: bool = False) -> str:
        """
        Format segments as SRT subtitle file.

        Args:
            segments: List of transcription segments with timestamps
            word_level: If True, create one subtitle per word (requires words in segments)

        Returns:
            SRT formatted string
        """
        if word_level:
            return self._format_word_level(segments)
        else:
            return self._format_segment_level(segments)

    def _format_segment_level(self, segments: List[Segment]) -> str:
        """Format at segment level (sentence/phrase per subtitle)."""
        if self.adjust_timing:
            return self._format_with_adjusted_timing(segments)

        srt_entries = []
        for idx, segment in enumerate(segments, start=1):
            text = segment.text.strip()
            start_time = self._format_timestamp(segment.start)
            end_time = self._format_timestamp(segment.end)
            text_lines = self._wrap_text(text)
            entry = f"{idx}\n{start_time} --> {end_time}\n{text_lines}\n"
            srt_entries.append(entry)

        return "\n".join(srt_entries)

    def _format_with_adjusted_timing(self, segments: List[Segment]) -> str:
        """
        Format segments with adjusted timing, fixing overlaps.

        When adjust_timing causes subtitles to overlap, adjust the start time
        of the overlapping subtitle to match the end time of the previous one.
        """
        if not segments:
            return ""

        # First pass: optionally split by punctuation, then calculate adjusted timing
        adjusted_segments = []
        for segment in segments:
            # Split segment by punctuation if enabled
            if self.split_by_punctuation and segment.words:
                split_segments = self._split_by_punctuation(segment)
            else:
                split_segments = [{
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip(),
                }]

            for split_seg in split_segments:
                text = split_seg['text'].strip()
                if not text:
                    continue
                start_sec, end_sec = self._calculate_adjusted_timing(
                    text, split_seg['start'], split_seg['end']
                )
                adjusted_segments.append({
                    'start': start_sec,
                    'end': end_sec,
                    'text': text,
                })

        # Second pass: fix overlaps by adjusting start time
        for i in range(1, len(adjusted_segments)):
            prev_end = adjusted_segments[i - 1]['end']
            curr_start = adjusted_segments[i]['start']

            if curr_start < prev_end:
                # Overlap detected - set start to previous end
                adjusted_segments[i]['start'] = prev_end

        # Build SRT entries
        srt_entries = []
        for idx, seg in enumerate(adjusted_segments, start=1):
            start_time = self._format_timestamp(seg['start'])
            end_time = self._format_timestamp(seg['end'])
            text_lines = self._wrap_text(seg['text'])

            entry = f"{idx}\n{start_time} --> {end_time}\n{text_lines}\n"
            srt_entries.append(entry)

        return "\n".join(srt_entries)

    def _split_by_punctuation(self, segment: Segment) -> list:
        """
        Split a segment into multiple parts based on punctuation marks.

        Uses word timestamps to create accurate timing for each split.
        Splits at: 。，？！,. etc.

        Args:
            segment: Segment with word timestamps

        Returns:
            List of dicts with 'start', 'end', 'text' keys
        """
        if not segment.words:
            return [{
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip(),
            }]

        result = []
        current_words = []
        current_text = ""

        for word in segment.words:
            word_text = word.word.strip()
            current_words.append(word)
            current_text += word_text

            # Check if word ends with punctuation
            if word_text and word_text[-1] in self.SPLIT_PUNCTUATION:
                # Save current group
                if current_words and current_text.strip():
                    result.append({
                        'start': current_words[0].start,
                        'end': current_words[-1].end,
                        'text': current_text.strip(),
                    })
                current_words = []
                current_text = ""

        # Don't forget remaining words
        if current_words and current_text.strip():
            result.append({
                'start': current_words[0].start,
                'end': current_words[-1].end,
                'text': current_text.strip(),
            })

        return result if result else [{
            'start': segment.start,
            'end': segment.end,
            'text': segment.text.strip(),
        }]

    def _is_cjk_text(self, text: str) -> bool:
        """Check if text is primarily CJK (Chinese/Japanese/Korean)."""
        cjk_count = 0
        total_count = 0
        for char in text:
            if char.isalpha() or '\u4e00' <= char <= '\u9fff':
                total_count += 1
                # CJK Unified Ideographs
                if '\u4e00' <= char <= '\u9fff':
                    cjk_count += 1
                # Japanese Hiragana/Katakana
                elif '\u3040' <= char <= '\u30ff':
                    cjk_count += 1
                # Korean Hangul
                elif '\uac00' <= char <= '\ud7af':
                    cjk_count += 1

        if total_count == 0:
            return False
        return cjk_count / total_count > 0.3

    def _calculate_reading_duration(self, text: str) -> float:
        """
        Calculate estimated reading duration for text.

        Args:
            text: Subtitle text

        Returns:
            Estimated duration in seconds
        """
        if self.chars_per_second:
            cps = self.chars_per_second
        elif self._is_cjk_text(text):
            cps = self.DEFAULT_CPS_CJK
        else:
            cps = self.DEFAULT_CPS_LATIN

        # Count visible characters (excluding spaces for more accurate CJK calculation)
        char_count = len(text.replace(' ', ''))

        duration = char_count / cps

        # Clamp to min/max duration
        return max(self.MIN_DURATION, min(self.MAX_DURATION, duration))

    def _calculate_adjusted_timing(
        self, text: str, original_start: float, original_end: float
    ) -> tuple[float, float]:
        """
        Calculate adjusted timing with start time calculated backwards from end time.

        The end time is kept as anchor (accurate), start time is recalculated
        based on text reading duration.

        Args:
            text: Subtitle text
            original_start: Original start time (may be inaccurate)
            original_end: Original end time (accurate anchor)

        Returns:
            Tuple of (adjusted_start, adjusted_end)
        """
        # Keep end time as anchor
        end_time = original_end

        # Calculate duration based on text length
        duration = self._calculate_reading_duration(text)

        # Calculate start time backwards from end
        start_time = end_time - duration

        # Ensure start time is not negative
        if start_time < 0:
            start_time = 0

        return start_time, end_time

    def _format_word_level(self, segments: List[Segment]) -> str:
        """Format at word level (one word per subtitle)."""
        srt_entries = []
        entry_num = 1

        for segment in segments:
            if not segment.words:
                # Fallback to segment level if no word timestamps
                logger.warning(
                    f"Segment has no word timestamps, using segment timing"
                )
                start_time = self._format_timestamp(segment.start)
                end_time = self._format_timestamp(segment.end)
                text = segment.text.strip()
                entry = f"{entry_num}\n{start_time} --> {end_time}\n{text}\n"
                srt_entries.append(entry)
                entry_num += 1
                continue

            # Create entry for each word
            for word in segment.words:
                start_time = self._format_timestamp(word.start)
                end_time = self._format_timestamp(word.end)
                text = word.word.strip()

                entry = f"{entry_num}\n{start_time} --> {end_time}\n{text}\n"
                srt_entries.append(entry)
                entry_num += 1

        return "\n".join(srt_entries)

    def _format_timestamp(self, seconds: float) -> str:
        """
        Convert seconds to SRT timestamp format: HH:MM:SS,mmm

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def _wrap_text(self, text: str) -> str:
        """
        Wrap text to respect max line width and line count.

        Args:
            text: Text to wrap

        Returns:
            Wrapped text with newlines
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)

            # Check if adding this word exceeds line width
            if current_length + word_length + len(current_line) > self.max_line_width:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_length = word_length
                else:
                    # Single word exceeds max width, add it anyway
                    lines.append(word)
                    current_length = 0
            else:
                current_line.append(word)
                current_length += word_length

        # Add remaining words
        if current_line:
            lines.append(" ".join(current_line))

        # Limit to max line count
        if len(lines) > self.max_line_count:
            # Merge excess lines
            while len(lines) > self.max_line_count:
                # Merge last two lines
                last_line = lines.pop()
                lines[-1] = lines[-1] + " " + last_line

        return "\n".join(lines)

    def validate(self, srt_content: str) -> tuple[bool, List[str]]:
        """
        Validate SRT file format.

        Args:
            srt_content: SRT file content string

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        lines = srt_content.strip().split("\n")

        if not lines:
            return False, ["Empty SRT file"]

        # Basic structure validation
        entry_count = 0
        i = 0

        while i < len(lines):
            # Skip blank lines
            if not lines[i].strip():
                i += 1
                continue

            # Expect entry number
            if not lines[i].strip().isdigit():
                errors.append(f"Line {i+1}: Expected entry number, got '{lines[i]}'")
                i += 1
                continue

            entry_count += 1
            i += 1

            # Expect timestamp line
            if i >= len(lines):
                errors.append(f"Entry {entry_count}: Missing timestamp")
                break

            if " --> " not in lines[i]:
                errors.append(
                    f"Entry {entry_count}: Invalid timestamp format '{lines[i]}'"
                )

            i += 1

            # Expect text content (at least one line)
            if i >= len(lines) or not lines[i].strip():
                errors.append(f"Entry {entry_count}: Missing subtitle text")

            # Skip text lines until blank line or end
            while i < len(lines) and lines[i].strip():
                i += 1

        is_valid = len(errors) == 0
        return is_valid, errors
