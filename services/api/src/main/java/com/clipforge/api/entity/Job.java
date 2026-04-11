package com.clipforge.api.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;

@Entity
public class Job {

    @Id
    private String jobId;

    private String title;
    private String description;
    private String youtubeUrl;

    // getters/setters
}