package com.buy_01.media;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(properties = {"cloudinary.cloud-name=ci-fixture", "cloudinary.api-key=ci-fixture", "cloudinary.api-secret=ci-fixture"})
class MediaApplicationTests {

	@Test
	void contextLoads() {
	}

}
