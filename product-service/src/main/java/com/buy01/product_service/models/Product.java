package com.buy01.product_service.models;
import java.time.Instant;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
@NoArgsConstructor
@AllArgsConstructor
@Getter
@Setter
@Builder
@Document(collection = "products")

public class Product {

    @Id
    private String id;

    private String name;

    private String description;

    private double price;

    private String ownerId;
    
    private String[] images;            

    private String[] mediaIds;

    private int quantity;

    private Instant createdAt;

    private Instant updatedAt;
    
}