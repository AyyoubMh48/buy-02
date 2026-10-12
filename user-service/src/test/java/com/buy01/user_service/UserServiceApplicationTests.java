package com.buy01.user_service;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(properties = "jwt.secret=ci-only-test-signing-key-at-least-32-bytes")
class UserServiceApplicationTests {

	@Test
	void contextLoads() {
	}

}
