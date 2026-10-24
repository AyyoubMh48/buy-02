package com.buy01.order_service.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import com.buy01.order_service.dtos.external.ProductDetails;
import com.buy01.order_service.exception.BadRequestException;
import com.buy01.order_service.exception.UpstreamServiceException;

/** Reads current product data from Product Service, found through Eureka. */
@Component
public class ProductClient {

    private final RestClient restClient;

    public ProductClient(RestClient.Builder loadBalancedRestClientBuilder,
            @Value("${product-service.base-url}") String baseUrl) {
        this.restClient = loadBalancedRestClientBuilder.baseUrl(baseUrl).build();
    }

    public ProductDetails getProduct(String productId) {
        ProductDetails product;
        try {
            product = restClient.get()
                    .uri("/products/{id}", productId)
                    .accept(MediaType.APPLICATION_JSON)
                    .retrieve()
                    .body(ProductDetails.class);
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().value() == 404) {
                throw new BadRequestException("Product not found: " + productId);
            }
            throw new UpstreamServiceException(
                    "Product Service returned " + ex.getStatusCode().value() + " for product " + productId);
        } catch (RestClientException ex) {
            throw new UpstreamServiceException("Product Service is unreachable for product " + productId);
        }
        if (product == null) {
            throw new UpstreamServiceException("Product Service returned no data for product " + productId);
        }
        return product;
    }
}
