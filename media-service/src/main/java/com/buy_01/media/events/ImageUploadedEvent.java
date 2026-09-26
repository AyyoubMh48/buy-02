package com.buy_01.media.events;

import java.time.LocalDateTime;

public record ImageUploadedEvent(
        String mediaId,
        String uploaderId,
        String url,
        String filename,
        String contentType,
        long size,
        LocalDateTime uploadedAt
) {
}