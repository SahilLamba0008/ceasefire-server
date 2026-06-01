package com.clipforge.outboxworker.model;

import org.springframework.jdbc.core.RowMapper;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;

public class JobEventRowMapper implements RowMapper<JobEvent> {

    @Override
    public JobEvent mapRow(ResultSet rs, int rowNum) throws SQLException {
        JobEvent event = new JobEvent();
        event.setId(rs.getObject("id", UUID.class));
        event.setEventType(rs.getString("event_type"));
        event.setPayload(rs.getString("payload"));
        event.setRetryCount(rs.getInt("retry_count"));
        event.setMaxRetries(rs.getInt("max_retries"));
        event.setCreatedAt(toOffsetDateTime(rs.getTimestamp("created_at")));
        return event;
    }

    private OffsetDateTime toOffsetDateTime(Timestamp ts) {
        if (ts == null) return null;
        return ts.toInstant().atOffset(ZoneOffset.UTC);
    }
}
