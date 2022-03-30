from typing import List

from posthog.client import sync_execute
from posthog.helpers.session_recording import try_read_from_object_storage
from posthog.models import SessionRecordingEvent
from posthog.queries.session_recordings.session_recording import SessionRecording


class ClickhouseSessionRecording(SessionRecording):
    _recording_snapshot_query = """
        SELECT session_id, window_id, distinct_id, timestamp, snapshot_data
        FROM session_recording_events
        WHERE
            team_id = %(team_id)s
            AND session_id = %(session_id)s
        ORDER BY timestamp
    """

    def _query_recording_snapshots(self) -> List[SessionRecordingEvent]:
        response = sync_execute(
            self._recording_snapshot_query, {"team_id": self._team.id, "session_id": self._session_recording_id,},
        )

        events = []

        for (session_id, window_id, distinct_id, timestamp, snapshot_data) in response:

            loaded_data = try_read_from_object_storage(session_id, snapshot_data)

            events.append(
                SessionRecordingEvent(
                    session_id=session_id,
                    window_id=window_id,
                    distinct_id=distinct_id,
                    timestamp=timestamp,
                    snapshot_data=loaded_data,
                )
            )

        return events
