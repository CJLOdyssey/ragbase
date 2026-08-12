"""SSE stream splitters — cross-chunk <think> tag state machines."""


class ThinkTagSplitter:
    """Streaming splitter for models that emit chain-of-thought inside <think>.

    Some providers (e.g. SiliconFlow's GLM-Z1) return reasoning inline in
    ``content`` wrapped in ``<think>...</think>`` instead of via
    ``reasoning_content``. This state machine accumulates those tags across SSE
    chunks and routes the enclosed text to "thinking" and everything else to
    "content", so the UI can render the chain-of-thought separately.
    """

    __slots__ = ("_in_think", "_buffer")

    def __init__(self) -> None:
        self._in_think = False
        self._buffer: list[str] = []

    def feed(self, text: str) -> tuple[list[str], list[str]]:
        """Process one content chunk; return (thinking_parts, content_parts)."""
        thinking: list[str] = []
        content: list[str] = []
        rest = text
        while rest:
            tag = "</think>" if self._in_think else "<think>"
            idx = rest.find(tag)
            if idx < 0:
                if self._in_think:
                    self._buffer.append(rest)
                else:
                    content.append(rest)
                break
            head, tail = rest[:idx], rest[idx + len(tag):]
            if self._in_think:
                self._buffer.append(head)
                thinking.append("".join(self._buffer))
                self._buffer = []
                self._in_think = False
            else:
                if head:
                    content.append(head)
                self._in_think = True
            rest = tail
        return thinking, content

    def finish(self) -> tuple[str | None, str | None]:
        """Flush any trailing buffer. Returns (leftover_thinking, leftover_content)."""
        leftover = "".join(self._buffer)
        self._buffer = []
        if leftover:
            if self._in_think:
                self._in_think = False
                return leftover, None
            return None, leftover
        return None, None


class ReasoningSplitter:
    """Streaming splitter for ``reasoning_content`` that may carry <think> tags.

    SiliconFlow's GLM-Z1 emits chain-of-thought in ``reasoning_content``
    wrapped in ``<think>`` — the tag may be sliced across SSE chunks
    (``'<th'`` + ``'ink'`` + ``'>'``) and the closing tag is often omitted
    entirely. DeepSeek's native ``reasoning_content`` carries NO tag at all.

    State machine over two modes:
    - content mode: boundedly wait for a fully-assembled ``<think>`` opening
      tag (cross-chunk slicing); past a small character budget the stream is
      treated as tag-less (DeepSeek) and emitted immediately.
    - thinking mode: strip a fully-assembled ``</think>`` closing tag
      (cross-chunk slicing) and emit everything before it; the remainder is
      re-processed (may open a new think block).
    """

    __slots__ = ("_pending", "_in_think")

    _OPEN_TAG = "<think>"
    _CLOSE_TAG = "</think>"
    # Bounded wait for the tag to assemble across chunks: <think> is 7 chars,
    # providers slice ~1-2 chars/chunk, so 16 chars covers the worst case
    # while keeping tag-less streams (DeepSeek) real-time.
    _TAG_WAIT_CHARS = 16

    def __init__(self) -> None:
        self._pending: list[str] = []
        self._in_think = False

    def feed(self, text: str) -> list[str]:
        """Process one reasoning chunk; return thinking parts to emit."""
        out: list[str] = []
        rest = text
        while rest:
            rest = (
                self._feed_thinking(rest, out)
                if self._in_think
                else self._feed_content(rest, out)
            )
        return out

    def _feed_content(self, text: str, out: list[str]) -> str:
        """Content mode: wait for the opening tag, or stream tag-less input."""
        self._pending.append(text)
        joined = "".join(self._pending)
        idx = joined.find(self._OPEN_TAG)
        if idx < 0:
            if len(joined) >= self._TAG_WAIT_CHARS:
                flushed = "".join(self._pending)
                self._pending = []
                if flushed:
                    out.append(flushed)
            return ""
        # Opening tag assembled — drop everything before it (format noise such
        # as leading newlines) and switch to thinking mode. The trailing part
        # may also start with a chunk-boundary newline; strip it.
        tail = joined[idx + len(self._OPEN_TAG):].lstrip("\n")
        self._pending = []
        self._in_think = True
        return tail

    def _feed_thinking(self, text: str, out: list[str]) -> str:
        """Thinking mode: strip the closing tag (cross-chunk), keep the rest."""
        self._pending.append(text)
        joined = "".join(self._pending)
        idx = joined.find(self._CLOSE_TAG)
        if idx < 0:
            # Not closed yet — emit everything but a trailing fragment that
            # could be a sliced closing tag.
            hold = len(self._CLOSE_TAG) - 1
            if len(joined) > hold:
                emit, keep = joined[:-hold], joined[-hold:]
                self._pending = [keep]
                if emit:
                    out.append(emit)
            return ""
        before = joined[:idx]
        self._pending = []
        self._in_think = False
        if before:
            out.append(before)
        return joined[idx + len(self._CLOSE_TAG):]

    def finish(self) -> str | None:
        """Flush any remaining buffered thinking text."""
        leftover = "".join(self._pending)
        self._pending = []
        self._in_think = False
        return leftover or None
