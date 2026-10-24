package com.buy01.order_service.client;

import java.math.BigDecimal;
import java.time.Duration;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;
import com.buy01.order_service.exception.UpstreamServiceException;

/** Uses the same synchronous RestClient pattern as ProductService's MediaServiceClient. */
@Component
public class ProductClient {
    public record Product(String id, String name, BigDecimal price, int quantity, List<String> images) {}
    private final RestClient client;
    public ProductClient(@Value("${product-service.base-url}") String url) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(3));
        factory.setReadTimeout(Duration.ofSeconds(5));
        client = RestClient.builder().requestFactory(factory).baseUrl(url).build();
    }
    public Product get(String id) {
        try {
            Product p = client.get().uri("/{id}", id).retrieve().body(Product.class);
            if (p == null || !id.equals(p.id()) || p.price() == null || p.price().signum() < 0) {
                throw new UpstreamServiceException("Invalid Product Service response");
            }
            return p;
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().value() == 404) return null;
            throw new UpstreamServiceException("Product Service could not validate this cart");
        } catch (RestClientException ex) {
            throw new UpstreamServiceException("Product Service is unavailable. Try again later");
        }
    }
}
