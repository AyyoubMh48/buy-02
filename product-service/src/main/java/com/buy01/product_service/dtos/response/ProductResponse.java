package com.buy01.product_service.dtos.response;


public record ProductResponse (
    String id,
    String name,
    String description,
    double price,
    String ownerId,
    String[] images,
    String[] mediaIds,
    int quantity
) 
{}
