package com.buy01.user_service.dto.external;

public record MediaMetadataResponse(
        String id,
        String filename,
        String contentType,
        String url,
        long size,
        String uploaderId
) {}