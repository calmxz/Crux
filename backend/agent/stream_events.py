"""Server-sent-event payloads for the streaming tutor loop.

A StreamEvent is the unit yielded by tutor.run_streaming. The stream route
(Task 13) serializes each via to_sse() onto a text/event-stream response.
"""

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class StreamEvent:
    # one of: 'tool_call_start' | 'tool_call_done' | 'assistant_delta'
    #         | 'citations' | 'cost_warning' | 'done' | 'error' | 'cancelled'
    #         | 'check_question' | 'topic_suggestions' | 'followup_skipped'
    type: str
    data: Any

    def to_sse(self) -> str:
        return f"event: {self.type}\ndata: {json.dumps(self.data)}\n\n"
