package com.buy01.product_service.config;

 
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {

    /**
     * A RestClient.Builder that resolves hostnames against Eureka's registry
     * instead of DNS. Lets callers use the logical spring.application.name
     * of a service (e.g. "media") as if it were a real host:
     *   restClient.get().uri("http://media/api/v1/media/images/{id}", id)
     */
    @Bean
    public RestClient.Builder restClientBuilder() {
        return RestClient.builder();
    }
}
