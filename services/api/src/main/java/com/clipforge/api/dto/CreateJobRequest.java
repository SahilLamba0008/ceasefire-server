package com.clipforge.api.dto;

import jakarta.validation.constraints.NotBlank;

public class CreateJobRequest {

    @NotBlank(message = "Title is required")
    private String title;

    @NotBlank(message = "Description is required")
    private String description;

    @NotBlank(message = "YouTube URL is required")
    private String youtubeUrl;
}