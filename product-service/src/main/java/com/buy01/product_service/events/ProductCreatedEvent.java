package com.buy01.product_service.events;

import java.time.Instant;

public record ProductCreatedEvent(
        String productId,
        String ownerId,
        String name,
        double price,
        int quantity,
        Instant createdAt
) {
}