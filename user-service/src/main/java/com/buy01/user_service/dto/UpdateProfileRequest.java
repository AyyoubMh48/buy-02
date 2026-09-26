package com.buy01.user_service.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record UpdateProfileRequest(

        @NotBlank(message = "Username is required")
        @Size(min = 2, max = 50, message = "Username must be between 2 and 50 characters")
        @Pattern(regexp = "^[\\p{L}0-9_.'\\- @]+$", message = "Username contains invalid characters")
        String username,

        @Size(max = 2048, message = "Avatar URL or media ID is too long")
        @Pattern(regexp = "^(https?://[^\\s<>\"'{}|\\\\^`]+|[a-zA-Z0-9_-]+)?$", message = "Avatar must be a valid media ID or HTTP/HTTPS URL")
        String avatarUrl
) {}