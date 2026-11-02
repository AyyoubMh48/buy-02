package com.buy01.order_service.config;

import java.time.Clock;
import java.time.Duration;

import org.springframework.cloud.client.loadbalancer.LoadBalanced;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class AppConfig {

    /**
     * Plain builder for everything that asks for an unqualified RestClient.Builder, including the Eureka
     * client itself. If the load-balanced builder were the only one, Eureka would try to resolve its own
     * server address through the load balancer, fail, and the service would never register.
     */
    @Bean
    @Primary
    public RestClient.Builder restClientBuilder() {
        return RestClient.builder();
    }

    /** Resolves service names such as http://product-service through Eureka. Inject with @LoadBalanced. */
    @Bean
    @LoadBalanced
    public RestClient.Builder loadBalancedRestClientBuilder() {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(2));
        requestFactory.setReadTimeout(Duration.ofSeconds(5));
        return RestClient.builder().requestFactory(requestFactory);
    }

    @Bean
    public Clock clock() {
        return Clock.systemUTC();
    }
}
