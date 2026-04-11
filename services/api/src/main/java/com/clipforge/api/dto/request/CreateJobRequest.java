package com.clipforge.api.dto.request;

import com.fasterxml.jackson.annotation.JsonAlias;

import jakarta.validation.constraints.NotBlank;

public class CreateJobRequest {
    @NotBlank(message = "YouTube URL is required")
    @JsonAlias({"youtube_url", "url"})
    private String youtubeUrl;
    
    public CreateJobRequest() {
    }

    public String getYoutubeUrl() {
        return youtubeUrl;
    }

    public void setYoutubeUrl(String youtubeUrl) {
        this.youtubeUrl = youtubeUrl;
    }
}
