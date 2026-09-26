package com.buy01.product_service.repository;

import java.util.List;

import org.springframework.data.mongodb.repository.MongoRepository;

import com.buy01.product_service.models.Product;

public interface ProductRepository extends MongoRepository<Product, String> {
    List<Product> findByOwnerId(String ownerId);
}