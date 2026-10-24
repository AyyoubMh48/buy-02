package com.buy01.order_service;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

// No MongoDB runs during unit tests, so skip index creation at startup.
@SpringBootTest(properties = "spring.data.mongodb.auto-index-creation=false")
class OrderServiceApplicationTests {

	@Test
	void contextLoads() {
	}

}
