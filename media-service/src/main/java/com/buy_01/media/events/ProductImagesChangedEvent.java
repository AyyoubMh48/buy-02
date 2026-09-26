package com.buy_01.media.events;

import java.util.List;

/** Current media IDs are empty when the product is deleted. */
public record ProductImagesChangedEvent(
        String productId,
        String ownerId,
        List<String> previousMediaIds,
        List<String> mediaIds) {
}
