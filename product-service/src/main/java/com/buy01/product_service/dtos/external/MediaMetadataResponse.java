package com.buy01.product_service.dtos.external;

 
// this record is kindaa worrk like a bridge between our 
// two isolated services, it allows us to represent the 
// media metadata without having to directly depend on the
//  media service's internal implementation details.

public record MediaMetadataResponse(
        String id,
        String filename,
        String contentType,
        String url,
        long size,
        String uploaderId
) {}
