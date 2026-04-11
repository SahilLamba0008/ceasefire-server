package com.clipforge.api.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import com.clipforge.api.entity.Job;

public interface JobRepository extends JpaRepository<Job, String> {
}