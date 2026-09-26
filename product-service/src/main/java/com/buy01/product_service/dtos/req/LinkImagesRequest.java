package com.buy01.product_service.dtos.req;

import java.util.List;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;

 
public record LinkImagesRequest(
        @NotEmpty(message = "At least one image URL is required")
        List<@NotBlank(message = "Image URL cannot be blank") String> imageUrls
) {}
