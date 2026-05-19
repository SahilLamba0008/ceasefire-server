package com.clipforge.api.repository;

import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.clipforge.api.entity.JobEvent;

public interface JobEventRepository extends JpaRepository<JobEvent, UUID> {
}
