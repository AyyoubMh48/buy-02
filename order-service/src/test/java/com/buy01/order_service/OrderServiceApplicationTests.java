package com.buy01.order_service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.client.loadbalancer.LoadBalanced;
import org.springframework.web.client.RestClient;

import com.buy01.order_service.service.CartService;
import com.buy01.order_service.service.OrderService;
import com.buy01.order_service.service.OrderServiceImpl;

@SpringBootTest(properties = {
        "spring.data.mongodb.auto-index-creation=false",
        "eureka.client.enabled=false"})
class OrderServiceApplicationTests {

    @Autowired
    private OrderService orderService;

    @Autowired
    private CartService cartService;

    @Autowired
    private RestClient.Builder defaultBuilder;

    @Autowired
    @LoadBalanced
    private RestClient.Builder loadBalancedBuilder;

    @Test
    void defaultRestClientBuilderIsNotLoadBalanced() {
        // The Eureka client takes the default builder; a load-balanced one would stop registration.
        assertThat(defaultBuilder).isNotSameAs(loadBalancedBuilder);
    }

    @Test
    void contextLoadsWithRealOrdersAndCartServices() {
        assertThat(orderService).isInstanceOf(OrderServiceImpl.class);
        assertThat(cartService).isNotNull();
    }
}
