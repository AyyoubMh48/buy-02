package com.buy01.order_service;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import com.buy01.order_service.service.OrderService;

@SpringBootTest
class OrderServiceApplicationTests {

	// No OrderService implementation exists yet; drop this mock when it is added.
	@MockitoBean
	private OrderService orderService;

	@Test
	void contextLoads() {
	}

}
